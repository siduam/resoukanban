import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import PROJECT_ROOT, Settings
from data_sources import WeatherData
from nba import TZ, build_state, minutes_to_start


CANVAS_SIZE = (400, 300)


@dataclass(frozen=True)
class Fonts:
    title: ImageFont.FreeTypeFont
    item: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont
    weather_title: ImageFont.FreeTypeFont
    weather_item: ImageFont.FreeTypeFont
    weather_small: ImageFont.FreeTypeFont
    temperature: ImageFont.FreeTypeFont
    weather: ImageFont.FreeTypeFont


def load_fonts(font_path: Path) -> Fonts:
    if not font_path.exists():
        raise FileNotFoundError(f"找不到字体文件: {font_path}")

    def font(size, scale=1):
        return ImageFont.truetype(str(font_path), size * scale)

    return Fonts(
        title=font(21),
        item=font(15),
        small=font(12),
        weather_title=font(24),
        weather_item=font(18),
        weather_small=font(14),
        temperature=font(48),
        weather=font(36),
    )


def new_mono_canvas():
    return Image.new("1", CANVAS_SIZE, color=1)


def mono_draw(image: Image.Image):
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"
    return draw


def wrap_text_by_pixels(draw, text: str, font, max_width: int) -> List[str]:
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        try:
            width = draw.textlength(test_line, font=font)
        except AttributeError:
            width = draw.textbbox((0, 0), test_line, font=font)[2]

        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)
    return lines


def _draw_hotlist_page(draw, page_title, items, start_index, fonts):
    draw.rounded_rectangle([(10, 10), (390, 42)], radius=8, fill=0)
    draw.text((20, 15), page_title, font=fonts.title, fill=255)

    y = 50
    last_index = start_index
    item_gap = 8
    line_height = 20
    badge_size = 21

    for index in range(start_index, len(items)):
        lines = wrap_text_by_pixels(draw, items[index], fonts.item, max_width=340)
        required_height = len(lines) * line_height
        if y + required_height > 295:
            break

        current_number = index + 1
        draw.rounded_rectangle([(10, y), (10 + badge_size, y + badge_size)], radius=5, fill=0)
        number_text = str(current_number)
        number_box = draw.textbbox((0, 0), number_text, font=fonts.small)
        number_width = number_box[2] - number_box[0]
        number_height = number_box[3] - number_box[1]
        draw.text(
            (
                10 + (badge_size - number_width) / 2,
                y + (badge_size - number_height) / 2 - 1,
            ),
            number_text,
            font=fonts.small,
            fill=255,
        )

        current_y = y + 1
        for line in lines:
            draw.text((45, current_y), line, font=fonts.item, fill=0)
            current_y += line_height

        y += max(badge_size, required_height) + item_gap
        last_index = index + 1
        if y < 290:
            draw.line([(45, y - item_gap / 2), (380, y - item_gap / 2)], fill=0)

    return last_index


def render_information_page(
    titles: List[str],
    page_title: str,
    start_index: int,
    fonts: Fonts,
) -> Tuple[Image.Image, int]:
    image = new_mono_canvas()
    draw = mono_draw(image)
    next_start = _draw_hotlist_page(
        draw,
        f"◆ {page_title}",
        titles,
        start_index,
        fonts,
    )
    if next_start == start_index:
        draw.text((45, 70), "暂无更多内容", font=fonts.item, fill=0)
    return image, next_start


def render_weather_dashboard(
    weather: WeatherData,
    settings: Settings,
    fonts: Fonts,
) -> Image.Image:
    image = new_mono_canvas()
    draw = mono_draw(image)

    if weather.temp_curr == 0 and not weather.forecasts:
        draw.text(
            (20, 50),
            "天气数据获取失败，请检查 API Key 或网络",
            font=fonts.weather_item,
            fill=0,
        )
        return image

    draw.text((20, 10), settings.city_display_name, font=fonts.weather_title, fill=0)
    time_text = f"更新: {weather.update_time}"
    time_box = draw.textbbox((0, 0), time_text, font=fonts.weather_small)
    time_width = time_box[2] - time_box[0]
    draw.text((390 - time_width, 12), time_text, font=fonts.weather_small, fill=0)

    draw.text((25, 40), f"{weather.temp_curr}°", font=fonts.temperature, fill=0)
    draw.text(
        (25, 100),
        f"{weather.temp_low}°/{weather.temp_high}°",
        font=fonts.weather_item,
        fill=0,
    )
    draw.text((150, 45), weather.weather, font=fonts.weather, fill=0)

    draw.rounded_rectangle([(235, 45), (385, 130)], radius=8, outline=0, fill=255)
    draw.text((255, 56), weather.wind_info, font=fonts.weather_small, fill=0)
    draw.text((255, 80), f"湿度 {weather.humidity}", font=fonts.weather_small, fill=0)
    draw.text((255, 104), f"体感 {weather.feel_temp}", font=fonts.weather_small, fill=0)

    draw.text(
        (25, 135),
        f"日出 {weather.sunrise}   日落 {weather.sunset}",
        font=fonts.weather_item,
        fill=0,
    )
    draw.line([(20, 160), (380, 160)], fill=0)

    for x, forecast in zip([30, 200], weather.forecasts[:2]):
        draw.text((x, 175), forecast.date, font=fonts.weather_item, fill=0)
        draw.text((x, 200), forecast.weather, font=fonts.weather_item, fill=0)
        draw.text(
            (x, 220),
            f"{forecast.temp_low}°~{forecast.temp_high}°",
            font=fonts.weather_item,
            fill=0,
        )

    draw.line([(20, 250), (380, 250)], fill=0)
    life_index_text = (
        f"紫外线: {weather.ultraviolet} | 舒适度: {weather.comfort}"
    )
    draw.text((20, 270), life_index_text, font=fonts.weather_item, fill=0)

    return image


# ---------------------------------------------------------------- NBA 看板


@dataclass(frozen=True)
class NbaFonts:
    title: ImageFont.FreeTypeFont
    team: ImageFont.FreeTypeFont
    code: ImageFont.FreeTypeFont
    score: ImageFont.FreeTypeFont
    detail: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont
    result_team: ImageFont.FreeTypeFont
    result_score: ImageFont.FreeTypeFont


def load_nba_fonts(font_path: Path) -> NbaFonts:
    if not font_path.exists():
        raise FileNotFoundError(f"找不到字体文件: {font_path}")

    def font(size):
        return ImageFont.truetype(str(font_path), size)

    return NbaFonts(
        title=font(15),
        team=font(17),
        code=font(11),
        score=font(27),
        detail=font(13),
        small=font(11),
        result_team=font(15),
        result_score=font(20),
    )


_NBA_LOGO: Optional[Image.Image] = None
_NBA_LOGO_TRIED = False


def _nba_logo() -> Optional[Image.Image]:
    """预渲染的 NBA 字标（由 assets/nba-script.svg 生成，避免运行期依赖 CairoSVG）。"""
    global _NBA_LOGO, _NBA_LOGO_TRIED
    if not _NBA_LOGO_TRIED:
        _NBA_LOGO_TRIED = True
        path = PROJECT_ROOT / "assets" / "nba-logo.png"
        try:
            with Image.open(path) as raw:
                _NBA_LOGO = raw.convert("L").point(
                    lambda value: 0 if value < 128 else 255,
                    mode="1",
                )
        except OSError:
            _NBA_LOGO = None
    return _NBA_LOGO


def _fit(draw, text, text_font, width):
    text = str(text or "")
    if draw.textlength(text, font=text_font) <= width:
        return text
    while text and draw.textlength(text + "…", font=text_font) > width:
        text = text[:-1]
    return text + "…"


def _draw_left_centered(draw, xy, text, text_font, fill, max_width):
    left, top, right, bottom = xy
    label = _fit(draw, text, text_font, max_width or right - left)
    bbox = draw.textbbox((0, 0), label, font=text_font)
    y = (top + bottom - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((left, y), label, font=text_font, fill=fill)


def _draw_right_centered(draw, xy, text, text_font, fill, max_width):
    left, top, right, bottom = xy
    label = _fit(draw, text, text_font, max_width or right - left)
    bbox = draw.textbbox((0, 0), label, font=text_font)
    y = (top + bottom - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((right, y), label, font=text_font, fill=fill, anchor="ra")


def _draw_recent_finals(draw, state, fonts, black, gray):
    label = (
        f"今日赛果 · 共 {len(state['recent_finals'])} 场"
        if state["status"] == "FINAL"
        else f"最近比赛日 · 共 {len(state['recent_finals'])} 场"
    )
    _draw_left_centered(draw, (44, 84, 356, 105), label, fonts.detail, black, 312)

    finals = state["recent_finals"]
    band_top, band_bottom = 112, 198
    row_h = {1: 44, 2: 38, 3: 28}.get(len(finals), 28)
    block_h = row_h * len(finals)
    row_top = band_top + max(0, (band_bottom - band_top - block_h) // 2)

    for index, game in enumerate(finals):
        y = row_top + index * row_h
        away = _fit(draw, game.get("away"), fonts.result_team, 88)
        home = _fit(draw, game.get("home"), fonts.result_team, 88)
        score = "%s : %s" % (
            game.get("away_score", "-"),
            game.get("home_score", "-"),
        )
        _draw_left_centered(draw, (44, y, 152, y + row_h - 4), away, fonts.result_team, black, 108)
        draw.text(
            (200, y + (row_h - 4) / 2),
            score,
            font=fonts.result_score,
            fill=black,
            stroke_width=1,
            anchor="mm",
        )
        _draw_right_centered(draw, (248, y, 356, y + row_h - 4), home, fonts.result_team, black, 108)
        if index < len(finals) - 1:
            draw.line((44, y + row_h - 2, 356, y + row_h - 2), fill=gray, width=1)


def render_nba_page(
    data: Dict[str, Any],
    date,
    fonts: NbaFonts,
    now: Optional[dt.datetime] = None,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """绘制 400×300 NBA 单页看板，返回图片与状态（LIVE/NEXT/FINAL/REST）。"""
    now = now or dt.datetime.now(TZ)
    image = new_mono_canvas()
    draw = mono_draw(image)
    black, white, gray = 0, 255, 0
    state = build_state(data, date, now)

    draw.rounded_rectangle((12, 12, 388, 288), radius=2, outline=black, width=2)

    logo = _nba_logo()
    if logo is not None:
        image.paste(logo, (18, 15))
    else:
        draw.text((18, 18), "NBA", font=fonts.title, fill=black)

    header_text = "%s %s NBA 赛程" % (
        date.strftime("%m月%d日"),
        ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()],
    )
    title_width = draw.textlength(header_text, font=fonts.title)
    draw.text((190 - title_width / 2, 17), header_text, font=fonts.title, fill=black)
    _draw_left_centered(
        draw, (310, 13, 382, 39), "更新 %s" % now.strftime("%H:%M"), fonts.small, black, 72
    )

    draw.line((14, 43, 386, 43), fill=black, width=1)

    focus = state["focus"]
    status = state["status"]
    status_zh = {
        "LIVE": "直播中",
        "NEXT": "未开始",
        "FINAL": "已结束",
        "REST": "休赛日",
    }[status]
    badge_right = 90 if status == "LIVE" else 82
    draw.rounded_rectangle((20, 51, badge_right, 73), radius=3, fill=black)
    draw.text(((20 + badge_right) / 2, 62), status_zh, font=fonts.small, fill=white, anchor="mm")
    type_text = "今日无比赛" if status == "REST" else "常规赛"
    _draw_left_centered(draw, (310, 51, 380, 73), type_text, fonts.small, black, 70)

    if status in {"FINAL", "REST"} and state["recent_finals"]:
        _draw_recent_finals(draw, state, fonts, black, gray)
    elif focus:
        _draw_left_centered(draw, (44, 84, 136, 108), focus.get("away"), fonts.team, black, 92)
        _draw_left_centered(draw, (44, 111, 136, 130), focus.get("away_code", "客"), fonts.code, black, 92)
        _draw_right_centered(draw, (264, 84, 356, 108), focus.get("home"), fonts.team, black, 92)
        _draw_right_centered(draw, (264, 111, 356, 130), focus.get("home_code", "主"), fonts.code, black, 92)

        if status == "NEXT":
            center = "@"
            detail = "今晚 %s · 北京时间" % focus.get("status", "待定")
            remaining = minutes_to_start(focus, now)
            sub = (
                "距开赛约 %02d小时%02d分" % (max(0, remaining) // 60, max(0, remaining) % 60)
                if remaining < 99999
                else "今日下一场比赛"
            )
        else:
            center = "%s  :  %s" % (
                focus.get("away_score", "-"),
                focus.get("home_score", "-"),
            )
            detail = focus.get("status", "比赛进行中") if status == "LIVE" else "全场结束"
            sub = {"LIVE": "当前直播比分", "FINAL": "今日最终赛果", "REST": "最近一场赛果"}[status]

        draw.text((200, 105), center, font=fonts.score, fill=black, stroke_width=1, anchor="mm")
        draw.text((200, 150), _fit(draw, detail, fonts.detail, 232), font=fonts.detail, fill=black, anchor="mm")
        draw.text((200, 176), _fit(draw, sub, fonts.small, 232), font=fonts.small, fill=black, anchor="mm")
    else:
        _draw_left_centered(draw, (84, 95, 316, 124), "今日暂无赛程", fonts.team, black, 232)
        _draw_left_centered(draw, (84, 137, 316, 158), "等待下一场比赛", fonts.detail, black, 232)

    draw.line((14, 202, 386, 202), fill=black, width=1)

    if status == "LIVE":
        next_games = [game for game in state["today"] if game["state"] == "scheduled"]
        aux = "NEXT  %s · 今日还有 %d 场" % (
            next_games[0].get("status", "待定") if next_games else "暂无",
            len(next_games),
        )
    elif status == "NEXT":
        aux = "TODAY  已结束 %d 场 · 下一场后还有 %d 场" % (
            sum(game["state"] == "final" for game in state["today"]),
            max(0, len(state["today"]) - 1),
        )
    else:
        # FINAL / REST：第三栏补全为「下一比赛日标签 · 开赛时间 · 共 N 场」，
        # 场次按北京开赛日分桶，避免 UTC 跨日误计。
        next_day = next(
            (
                day
                for day in sorted(
                    (item for item in (data.get("days") or []) if item["date"] > date.isoformat()),
                    key=lambda item: item["date"],
                )
                if day.get("games")
            ),
            None,
        )
        if next_day:
            next_date = dt.date.fromisoformat(next_day["date"])
            label = {1: "明日", 2: "后天"}.get((next_date - date).days, next_date.strftime("%m-%d"))

            def _start_key(game):
                value = game.get("status", "")
                return value if re.match(r"^\d{1,2}:\d{2}$", value) else "99:99"

            first = min(next_day["games"], key=_start_key)
            aux = "NEXT  %s · %s · 共 %d 场" % (label, first.get("status", "待定"), len(next_day["games"]))
        else:
            aux = "NEXT  暂无后续赛程"

    _draw_left_centered(draw, (22, 206, 378, 250), aux, fonts.detail, black, 356)

    draw.line((14, 250, 386, 250), fill=black, width=1)

    news = (data.get("news") or [{}])[0] or {}
    hot = "热点  %s · %s %s" % (
        news.get("title", "暂无最新中文资讯"),
        news.get("source", ""),
        news.get("age", ""),
    )
    _draw_left_centered(draw, (22, 254, 378, 286), hot, fonts.detail, black, 356)

    return image, state
