"""星よみPLANET 自動投稿（複数アカウント対応）

使い方:
  python main.py generate            # accounts.json で使うテーマの占いと画像を作る
  python main.py post                # accounts.json の各アカウントに投稿
  python main.py post --dry-run      # 投稿せずに投稿文を表示（確認用）
  python main.py reply               # Threads / Instagram のコメントに自動返信
  python main.py reply --dry-run     # 返信せずに返信文だけ表示
  python main.py generate --date 2026-12-01   # 日付指定
"""
from __future__ import annotations

import argparse
import json
import os
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


def load_accounts() -> list[dict]:
    return json.loads(ACCOUNTS.read_text(encoding="utf-8"))["accounts"]


def env(name: str | None) -> str:
    return (os.environ.get(name) or "").strip() if name else ""


def image_url_for(card_rel: str) -> str:
    base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY")
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        if not repo:
            raise RuntimeError("IMAGE_BASE_URL か GITHUB_REPOSITORY が必要です")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}"
    return f"{base}/{card_rel}"


def cmd_generate(day: date) -> None:
    themes = sorted({a["theme"] for a in load_accounts()})
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in themes:
        fortune = build_fortune(day, theme)
        card_rel = f"cards/{day.isoformat()}-{theme}.jpg"
        make_card(fortune, ROOT / card_rel, SITE_NAME)
        fortune["card"] = card_rel
        (OUT / f"{theme}.json").write_text(json.dumps(fortune, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"生成しました: {card_rel}（文章: {fortune['source']}）")


def _texts_for(platform: str, fortune: dict) -> tuple[str, str | None]:
    if platform == "x":
        return texts.x_post(fortune), texts.x_reply(fortune, SITE_URL)
    if platform == "threads":
        return texts.threads_post(fortune), texts.threads_reply(fortune, SITE_URL)
    if platform == "instagram":
        return texts.instagram_caption(fortune, SITE_NAME), None
    raise RuntimeError(f"未対応のSNS: {platform}")


def _post_one(acc: dict, fortune: dict, body: str, reply: str | None) -> str:
    from fortune import posters

    p = acc["platform"]
    if p == "threads":
        return posters.post_threads(body, image_url_for(fortune["card"]), reply,
                                    token=env(acc["token_env"]), user_id=env(acc.get("user_id_env")) or "me")
    if p == "instagram":
        user_id = env(acc.get("user_id_env"))
        if not user_id:
            raise RuntimeError(f"{acc.get('user_id_env')} が設定されていません")
        return posters.post_instagram(body, image_url_for(fortune["card"]),
                                      token=env(acc["token_env"]), ig_user=user_id)
    if p == "x":
        keys = [env(acc.get(k)) for k in ("api_key_env", "api_secret_env", "token_env", "token_secret_env")]
        if not all(keys):
            raise RuntimeError("X のキー4つのうち未設定のものがあります")
        return posters.post_x(body, ROOT / fortune["card"], reply, *keys)
    raise RuntimeError(f"未対応のSNS: {p}")


def cmd_post(dry_run: bool) -> int:
    failed, posted = [], 0
    for acc in load_accounts():
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
        if posted:
            time.sleep(15)  # アカウント間で少し間をあける
        try:
            pid = _post_one(acc, fortune, body, reply)
            print(f"[ok] {acc['name']}: {pid}")
            posted += 1
        except Exception as e:  # 1つ失敗しても他のアカウントは続ける
            print(f"[error] {acc['name']}: {e}")
            failed.append(acc["name"])
    return 1 if failed else 0


def cmd_reply(dry_run: bool) -> int:
    """Threads / Instagram のコメントに自動返信する（X は読み取りAPIが高額なので対象外）。"""
    from fortune.replies import run_account

    failed, review_all = [], []
    for acc in load_accounts():
        if acc["platform"] not in ("threads", "instagram"):
            continue
        token = env(acc["token_env"])
        if not token:
            print(f"[skip] {acc['name']}: {acc['token_env']} が未登録")
            continue
        print(f"===== {acc['name']} =====")
        try:
            sent, review = run_account(acc["platform"], token, env(acc.get("user_id_env")), dry_run)
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
    args = ap.parse_args()
    if args.command == "generate":
        day = date.fromisoformat(args.date) if args.date else datetime.now(JST).date()
        cmd_generate(day)
        return 0
    if args.command == "reply":
        return cmd_reply(args.dry_run)
    return cmd_post(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
