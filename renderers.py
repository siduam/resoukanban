import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import PROJECT_ROOT, Settings
from data_sources import WeatherData
from nba import TZ


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


NBA_LIST_TOP = 44
NBA_LIST_BOTTOM = 286
NBA_CUTOFF_HOUR = 15

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


def nba_display_date(now: dt.datetime) -> dt.date:
    """15:00 前显示当天，15:00 起显示次日预告。"""
    if now.hour >= NBA_CUTOFF_HOUR:
        return now.date() + dt.timedelta(days=1)
    return now.date()


def _nba_start_at(game: Dict[str, Any]) -> dt.datetime:
    try:
        start = dt.datetime.fromisoformat(
            str(game.get("start", "")).replace("Z", "+00:00")
        )
        return start.astimezone(TZ)
    except (ValueError, TypeError):
        return dt.datetime.max.replace(tzinfo=dt.timezone.utc)


def _nba_start_text(game: Dict[str, Any]) -> str:
    start = _nba_start_at(game)
    if start.year == 9999:
        return "待定"
    return start.strftime("%H:%M")


def _nba_sizes(count: int) -> Tuple[int, int, int]:
    if count <= 4:
        return 34, 18, 13
    if count <= 6:
        return 30, 17, 12
    available = NBA_LIST_BOTTOM - NBA_LIST_TOP
    row_h = max(16, min(28, available // max(1, count)))
    if row_h >= 26:
        return row_h, 16, 12
    if row_h >= 22:
        return row_h, 15, 12
    if row_h >= 19:
        return row_h, 14, 12
    if row_h >= 17:
        return row_h, 13, 11
    return row_h, 12, 11


def _nba_next_matchday(days: Dict[str, List[Dict[str, Any]]], after: str):
    for key in sorted(key for key in days if key > after):
        if days[key]:
            return key
    return None


def render_nba_page(
    data: Dict[str, Any],
    now: Optional[dt.datetime],
    font_path: Path,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """绘制 NBA 全天赛程页，返回 (图片, 信息)。

    15:00 前显示当天全部比赛（已结束显示比分、直播中显示比分和“进行中”、
    未开始显示 vs），15:00 起显示次日赛程预告。场次多时自动压缩行高，
    15 场也能完整放下。
    """
    now = now or dt.datetime.now(TZ)
    target = nba_display_date(now)
    days = {
        str(item.get("date")): item.get("games") or []
        for item in (data.get("days") or [])
    }
    games = sorted(days.get(target.isoformat(), []), key=_nba_start_at)
    label = "今日" if target == now.date() else "明日"

    def font(size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(font_path), size)

    image = new_mono_canvas()
    draw = mono_draw(image)

    logo = _nba_logo()
    if logo is not None:
        image.paste(logo, (12, 10))
    else:
        draw.text((12, 12), "NBA", font=font(14), fill=0)

    header = "%d月%02d日 %s · %s %d 场" % (
        target.month,
        target.day,
        ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][target.weekday()],
        label,
        len(games),
    )
    draw.text((62, 14), header, font=font(14), fill=0)
    draw.text(
        (388, 15),
        "更新 %s" % now.strftime("%H:%M"),
        font=font(11),
        fill=0,
        anchor="ra",
    )
    draw.line((12, 38, 388, 38), fill=0, width=1)

    if not games:
        title = "明日无比赛" if label == "明日" else "今日无比赛"
        draw.text((200, 120), title, font=font(22), fill=0, anchor="mm")
        next_key = _nba_next_matchday(days, target.isoformat())
        if next_key:
            next_date = dt.date.fromisoformat(next_key)
            next_label = {1: "明日", 2: "后天"}.get(
                (next_date - now.date()).days,
                next_date.strftime("%m-%d"),
            )
            next_games = days[next_key]
            draw.text(
                (200, 168),
                "下一比赛日 %s · 共 %d 场" % (next_label, len(next_games)),
                font=font(15),
                fill=0,
                anchor="mm",
            )
            draw.text(
                (200, 196),
                "首场 %s · 北京时间" % _nba_start_text(min(next_games, key=_nba_start_at)),
                font=font(12),
                fill=0,
                anchor="mm",
            )
        else:
            draw.text((200, 168), "暂无后续赛程", font=font(15), fill=0, anchor="mm")
        return image, {"date": target, "label": label, "count": 0}

    row_h, name_px, meta_px = _nba_sizes(len(games))
    name_font = font(name_px)
    meta_font = font(meta_px)
    badge_font = font(max(9, meta_px - 1))
    block_h = len(games) * row_h
    list_bottom = 270 if len(games) <= 6 else NBA_LIST_BOTTOM
    top = NBA_LIST_TOP + max(0, (list_bottom - NBA_LIST_TOP - block_h) // 2)

    for index, game in enumerate(games):
        center_y = top + index * row_h + row_h // 2
        draw.text(
            (14, center_y),
            _nba_start_text(game),
            font=meta_font,
            fill=0,
            anchor="lm",
        )
        draw.text(
            (150, center_y),
            _fit(draw, game.get("away"), name_font, 88),
            font=name_font,
            fill=0,
            anchor="rm",
        )
        draw.text(
            (250, center_y),
            _fit(draw, game.get("home"), name_font, 88),
            font=name_font,
            fill=0,
            anchor="lm",
        )

        if game.get("state") == "scheduled":
            draw.text((200, center_y), "vs", font=meta_font, fill=0, anchor="mm")
        else:
            draw.text(
                (200, center_y),
                "%s-%s" % (game.get("away_score", "-"), game.get("home_score", "-")),
                font=name_font,
                fill=0,
                anchor="mm",
            )
            if game.get("state") == "live":
                badge_text = "进行中"
                badge_width = int(draw.textlength(badge_text, font=badge_font)) + 8
                badge_height = max(12, row_h - 3)
                left = 388 - badge_width
                draw.rounded_rectangle(
                    (left, center_y - badge_height // 2, 388, center_y + badge_height // 2),
                    radius=2,
                    fill=0,
                )
                draw.text(
                    (left + badge_width / 2, center_y),
                    badge_text,
                    font=badge_font,
                    fill=255,
                    anchor="mm",
                )

    if len(games) <= 6:
        draw.text(
            (200, 282),
            "以上时间均为北京时间",
            font=font(11),
            fill=0,
            anchor="mm",
        )

    return image, {"date": target, "label": label, "count": len(games)}
