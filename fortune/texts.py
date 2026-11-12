"""SNS ごとの投稿文を作る（文字数制限に合わせる）。テーマ（総合運/恋愛運）で言葉とタグを変える。"""
from __future__ import annotations

from datetime import date

STYLE = {
    "general": {
        "icon": "🔮",
        "tags_x": "#今日の運勢 #星座占い",
        "tags_threads": "#星座占い",
        "tags_ig": ("#今日の運勢 #星座占い #12星座 #占い #星占い #運勢 #星よみ "
                    "#開運 #ラッキーアイテム #ラッキーカラー #占い好きな人と繋がりたい"),
        "reply": ("星座占いは、毎日のちいさなヒント。\n"
                  "あなただけの運命の流れをじっくり読み解くなら、生年月日から占う「四柱推命」で🔮\n"
                  "星よみPLANETはこちら👇"),
    },
    "love": {
        "icon": "🌙",
        "tags_x": "#恋愛運 #星座占い",
        "tags_threads": "#恋愛運",
        "tags_ig": ("#恋愛運 #今日の恋愛運 #星座占い #12星座 #恋愛占い #占い #片思い "
                    "#恋愛 #星占い #開運 #占い好きな人と繋がりたい"),
        "reply": ("あの人との相性、恋が動く時期をじっくり知りたい方へ。\n"
                  "生年月日から読み解く「四柱推命」の鑑定は星よみPLANETで🌙\n"
                  "こちらからどうぞ👇"),
    },
}


# Threads / Instagram の投稿に入れる呼びかけ（コメントには replies.py が自動返信する）
COMMENT_CALL = "星座か誕生月をコメントしてくれたら、ひかりがひと言お返事します🌙"


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


def threads_post(fortune: dict) -> str:
    """Threads: 上限500字。"""
    r = fortune["ranking"]
    lines = [_head(fortune), f"{_label(fortune)}：{fortune['theme']}", ""]
    for s in r[:3]:
        lines.append(f"{s['rank']}位 {s['symbol']}{s['name']}：{s['message']}")
    lines.append("")
    lines.append(" / ".join(f"{s['rank']}位{s['name']}" for s in r[3:]))
    lines += ["", "あなたは何位でしたか？", COMMENT_CALL, _style(fortune)["tags_threads"]]
    return "\n".join(lines)[:500]


def threads_reply(fortune: dict, site_url: str) -> str:
    return f"{_style(fortune)['reply']}\n{site_url}"


def instagram_caption(fortune: dict, site_name: str) -> str:
    """Instagram: 上限2200字。本文のリンクは押せないのでプロフィールへ誘導。"""
    lines = [_head(fortune), f"{_label(fortune)}：{fortune['theme']}", ""]
    for s in fortune["ranking"]:
        lines.append(f"{s['rank']}位 {s['symbol']}{s['name']}")
        lines.append(s["message"])
        lines.append(f"ラッキー：{s['lucky_item']}／{s['lucky_color']}")
        lines.append("")
    lines += [COMMENT_CALL, "",
              "星座占いは毎日のちいさなヒント。",
              f"あなただけの運命をじっくり読み解く「四柱推命」の鑑定は「{site_name}」で{_style(fortune)['icon']}",
              "プロフィールのリンクからどうぞ",
              "保存して毎朝チェックしてね✨", "", _style(fortune)["tags_ig"]]
    return "\n".join(lines)[:2200]
