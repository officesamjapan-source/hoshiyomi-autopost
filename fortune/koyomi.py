"""暦（こよみ）の計算。インターネットや外部サービスは使わず、計算だけで出す。

- 日の干支（四柱推命の「日柱」と同じ）
- 吉日：天赦日・一粒万倍日・己巳の日・巳の日・寅の日・甲子の日・天一天上
- 新月・満月、二十四節気

太陽と月の位置は簡易式（誤差は数分〜数十分）で計算する。
境目ぎりぎりの日だけ、暦の本と1日ずれることがありうる。
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
STEM_YOMI = ["きのえ", "きのと", "ひのえ", "ひのと", "つちのえ", "つちのと", "かのえ", "かのと", "みずのえ", "みずのと"]
BRANCH_YOMI = ["ね", "うし", "とら", "う", "たつ", "み", "うま", "ひつじ", "さる", "とり", "いぬ", "い"]

# 2000年1月1日は戊午（60干支の55番目＝0始まりで54）
_ANCHOR = date(2000, 1, 1)
_ANCHOR_INDEX = 54

# 二十四節気（太陽の黄経 0° = 春分 から 15° ごと）
SOLAR_TERMS = ["春分", "清明", "穀雨", "立夏", "小満", "芒種", "夏至", "小暑", "大暑", "立秋", "処暑", "白露",
               "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至", "小寒", "大寒", "立春", "雨水", "啓蟄"]
_TERM_NOTE = {
    "立春": "暦の上で春が始まる日", "春分": "昼と夜の長さがほぼ同じになる日",
    "立夏": "暦の上で夏が始まる日", "夏至": "一年でいちばん昼が長い日",
    "立秋": "暦の上で秋が始まる日", "秋分": "昼と夜の長さがほぼ同じになる日",
    "立冬": "暦の上で冬が始まる日", "冬至": "一年でいちばん夜が長い日",
}

# 一粒万倍日：節月（0 = 立春〜、1 = 啓蟄〜 … 11 = 小寒〜）ごとの十二支
_ICHIRYU = {0: "丑午", 1: "酉寅", 2: "子卯", 3: "卯辰", 4: "巳午", 5: "酉午",
            6: "子未", 7: "卯申", 8: "酉午", 9: "酉戌", 10: "亥子", 11: "卯子"}
# 天赦日：季節（節月で判定）ごとの干支
_TENSHA = {0: "戊寅", 1: "戊寅", 2: "戊寅", 3: "甲午", 4: "甲午", 5: "甲午",
           6: "戊申", 7: "戊申", 8: "戊申", 9: "甲子", 10: "甲子", 11: "甲子"}


# ---------------- 干支 ----------------
def kanshi_index(day: date) -> int:
    return (_ANCHOR_INDEX + (day - _ANCHOR).days) % 60


def kanshi(day: date) -> tuple[str, str]:
    """(漢字, 読み) 例: ("癸巳", "みずのとみ")"""
    i = kanshi_index(day)
    return STEMS[i % 10] + BRANCHES[i % 12], STEM_YOMI[i % 10] + BRANCH_YOMI[i % 12]


# ---------------- 太陽と月の位置 ----------------
def _jd(dt: datetime) -> float:
    """ユリウス日（UTC）。"""
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp() / 86400.0 + 2440587.5


def sun_longitude(dt: datetime) -> float:
    t = (_jd(dt) - 2451545.0) / 36525
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m) + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * t)
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega)) % 360


def moon_longitude(dt: datetime) -> float:
    t = (_jd(dt) - 2451545.0) / 36525
    lp = 218.3164477 + 481267.88123421 * t
    d = math.radians(297.8501921 + 445267.1114034 * t)
    m = math.radians(357.5291092 + 35999.0502909 * t)
    mp = math.radians(134.9633964 + 477198.8675055 * t)
    f = math.radians(93.2720950 + 483202.0175233 * t)
    lon = (lp + 6.288774 * math.sin(mp) + 1.274027 * math.sin(2 * d - mp) + 0.658314 * math.sin(2 * d)
           + 0.213618 * math.sin(2 * mp) - 0.185116 * math.sin(m) - 0.114332 * math.sin(2 * f)
           + 0.058793 * math.sin(2 * d - 2 * mp) + 0.057066 * math.sin(2 * d - m - mp)
           + 0.053322 * math.sin(2 * d + mp) + 0.045758 * math.sin(2 * d - m)
           - 0.040923 * math.sin(m - mp) - 0.034720 * math.sin(d) - 0.030383 * math.sin(m + mp))
    return lon % 360


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=JST)
    return start, start + timedelta(days=1)


def setsu_month(day: date) -> int:
    """節月。0 = 寅月（立春〜）… 9 = 亥月（立冬〜）、10 = 子月（大雪〜）、11 = 丑月（小寒〜）。
    節入りの日は新しい月として数える（その日の終わりの太陽の位置で判定）。"""
    _, end = _day_bounds(day)
    return int(((sun_longitude(end) - 315) % 360) // 30)


def solar_term(day: date) -> str | None:
    """その日（日本時間）に二十四節気が始まるなら名前を返す。"""
    start, end = _day_bounds(day)
    a, b = sun_longitude(start), sun_longitude(end)
    if b < a:
        b += 360
    ka, kb = int(a // 15), int(b // 15)
    return SOLAR_TERMS[kb % 24] if kb != ka else None


def moon_phase(day: date) -> str | None:
    """その日（日本時間）に新月・満月の瞬間があれば "新月" / "満月"。"""
    start, end = _day_bounds(day)
    e1 = (moon_longitude(start) - sun_longitude(start)) % 360
    e2 = (moon_longitude(end) - sun_longitude(end)) % 360
    if e1 > 300 and e2 < 60:
        return "新月"
    if e1 < 180 <= e2:
        return "満月"
    return None


# ---------------- 吉日・暦のできごと ----------------
def events(day: date) -> list[tuple[str, str]]:
    """その日の暦のできごと（名前, ひと言）。大事なものから順に並べる。"""
    i = kanshi_index(day)
    kan, _ = kanshi(day)
    branch = BRANCHES[i % 12]
    sm = setsu_month(day)
    out: list[tuple[str, str]] = []
    if _TENSHA[sm] == kan:
        out.append(("天赦日", "暦の上でいちばんの吉日と言われる日"))
    if branch in _ICHIRYU[sm]:
        out.append(("一粒万倍日", "始めたことが大きく実ると言われる日"))
    if kan == "己巳":
        out.append(("己巳の日", "60日に一度の、弁財天さまの特別なご縁日"))
    elif branch == "巳":
        out.append(("巳の日", "弁財天さまのご縁日"))
    if branch == "寅":
        out.append(("寅の日", "金運招来の日と言われる日"))
    if kan == "甲子":
        out.append(("甲子の日", "60日に一度の、始まりの日"))
    phase = moon_phase(day)
    if phase == "新月":
        out.append(("新月", "新しい願いごとを始めるのにぴったりのタイミング"))
    elif phase == "満月":
        out.append(("満月", "感謝と手放しにぴったりのタイミング"))
    term = solar_term(day)
    if term:
        out.append((term, _TERM_NOTE.get(term, "季節の節目")))
    if 29 <= i <= 44:  # 癸巳〜戊申の16日間
        out.append(("天一天上", "どの方角へ出かけても良いと言われる期間"))
    return out


def koyomi_line(day: date) -> str:
    """投稿に入れる1行。吉日があれば吉日、なければその日の干支。"""
    ev = events(day)
    if ev:
        names = "・".join(n for n, _ in ev[:3])
        return f"📅今日の暦：{names}（{ev[0][1]}）"
    kan, yomi = kanshi(day)
    return f"📅今日の干支：{kan}（{yomi}）"
