"""今日の12星座ランキングを作る（テーマ: 総合運 / 恋愛運）。

順位は日付とテーマから決まる乱数で決定（同じ日・同じテーマなら何度実行しても同じ結果）。
文章は ANTHROPIC_API_KEY があれば Claude が書き、なければテンプレートで作る。
"""
from __future__ import annotations

import json
import os
import random
from datetime import date

SIGNS = [
    ("aries", "牡羊座", "♈"),
    ("taurus", "牡牛座", "♉"),
    ("gemini", "双子座", "♊"),
    ("cancer", "蟹座", "♋"),
    ("leo", "獅子座", "♌"),
    ("virgo", "乙女座", "♍"),
    ("libra", "天秤座", "♎"),
    ("scorpio", "蠍座", "♏"),
    ("sagittarius", "射手座", "♐"),
    ("capricorn", "山羊座", "♑"),
    ("aquarius", "水瓶座", "♒"),
    ("pisces", "魚座", "♓"),
]

THEMES = {
    "general": {
        "title": "今日の12星座ランキング",
        "focus": "総合運",
        "default_theme": "星のメッセージを受け取って、すてきな一日を",
    },
    "love": {
        "title": "今日の恋愛運ランキング",
        "focus": "恋愛運（片思い中・恋人がいる・出会いを探している、どの人にも当てはまる助言にする）",
        "default_theme": "ときめきは、いつもの毎日の中に",
    },
}

MODEL = "claude-opus-5-5"


def rank_signs(day: date, theme: str) -> list[tuple[str, str, str]]:
    """日付＋テーマ＋任意のソルトから順位を決める。"""
    salt = os.environ.get("RANKING_SALT") or "hoshiyomi-planet"
    rng = random.Random(f"{salt}-{theme}-{day.isoformat()}")
    order = SIGNS[:]
    rng.shuffle(order)
    return order


# ---------- テンプレート（API キーがないとき用） ----------
_TEMPLATES = {
    "general": {
        "high": [
            ("直感が冴える日。思い切った行動が幸運を呼びます", "直感を信じて前進"),
            ("周りからの評価が上がる日。積極的に発言してみて", "あなたの声が届く日"),
            ("うれしい知らせが届きそう。笑顔を忘れずに", "うれしい知らせの予感"),
            ("新しい出会いにチャンスあり。いつもと違う道を選んで", "出会いが運を開く"),
        ],
        "mid": [
            ("コツコツ進めたことが形になる日。焦らずマイペースで", "マイペースが吉"),
            ("身の回りを整えると運気アップ。デスクの片付けから", "整理整頓で運気UP"),
            ("人の話をよく聞くとヒントが見つかります", "聞き上手がカギ"),
            ("小さなご褒美で気分転換を。午後から流れが良くなります", "午後から好調"),
            ("いつもの道を少し変えると、思わぬ発見がありそう", "寄り道に発見あり"),
            ("ていねいな挨拶が信頼を呼ぶ日。笑顔を添えて", "挨拶が運を呼ぶ"),
        ],
        "low": [
            ("無理は禁物。今日は早めに休んでエネルギーを充電して", "休息で充電を"),
            ("うっかりミスに注意。確認をていねいにすれば大丈夫", "確認をていねいに"),
            ("言葉選びは慎重に。やさしい一言が運気を守ります", "やさしい言葉が吉"),
        ],
    },
    "love": {
        "high": [
            ("気になる人との距離が縮まる日。自分から一言かけてみて", "一言が距離を縮める"),
            ("魅力が自然に伝わる日。いつもより少しおしゃれをして", "魅力が輝く日"),
            ("思いがけない場所で素敵な出会いの予感", "出会いの予感"),
            ("パートナーと気持ちが通じ合う日。感謝を言葉にして", "感謝が愛を深める"),
        ],
        "mid": [
            ("焦らず自然体が一番。笑顔があなたの魅力を引き出します", "自然体が魅力"),
            ("相手の話にじっくり耳を傾けると関係が深まります", "聞く姿勢がカギ"),
            ("小さな気づかいが好印象に。メッセージは短く温かく", "小さな気づかいを"),
            ("自分磨きに向く日。好きなことに夢中な姿が魅力に", "自分磨きが吉"),
            ("友だちとの何気ない会話に、恋のヒントがありそう", "会話にヒント"),
        ],
        "low": [
            ("すれ違いに注意。返事を急がずゆっくり向き合って", "急がずゆっくり"),
            ("今日は自分をいたわる日。心に余裕が生まれれば流れも好転", "自分をいたわって"),
            ("思い込みは禁物。気になることは素直に聞いてみて", "素直さがカギ"),
        ],
    },
}
_DAY_THEMES = {
    "general": [
        "星のメッセージを受け取って、すてきな一日を",
        "小さな一歩が、明日の流れをつくる日",
        "迷ったときは、心が軽くなるほうへ",
        "あなたのペースが、いちばんの近道",
        "ていねいに過ごすほど、運が味方する日",
        "いつもの景色に、ヒントが隠れています",
        "がんばりすぎない日が、運を整えます",
    ],
    "love": [
        "ときめきは、いつもの毎日の中に",
        "素直な一言が、距離を縮める日",
        "自分を大切にすると、恋も輝きます",
        "小さな勇気が、ときめきを連れてくる",
        "やさしさが、ちゃんと伝わる日",
    ],
}
_ITEMS = ["ハンカチ", "手帳", "ミントガム", "腕時計", "観葉植物", "温かい紅茶",
          "イヤホン", "キーホルダー", "リップクリーム", "チョコレート", "ブックカバー", "折りたたみ傘"]
_COLORS = ["ラベンダー", "ネイビー", "ゴールド", "ミントグリーン", "コーラルピンク", "シルバー",
           "ホワイト", "ワインレッド", "スカイブルー", "ベージュ", "オレンジ", "ブラウン"]


def _template_texts(order, day: date, theme: str) -> dict:
    rng = random.Random(f"text-{theme}-{day.isoformat()}")
    items = rng.sample(_ITEMS, 12)
    colors = rng.sample(_COLORS, 12)
    # 同じ日に同じ文が重ならないよう、段階ごとにシャッフルして順に使う
    pools = {tier: rng.sample(lst, len(lst)) for tier, lst in _TEMPLATES[theme].items()}
    used = {tier: 0 for tier in pools}
    result = {}
    for i, (key, _, _) in enumerate(order):
        tier = "high" if i < 4 else ("mid" if i < 9 else "low")
        pool = pools[tier]
        message, short = pool[used[tier] % len(pool)]
        used[tier] += 1
        result[key] = {"message": message, "short": short,
                       "lucky_item": items[i], "lucky_color": colors[i]}
    return {"theme": rng.choice(_DAY_THEMES[theme]), "signs": result}


# ---------- Claude で文章を作る ----------
_SCHEMA = {
    "type": "object",
    "properties": {
        "theme": {"type": "string"},
        "signs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "message": {"type": "string"},
                    "short": {"type": "string"},
                    "lucky_item": {"type": "string"},
                    "lucky_color": {"type": "string"},
                },
                "required": ["key", "message", "short", "lucky_item", "lucky_color"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["theme", "signs"],
    "additionalProperties": False,
}


def _claude_texts(order, day: date, theme: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    focus = THEMES[theme]["focus"]
    ranking = "\n".join(f"{i + 1}位: {name}（key={key}）" for i, (key, name, _) in enumerate(order))
    prompt = f"""あなたは占いサイト「星よみPLANET」の占い師です。
{day.year}年{day.month}月{day.day}日の12星座「{focus}」ランキングは次のとおりです（順位は確定済みなので変えないこと）。

{ranking}

各星座について、SNS投稿用に次を日本語で書いてください。
- message: 今日の{focus}。30〜40文字。順位に合ったトーンで、下位でも前向きな助言で締める
- short: 画像用の一言。12文字以内
- lucky_item: ラッキーアイテム。8文字以内
- lucky_color: ラッキーカラー。8文字以内
- theme: 全体の今日のテーマ。25文字以内

毎日読まれるので、ありきたりな定型句の繰り返しは避け、季節感（{day.month}月）を少し入れてください。
断定的な不安をあおる表現、健康・お金についての具体的な断言は避けてください。"""

    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Claude の応答が完了しませんでした: stop_reason={response.stop_reason}")
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    signs = {s["key"]: s for s in data["signs"]}
    missing = [key for key, _, _ in order if key not in signs]
    if missing:
        raise RuntimeError(f"Claude の応答に星座が足りません: {missing}")
    return {"theme": data["theme"], "signs": signs}


def build_fortune(day: date, theme: str = "general") -> dict:
    if theme not in THEMES:
        raise ValueError(f"未対応のテーマ: {theme}（{', '.join(THEMES)} のどれか）")
    order = rank_signs(day, theme)
    texts = None
    source = "template"
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            texts = _claude_texts(order, day, theme)
            source = "claude"
        except Exception as e:  # 文章生成に失敗しても投稿は止めない
            print(f"[warn] Claude での文章生成に失敗したためテンプレートを使います: {e}")
    if texts is None:
        texts = _template_texts(order, day, theme)

    ranking = []
    for i, (key, name, symbol) in enumerate(order):
        t = texts["signs"][key]
        ranking.append({
            "rank": i + 1, "key": key, "name": name, "symbol": symbol,
            "message": t["message"], "short": t["short"],
            "lucky_item": t["lucky_item"], "lucky_color": t["lucky_color"],
        })
    return {
        "date": day.isoformat(), "kind": theme, "title": THEMES[theme]["title"],
        "theme": texts["theme"], "source": source, "ranking": ranking,
    }
