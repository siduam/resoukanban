from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import Settings
from data_sources import WeatherData


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
