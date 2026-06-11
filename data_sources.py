from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
from typing import Any, Dict, List
from xml.etree import ElementTree

import requests

from config import PageSource, Settings


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

CAIYUN_BASE_URL = "https://api.caiyunapp.com/v2.6"
XML_INVALID_CONTROL_CHARACTERS = re.compile(
    rb"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)

SKYCON_NAMES = {
    "CLEAR_DAY": "晴",
    "CLEAR_NIGHT": "晴",
    "PARTLY_CLOUDY_DAY": "多云",
    "PARTLY_CLOUDY_NIGHT": "多云",
    "CLOUDY": "阴",
    "LIGHT_HAZE": "轻度雾霾",
    "MODERATE_HAZE": "中度雾霾",
    "HEAVY_HAZE": "重度雾霾",
    "LIGHT_RAIN": "小雨",
    "MODERATE_RAIN": "中雨",
    "HEAVY_RAIN": "大雨",
    "STORM_RAIN": "暴雨",
    "FOG": "雾",
    "LIGHT_SNOW": "小雪",
    "MODERATE_SNOW": "中雪",
    "HEAVY_SNOW": "大雪",
    "STORM_SNOW": "暴雪",
    "SLEET": "雨夹雪",
    "LIGHT_SNOW_TO_RAIN": "小雪转雨",
    "MODERATE_SNOW_TO_RAIN": "中雪转雨",
    "HEAVY_SNOW_TO_RAIN": "大雪转雨",
    "LIGHT_RAIN_TO_SNOW": "小雨转雪",
    "MODERATE_RAIN_TO_SNOW": "中雨转雪",
    "HEAVY_RAIN_TO_SNOW": "大雨转雪",
    "HAIL": "冰雹",
    "DUST": "浮尘",
    "SAND": "沙尘",
    "WIND": "大风",
}


@dataclass(frozen=True)
class Forecast:
    date: str
    weather: str
    temp_low: int
    temp_high: int


@dataclass
class WeatherData:
    city: str
    weather: str = "未知"
    temp_curr: int = 0
    temp_low: int = 0
    temp_high: int = 0
    wind_info: str = "无数据"
    humidity: str = "0%"
    feel_temp: str = "N/A"
    sunrise: str = "--:--"
    sunset: str = "--:--"
    forecasts: List[Forecast] = field(default_factory=list)


def get_clothing_advice(temp: int) -> str:
    if temp >= 28:
        return "建议穿短袖、短裤，注意防晒补水。"
    if temp >= 22:
        return "体感舒适，建议穿 T 恤配薄长裤。"
    if temp >= 16:
        return "建议穿长袖衬衫、卫衣或单层薄外套。"
    if temp >= 10:
        return "气温微凉，建议穿夹克、风衣或毛衣。"
    if temp >= 5:
        return "建议穿大衣、厚毛衣或薄款羽绒服。"
    return "天气寒冷，建议穿厚羽绒服，注意防寒。"


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_feed_titles(content: bytes) -> List[str]:
    sanitized_content = XML_INVALID_CONTROL_CHARACTERS.sub(b"", content)
    root = ElementTree.fromstring(sanitized_content)
    titles = []
    for entry in root.iter():
        if _xml_local_name(entry.tag) not in {"item", "entry"}:
            continue
        for child in entry:
            if _xml_local_name(child.tag) == "title":
                title = "".join(child.itertext()).strip()
                if title:
                    titles.append(title)
                break
    return titles


def get_rss_titles(url: str) -> List[str]:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return parse_feed_titles(response.content)


def get_information_items(page_source: PageSource) -> List[str]:
    try:
        source = page_source.source
        if source == "zhihu":
            response = requests.get(
                "https://api.zhihu.com/topstory/hot-list",
                headers=HEADERS,
                timeout=10,
            ).json()
            titles = [item["target"]["title"] for item in response["data"]]
        elif source == "bilibili":
            response = requests.get(
                "https://api.bilibili.com/x/web-interface/wbi/search/square?limit=30",
                headers=HEADERS,
                timeout=10,
            ).json()
            titles = [
                item["show_name"]
                for item in response["data"]["trending"]["list"]
            ]
        elif source == "github":
            date_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            url = (
                "https://api.github.com/search/repositories"
                f"?q=stars:>500+created:>{date_str}&sort=stars&order=desc"
            )
            response = requests.get(url, headers=HEADERS, timeout=10).json()
            titles = [
                f"{item['full_name']}: "
                f"{item['description'][:50] if item['description'] else 'No desc'}"
                for item in response["items"]
            ]
        elif source == "rss":
            titles = get_rss_titles(page_source.url)
        else:
            return ["不支持的数据源"]
    except (
        requests.RequestException,
        ElementTree.ParseError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"获取失败: {exc}")
        return ["数据获取失败，请检查配置"] * 10

    return titles[:30] or ["该信息源暂无内容"]


def _round_int(value, default=0) -> int:
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return default


def _skycon_name(value: Any) -> str:
    return SKYCON_NAMES.get(str(value), "未知")


def _wind_direction_name(degrees: Any) -> str:
    try:
        direction = float(degrees) % 360
    except (TypeError, ValueError):
        return "未知风向"
    names = ("北", "东北", "东", "东南", "南", "西南", "西", "西北")
    return names[int((direction + 22.5) // 45) % len(names)]


def _beaufort_level(speed_kmh: Any) -> int:
    try:
        speed = max(0.0, float(speed_kmh))
    except (TypeError, ValueError):
        return 0
    upper_bounds = (1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118)
    for level, upper_bound in enumerate(upper_bounds):
        if speed < upper_bound:
            return level
    return 12


def parse_caiyun_weather(payload: Dict[str, Any], city: str) -> WeatherData:
    if payload.get("status") != "ok":
        raise ValueError(f"彩云天气返回状态异常: {payload.get('status', 'unknown')}")

    result_data = payload["result"]
    realtime = result_data["realtime"]
    daily = result_data["daily"]
    temperatures = daily.get("temperature", [])
    skycons = daily.get("skycon_08h_20h") or daily.get("skycon", [])
    astro = daily.get("astro", [])

    result = WeatherData(
        city=city,
        weather=_skycon_name(realtime.get("skycon")),
        temp_curr=_round_int(realtime.get("temperature")),
        feel_temp=f"{_round_int(realtime.get('apparent_temperature'))}°C",
    )

    humidity = realtime.get("humidity", 0)
    try:
        humidity_value = float(humidity)
        if humidity_value <= 1:
            humidity_value *= 100
        result.humidity = f"{round(humidity_value)}%"
    except (TypeError, ValueError):
        pass

    wind = realtime.get("wind", {})
    wind_speed = wind.get("speed", 0)
    result.wind_info = (
        f"{_beaufort_level(wind_speed)}级 "
        f"{_wind_direction_name(wind.get('direction'))}"
    )

    if temperatures:
        result.temp_low = _round_int(temperatures[0].get("min"))
        result.temp_high = _round_int(temperatures[0].get("max"))

    if astro:
        result.sunrise = astro[0].get("sunrise", {}).get("time", "--:--")
        result.sunset = astro[0].get("sunset", {}).get("time", "--:--")

    forecast_count = min(len(temperatures), len(skycons), 3)
    for index in range(1, forecast_count):
        temperature = temperatures[index]
        skycon = skycons[index]
        result.forecasts.append(
            Forecast(
                date=str(temperature.get("date", ""))[5:10],
                weather=_skycon_name(skycon.get("value")),
                temp_low=_round_int(temperature.get("min")),
                temp_high=_round_int(temperature.get("max")),
            )
        )

    return result


def get_caiyun_weather(settings: Settings) -> WeatherData:
    city = settings.city_display_name.split("|")[0].strip()
    fallback = WeatherData(city=city)
    if not settings.caiyun_api_token:
        print("警告: 未设置 CAIYUN_API_TOKEN，无法获取彩云天气数据")
        return fallback

    location = f"{settings.caiyun_longitude:.6f},{settings.caiyun_latitude:.6f}"
    url = f"{CAIYUN_BASE_URL}/{settings.caiyun_api_token}/{location}/weather"
    params = {
        "alert": "true",
        "dailysteps": 3,
        "hourlysteps": 24,
        "lang": "zh_CN",
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return parse_caiyun_weather(response.json(), city)
    except (
        requests.RequestException,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"彩云天气请求异常: {type(exc).__name__}")
        return fallback
