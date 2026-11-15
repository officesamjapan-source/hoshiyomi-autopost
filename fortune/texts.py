"""SNS ごとの投稿文を作る（文字数制限に合わせる）。テーマ（総合運/恋愛運）で言葉とタグを変える。

文章が主役。絵文字は1投稿につき🌙を1つまで（1行目の見出しだけ）。"""
from __future__ import annotations

from datetime import date

from . import koyomi

# 投稿の下にぶら下げる、無料鑑定（公式LINE）の案内。このあとに LINE の URL が続く
LINE_GUIDE = ("ひかりの無料鑑定を受け付けています。\n"
              "\n"
              "お受け取り方法はこちら\n"
              "① ひかり（@hoshiyomi_koi）をフォロー\n"
              "② 下のリンクから公式LINEを追加")

STYLE = {
    "general": {
        "icon": "🌙",
        "tags_x": "#今日の運勢 #星座占い",
        "tags_threads": "#星座占い",
        "tags_ig": ("#今日の運勢 #星座占い #12星座 #占い #星占い #運勢 #星よみ "
                    "#開運 #ラッキーアイテム #ラッキーカラー #占い好きな人と繋がりたい"),
        "reply": LINE_GUIDE,
    },
    "love": {
        "icon": "🌙",
        "tags_x": "#恋愛運 #星座占い",
        "tags_threads": "#恋愛運",
        "tags_ig": ("#恋愛運 #今日の恋愛運 #星座占い #12星座 #恋愛占い #占い #片思い "
                    "#恋愛 #星占い #開運 #占い好きな人と繋がりたい"),
        "reply": LINE_GUIDE,
    },
}


# Threads / Instagram の投稿に入れる呼びかけ（コメントには replies.py が自動返信する）
COMMENT_CALL = "星座か誕生月をコメントしてくれたら、ひかりがひと言お返事します。"


def _style(fortune: dict) -> dict:
    return STYLE.get(fortune.get("kind", "general"), STYLE["general"])


def _label(fortune: dict) -> str:
    return fortune.get("theme_label") or "今日のテーマ"


def _head(fortune: dict) -> str:
    d = date.fromisoformat(fortune["date"])
    return f"{_style(fortune)['icon']}{d.month}/{d.day}（{'月火水木金土日'[d.weekday()]}）{fortune['title']}"


def x_post(fortune: dict) -> str:
    """X: 日本語は1文字=2カウントで上限280 → 全角140字程度に収める。"""
    r = fortune["ranking"]
    medal = ["🥇", "🥈", "🥉"]
    lines = [_head(fortune), ""]
    lines += [f"{medal[i]}{s['name']}" for i, s in enumerate(r[:3])]
    lines += ["", "あなたの星座は何位？👇", _style(fortune)["tags_x"]]
    return "\n".join(lines)


def x_reply(fortune: dict, site_url: str) -> str:
    return f"{_style(fortune)['reply']}\n{site_url}"


# 星座ごとの「いちばん多く重なる誕生月」（例：牡羊座 3/21〜4/19 → 4月）
SIGN_MONTH = {"aries": 4, "taurus": 5, "gemini": 6, "cancer": 7, "leo": 8, "virgo": 9,
              "libra": 10, "scorpio": 11, "sagittarius": 12, "capricorn": 1, "aquarius": 2, "pisces": 3}


def _with_month(s: dict) -> str:
    """例: 牡羊座 × 4月生まれ（星座記号は絵文字になるので付けない）"""
    return f"{s['name']} × {SIGN_MONTH[s['key']]}月生まれ"


def _koyomi(fortune: dict) -> str:
    return koyomi.koyomi_line(date.fromisoformat(fortune["date"]))


def threads_post(fortune: dict) -> str:
    """Threads: 上限500字。"""
    r = fortune["ranking"]
    lines = [_head(fortune), f"{_label(fortune)}：{fortune['theme']}", _koyomi(fortune), ""]
    for s in r[:3]:
        lines.append(f"{s['rank']}位 {_with_month(s)}：{s['message']}")
    lines.append("")
    lines.append(" / ".join(f"{s['rank']}位{s['name']}×{SIGN_MONTH[s['key']]}月" for s in r[3:]))
    lines += ["", "あなたは何位でしたか？", COMMENT_CALL, _style(fortune)["tags_threads"]]
    return "\n".join(lines)[:500]


def threads_reply(fortune: dict, site_url: str) -> str:
    return f"{_style(fortune)['reply']}\n{site_url}"


def threads_noon(fortune: dict) -> str:
    """お昼の短い投稿（文章だけ）。1行目に日付を入れる（二重投稿チェックが1行目で判定するため）。"""
    d = date.fromisoformat(fortune["date"])
    ev = koyomi.events(d)
    if ev:
        names = "・".join(n for n, _ in ev[:2])
        why = f"今日は{names}。{ev[0][1]}です。"
    else:
        kan, yomi = koyomi.kanshi(d)
        why = f"今日の干支は{kan}（{yomi}）。"
    # 絵文字は最後の呼びかけ『🌙』の1つだけにするため、見出しには付けない
    lines = [f"{d.month}/{d.day}（{'月火水木金土日'[d.weekday()]}）{fortune['hook']}", why,
             f"そんな今日、{fortune['title']}", ""]
    lines += [f"第{s['rank']}位　{s['month']}月生まれ：{s['message']}" for s in fortune["ranking"]]
    lines += ["", fortune["call"], "#誕生月占い"]
    return "\n".join(lines)[:500]


NOON_REPLY = LINE_GUIDE


def instagram_caption(fortune: dict, site_name: str) -> str:
    """Instagram: 上限2200字。本文のリンクは押せないのでプロフィールへ誘導。"""
    lines = [_head(fortune), f"{_label(fortune)}：{fortune['theme']}", _koyomi(fortune), ""]
    for s in fortune["ranking"]:
        lines.append(f"{s['rank']}位 {_with_month(s)}")
        lines.append(s["message"])
        lines.append(f"ラッキー：{s['lucky_item']}／{s['lucky_color']}")
        lines.append("")
    lines += [COMMENT_CALL, "",
              "ひかりの無料鑑定を受け付けています。", "",
              "お受け取り方法はこちら",
              "① ひかり（@hoshiyomi_koi）をフォロー",
              "② プロフィールのリンクから公式LINEを追加", "",
              "保存して、毎日のヒントにしてくださいね。", "", _style(fortune)["tags_ig"]]
    return "\n".join(lines)[:2200]
