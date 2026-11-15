"""星よみPLANET 自動投稿（複数アカウント対応）

使い方:
  python main.py generate            # accounts.json で使うテーマの占いと画像を作る
  python main.py post                # accounts.json の各アカウントに投稿
  python main.py post --dry-run      # 投稿せずに投稿文を表示（確認用）
  python main.py reply               # Threads / Instagram のコメントに自動返信
  python main.py reply --dry-run     # 返信せずに返信文だけ表示
  python main.py generate --date 2026-12-01   # 日付指定
  --slot morning / noon / evening で朝・昼・夜の枠を指定（省略時は日本時間の時刻で自動判定）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fortune import texts
from fortune.card import make_card
from fortune.generate import build_fortune

ROOT = Path(__file__).parent
OUT = ROOT / "out"
ACCOUNTS = ROOT / "accounts.json"
JST = timezone(timedelta(hours=9))

# GitHub Actions では未設定の変数が空文字で渡るため `or` で既定値にする
SITE_NAME = os.environ.get("SITE_NAME") or "星よみPLANET"
SITE_URL = os.environ.get("SITE_URL") or "https://example.com/"


def load_accounts(slot: str | None = None) -> list[dict]:
    accounts = json.loads(ACCOUNTS.read_text(encoding="utf-8"))["accounts"]
    if slot:
        accounts = [a for a in accounts if a.get("slot", "morning") == slot]
    return accounts


def current_slot() -> str:
    """日本時間の今の時刻から朝・昼・夜を決める（GitHub の遅延で1〜2時間ずれても大丈夫なように）。"""
    hour = datetime.now(JST).hour
    if hour < 10:
        return "morning"
    return "noon" if hour < 17 else "evening"


def env(name: str | None) -> str:
    return (os.environ.get(name) or "").strip() if name else ""


def _uid(acc: dict) -> str:
    """投稿先のユーザーID。Secret（user_id_env）→ accounts.json の user_id → "me" の順。"""
    return env(acc.get("user_id_env")) or acc.get("user_id") or "me"


def image_url_for(card_rel: str) -> str:
    base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY")
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        if not repo:
            raise RuntimeError("IMAGE_BASE_URL か GITHUB_REPOSITORY が必要です")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}"
    return f"{base}/{card_rel}"


def cmd_generate(day: date, slot: str) -> None:
    themes = sorted({a["theme"] for a in load_accounts(slot)})
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in themes:
        fortune = build_fortune(day, theme)
        if theme == "birthmonth":  # お昼の投稿は文章だけ（画像なし）
            (OUT / f"{theme}.json").write_text(json.dumps(fortune, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"生成しました: {theme}（画像なし）")
            continue
        card_rel = f"cards/{day.isoformat()}-{theme}.jpg"
        make_card(fortune, ROOT / card_rel, SITE_NAME)
        fortune["card"] = card_rel
        (OUT / f"{theme}.json").write_text(json.dumps(fortune, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"生成しました: {card_rel}（文章: {fortune['source']}）")


def _texts_for(platform: str, fortune: dict) -> tuple[str, str | None]:
    if fortune.get("kind") == "birthmonth":
        if platform != "threads":
            raise RuntimeError("お昼の誕生月投稿は Threads だけに対応しています")
        return texts.threads_noon(fortune), f"{texts.NOON_REPLY}\n{SITE_URL}"
    if platform == "x":
        return texts.x_post(fortune), texts.x_reply(fortune, SITE_URL)
    if platform == "threads":
        return texts.threads_post(fortune), texts.threads_reply(fortune, SITE_URL)
    if platform == "instagram":
        return texts.instagram_caption(fortune, SITE_NAME), None
    raise RuntimeError(f"未対応のSNS: {platform}")


def _already_posted(acc: dict, body: str) -> bool:
    """同じ見出し（日付＋タイトル）の投稿が最近あれば True。
    GitHub の定期実行が遅れて、手動実行と二重に投稿されるのを防ぐ。"""
    from fortune import posters

    head = body.splitlines()[0]
    p = acc["platform"]
    try:
        if p == "threads":
            recent = posters.recent_threads_texts(env(acc["token_env"]), _uid(acc))
        elif p == "instagram":
            recent = posters.recent_instagram_captions(env(acc["token_env"]), _uid(acc))
        else:
            return False
    except Exception as e:  # 確認できないときは投稿を優先する
        print(f"[warn] {acc['name']}: 重複確認に失敗（{e}）")
        return False
    return any(t.startswith(head) for t in recent)


def _post_one(acc: dict, fortune: dict, body: str, reply: str | None) -> str:
    from fortune import posters

    p = acc["platform"]
    if p == "threads":
        image = image_url_for(fortune["card"]) if fortune.get("card") else None
        return posters.post_threads(body, image, reply,
                                    token=env(acc["token_env"]), user_id=_uid(acc))
    if p == "instagram":
        user_id = _uid(acc)
        return posters.post_instagram(body, image_url_for(fortune["card"]),
                                      token=env(acc["token_env"]), ig_user=user_id)
    if p == "x":
        keys = [env(acc.get(k)) for k in ("api_key_env", "api_secret_env", "token_env", "token_secret_env")]
        if not all(keys):
            raise RuntimeError("X のキー4つのうち未設定のものがあります")
        return posters.post_x(body, ROOT / fortune["card"], reply, *keys)
    raise RuntimeError(f"未対応のSNS: {p}")


def cmd_post(dry_run: bool, slot: str) -> int:
    failed, posted = [], 0
    for acc in load_accounts(slot):
        fortune = json.loads((OUT / f"{acc['theme']}.json").read_text(encoding="utf-8"))
        body, reply = _texts_for(acc["platform"], fortune)

        if dry_run:
            print(f"===== {acc['name']}（{len(body)}字） =====\n{body}")
            if reply:
                print(f"--- リプライ ---\n{reply}")
            print()
            continue

        if not env(acc["token_env"]):
            print(f"[skip] {acc['name']}: {acc['token_env']} が未登録のためスキップ")
            continue
        if _already_posted(acc, body):
            print(f"[skip] {acc['name']}: 同じ投稿がすでにあるためスキップ")
            continue
        if posted:
            time.sleep(15)  # アカウント間で少し間をあける
        # 一時的なトラブル（画像の読み込み失敗・混雑など）に備えて、少し待って最大3回まで試す
        for attempt in range(1, RETRIES + 1):
            try:
                pid = _post_one(acc, fortune, body, reply)
                print(f"[ok] {acc['name']}: {pid}")
                posted += 1
                break
            except Exception as e:  # 1つ失敗しても他のアカウントは続ける
                msg = _redact(str(e))
                # ::error:: にすると、GitHub にログインしなくても実行画面の Annotations に理由が出る
                print(f"::error title={acc['name']} 投稿失敗（{attempt}/{RETRIES}回目）::{msg}")
                if attempt == RETRIES:
                    failed.append(acc["name"])
                    break
                time.sleep(RETRY_WAIT)
                if _already_posted(acc, body):  # 失敗に見えて実は投稿できていた場合
                    print(f"[ok] {acc['name']}: 投稿を確認できました")
                    posted += 1
                    break
    return 1 if failed else 0


RETRIES = 3
RETRY_WAIT = 90  # 秒


def _redact(text: str) -> str:
    """エラー文にトークンが混ざっても表示されないように伏せる。"""
    for name, val in os.environ.items():
        if val and len(val) >= 20 and ("TOKEN" in name or "SECRET" in name or "KEY" in name):
            text = text.replace(val, "***")
    text = re.sub(r"access_token=[^&\s'\"]+", "access_token=***", text)
    return text.replace("\n", " ")[:800]


def cmd_reply(dry_run: bool) -> int:
    """Threads / Instagram のコメントに自動返信する（X は読み取りAPIが高額なので対象外）。"""
    from fortune.replies import run_account

    failed, review_all, seen = [], [], set()
    for acc in load_accounts():
        if acc["platform"] not in ("threads", "instagram"):
            continue
        # 朝と夜で同じアカウントが2回書かれているので、1アカウント1回だけ処理する
        key = (acc["platform"], acc["token_env"])
        if key in seen:
            continue
        seen.add(key)
        token = env(acc["token_env"])
        if not token:
            print(f"[skip] {acc['name']}: {acc['token_env']} が未登録")
            continue
        print(f"===== {acc['name']} =====")
        try:
            sent, review = run_account(acc["platform"], token, _uid(acc), dry_run)
            print(f"[ok] 返信 {sent} 件")
            review_all += [f"{acc['name']}: {r}" for r in review]
        except Exception as e:
            print(f"[error] {acc['name']}: {e}")
            failed.append(acc["name"])
    if review_all:
        print("\n===== 自動返信しなかったコメント（手動で確認してください） =====")
        print("\n".join(review_all))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["generate", "post", "reply"])
    ap.add_argument("--date", help="YYYY-MM-DD（省略時は日本時間の今日）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--slot", choices=["morning", "noon", "evening", "auto"], default="auto",
                    help="morning（朝）/ noon（昼）/ evening（夜）。省略時は日本時間の時刻で自動判定")
    args = ap.parse_args()
    slot = current_slot() if args.slot == "auto" else args.slot
    if args.command == "generate":
        day = date.fromisoformat(args.date) if args.date else datetime.now(JST).date()
        print(f"枠: {slot}")
        cmd_generate(day, slot)
        return 0
    if args.command == "reply":
        return cmd_reply(args.dry_run)
    return cmd_post(args.dry_run, slot)


if __name__ == "__main__":
    sys.exit(main())
