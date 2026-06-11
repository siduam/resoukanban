from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import Settings
from data_sources import WeatherData, get_clothing_advice


CANVAS_SIZE = (400, 300)
RENDER_SCALE = 2
MONO_THRESHOLD = 176


@dataclass(frozen=True)
class Fonts:
    title: ImageFont.FreeTypeFont
    item: ImageFont.FreeTypeFont
    small: ImageFont.FreeTypeFont
    temperature: ImageFont.FreeTypeFont
    weather: ImageFont.FreeTypeFont


def load_fonts(font_path: Path) -> Fonts:
    if not font_path.exists():
        raise FileNotFoundError(f"找不到字体文件: {font_path}")

    def font(size):
        return ImageFont.truetype(str(font_path), size * RENDER_SCALE)

    return Fonts(
        title=font(24),
        item=font(18),
        small=font(14),
        temperature=font(48),
        weather=font(36),
    )


def new_canvas():
    size = tuple(dimension * RENDER_SCALE for dimension in CANVAS_SIZE)
    return Image.new("L", size, color=255)


def finish_canvas(image: Image.Image) -> Image.Image:
    image = image.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    return image.point(lambda pixel: 0 if pixel < MONO_THRESHOLD else 255, mode="1")


class ScaledDraw:
    def __init__(self, image: Image.Image):
        self.draw = ImageDraw.Draw(image)

    @staticmethod
    def _point(point):
        return tuple(value * RENDER_SCALE for value in point)

    @classmethod
    def _coordinates(cls, coordinates):
        return [cls._point(point) for point in coordinates]

    def text(self, position, text, **kwargs):
        return self.draw.text(self._point(position), text, **kwargs)

    def textlength(self, text, **kwargs):
        return self.draw.textlength(text, **kwargs) / RENDER_SCALE

    def textbbox(self, position, text, **kwargs):
        box = self.draw.textbbox(self._point(position), text, **kwargs)
        return tuple(value / RENDER_SCALE for value in box)

    def rounded_rectangle(self, coordinates, radius=0, width=1, **kwargs):
        return self.draw.rounded_rectangle(
            self._coordinates(coordinates),
            radius=radius * RENDER_SCALE,
            width=width * RENDER_SCALE,
            **kwargs,
        )

    def line(self, coordinates, width=1, **kwargs):
        return self.draw.line(
            self._coordinates(coordinates),
            width=width * RENDER_SCALE,
            **kwargs,
        )


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
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), page_title, font=fonts.title, fill=255)

    y = 55
    last_index = start_index
    item_gap = 12
    line_height = 23

    for index in range(start_index, len(items)):
        lines = wrap_text_by_pixels(draw, items[index], fonts.item, max_width=340)
        required_height = len(lines) * line_height
        if y + required_height > 295:
            break

        current_number = index + 1
        draw.rounded_rectangle([(10, y), (36, y + 24)], radius=6, fill=0)
        number_x = 18 if current_number < 10 else 11
        draw.text((number_x, y + 3), str(current_number), font=fonts.small, fill=255)

        current_y = y + 1
        for line in lines:
            draw.text((45, current_y), line, font=fonts.item, fill=0)
            current_y += line_height

        y += max(24, required_height) + item_gap
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
    image = new_canvas()
    next_start = _draw_hotlist_page(
        ScaledDraw(image),
        f"◆ {page_title}",
        titles,
        start_index,
        fonts,
    )
    if next_start == start_index:
        ScaledDraw(image).text((45, 70), "暂无更多内容", font=fonts.item, fill=0)
    return finish_canvas(image), next_start


def render_weather_dashboard(
    weather: WeatherData,
    settings: Settings,
    fonts: Fonts,
    now: datetime = None,
) -> Image.Image:
    image = new_canvas()
    draw = ScaledDraw(image)

    if weather.temp_curr == 0 and not weather.forecasts:
        draw.text(
            (20, 50),
            "天气数据获取失败，请检查 API Key 或网络",
            font=fonts.item,
            fill=0,
        )
        return finish_canvas(image)

    draw.text((20, 10), settings.city_display_name, font=fonts.title, fill=0)
    now = now or datetime.utcnow() + timedelta(hours=8)
    time_text = f"更新: {now.strftime('%H:%M')}"
    time_box = draw.textbbox((0, 0), time_text, font=fonts.small)
    time_width = time_box[2] - time_box[0]
    draw.text((390 - time_width, 12), time_text, font=fonts.small, fill=0)

    draw.text((25, 40), f"{weather.temp_curr}°C", font=fonts.temperature, fill=0)
    draw.text(
        (25, 100),
        f"{weather.temp_low}°/{weather.temp_high}°",
        font=fonts.item,
        fill=0,
    )
    draw.text((150, 45), weather.weather, font=fonts.weather, fill=0)

    draw.rounded_rectangle([(235, 45), (385, 130)], radius=8, outline=0, fill=0)
    draw.text((255, 56), weather.wind_info, font=fonts.small, fill=255)
    draw.text((255, 80), f"湿度 {weather.humidity}", font=fonts.small, fill=255)
    draw.text((255, 104), f"体感 {weather.feel_temp}", font=fonts.small, fill=255)

    draw.text(
        (25, 135),
        f"日出 {weather.sunrise}   日落 {weather.sunset}",
        font=fonts.item,
        fill=0,
    )
    draw.line([(20, 160), (380, 160)], fill=0)

    for x, forecast in zip([30, 200], weather.forecasts[:2]):
        draw.text((x, 175), forecast.date, font=fonts.item, fill=0)
        draw.text((x, 200), forecast.weather, font=fonts.item, fill=0)
        draw.text(
            (x, 220),
            f"{forecast.temp_low}°~{forecast.temp_high}°",
            font=fonts.item,
            fill=0,
        )

    advice = get_clothing_advice(weather.temp_curr)
    draw.line([(20, 250), (380, 250)], fill=0)
    advice_lines = [advice[index:index + 18] for index in range(0, len(advice), 18)]
    for index, line in enumerate(advice_lines[:2]):
        draw.text((20, 262 + index * 24), f"[衣] {line}", font=fonts.item, fill=0)

    return finish_canvas(image)
