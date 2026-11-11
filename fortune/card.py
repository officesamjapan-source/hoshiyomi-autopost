"""ランキング画像（1080x1350, Instagram の縦長サイズ）を作る。"""
from __future__ import annotations

import os
import random
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
# テーマごとの背景色（上, 下）。恋愛運はピンク寄りにしてアカウントの見た目を分ける
BACKGROUNDS = {
    "general": ((18, 16, 54), (58, 34, 98)),
    "love": ((54, 14, 52), (122, 40, 88)),
}
GOLD = (240, 206, 120)
WHITE = (245, 242, 255)
SUB = (190, 182, 225)
ROW_BG = (255, 255, 255, 22)

FONT_CANDIDATES = [
    os.environ.get("FONT_PATH", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError("日本語フォントが見つかりません。FONT_PATH を設定してください。")


def _background(day: date, kind: str) -> Image.Image:
    top, bottom = BACKGROUNDS.get(kind, BACKGROUNDS["general"])
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=color)
    rng = random.Random(day.isoformat())
    for _ in range(140):  # 星
        x, y = rng.randrange(W), rng.randrange(H)
        r = rng.choice([1, 1, 1, 2, 2, 3])
        a = rng.randrange(120, 255)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(a, a, min(255, a + 15)))
    return img


def make_card(fortune: dict, out_path: Path, site_name: str) -> Path:
    day = date.fromisoformat(fortune["date"])
    img = _background(day, fortune.get("kind", "general")).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    draw = ImageDraw.Draw(img)

    weekday = "月火水木金土日"[day.weekday()]
    draw.text((W // 2, 70), f"{day.month}月{day.day}日（{weekday}）", font=_font(40), fill=SUB, anchor="mm")
    draw.text((W // 2, 140), fortune["title"], font=_font(68), fill=GOLD, anchor="mm")
    draw.text((W // 2, 210), fortune["theme"], font=_font(32), fill=WHITE, anchor="mm")

    top, row_h, left, right = 262, 82, 50, W - 50
    f_rank, f_name, f_short, f_lucky = _font(40), _font(38), _font(30), _font(22)
    for i, s in enumerate(fortune["ranking"]):
        y = top + i * row_h
        od.rounded_rectangle([left, y + 4, right, y + row_h - 4], radius=18, fill=ROW_BG)
        img.alpha_composite(overlay)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        draw = ImageDraw.Draw(img)
        cy = y + row_h // 2
        rank_color = GOLD if s["rank"] <= 3 else WHITE
        draw.text((left + 70, cy), f"{s['rank']}位", font=f_rank, fill=rank_color, anchor="mm")
        draw.text((left + 140, cy), s["name"], font=f_name, fill=WHITE, anchor="lm")
        draw.text((left + 330, cy - 14), s["short"], font=f_short, fill=WHITE, anchor="lm")
        draw.text((left + 330, cy + 22), f"ラッキー：{s['lucky_item']}／{s['lucky_color']}",
                  font=f_lucky, fill=SUB, anchor="lm")

    draw.text((W // 2, H - 48), f"詳しい運勢は「{site_name}」で", font=_font(34), fill=GOLD, anchor="mm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Instagram の API は JPEG しか受け付けないため JPEG で保存する
    img.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path
