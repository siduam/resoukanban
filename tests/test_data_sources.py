import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config import PageSource, Settings
from data_sources import (
    _beaufort_level,
    _wind_direction_name,
    get_caiyun_weather,
    get_information_items,
    parse_feed_titles,
    parse_caiyun_weather,
)


def make_settings(token="test-token"):
    return Settings(
        enabled_pages=frozenset({4}),
        page_sources={},
        caiyun_longitude=117.32,
        caiyun_latitude=38.99,
        city_display_name="津南区 | 天大北洋园",
        font_path=Path("font.ttf"),
        caiyun_api_token=token,
    )


def make_payload():
    return {
        "status": "ok",
        "server_time": 1781150700,
        "tzshift": 28800,
        "result": {
            "realtime": {
                "temperature": 28.3,
                "apparent_temperature": 31.1,
                "humidity": 0.86,
                "skycon": "CLEAR_DAY",
                "wind": {"speed": 12.23, "direction": 111.58},
                "life_index": {
                    "ultraviolet": {"index": 3, "desc": "弱"},
                    "comfort": {"index": 0, "desc": "闷热"},
                },
            },
            "daily": {
                "temperature": [
                    {
                        "date": "2026-06-11T00:00+08:00",
                        "min": 17.34,
                        "max": 29.54,
                    },
                    {
                        "date": "2026-06-12T00:00+08:00",
                        "min": 19.2,
                        "max": 30.8,
                    },
                    {
                        "date": "2026-06-13T00:00+08:00",
                        "min": 20.1,
                        "max": 27.6,
                    },
                ],
                "skycon": [
                    {"value": "CLEAR_DAY"},
                    {"value": "PARTLY_CLOUDY_DAY"},
                    {"value": "LIGHT_RAIN"},
                ],
                "astro": [
                    {
                        "sunrise": {"time": "04:43"},
                        "sunset": {"time": "19:38"},
                    }
                ],
            },
        },
    }


class CaiyunWeatherTests(unittest.TestCase):
    def test_parses_realtime_daily_and_astro_data(self):
        weather = parse_caiyun_weather(make_payload(), "津南区")

        self.assertEqual(weather.city, "津南区")
        self.assertEqual(weather.weather, "晴")
        self.assertEqual(weather.update_time, "12:05")
        self.assertEqual(weather.temp_curr, 28)
        self.assertEqual(weather.feel_temp, "31°C")
        self.assertEqual(weather.humidity, "86%")
        self.assertEqual(weather.wind_info, "3级 东东南")
        self.assertEqual(weather.ultraviolet, "弱")
        self.assertEqual(weather.comfort, "闷热")
        self.assertEqual((weather.temp_low, weather.temp_high), (17, 30))
        self.assertEqual((weather.sunrise, weather.sunset), ("04:43", "19:38"))
        self.assertEqual(len(weather.forecasts), 2)
        self.assertEqual(weather.forecasts[0].date, "06-12")
        self.assertEqual(weather.forecasts[0].weather, "多云")
        self.assertEqual(weather.forecasts[1].weather, "小雨")

    @patch("data_sources.requests.get")
    def test_fetches_caiyun_with_configured_location(self, requests_get):
        response = Mock()
        response.json.return_value = make_payload()
        requests_get.return_value = response

        weather = get_caiyun_weather(make_settings())

        self.assertEqual(weather.weather, "晴")
        request_url = requests_get.call_args.args[0]
        request_kwargs = requests_get.call_args.kwargs
        self.assertIn("/test-token/117.320000,38.990000/weather", request_url)
        self.assertNotIn("alert", request_kwargs["params"])
        self.assertEqual(request_kwargs["params"]["dailysteps"], 3)
        self.assertEqual(request_kwargs["params"]["lang"], "zh_CN")
        response.raise_for_status.assert_called_once_with()

    @patch("data_sources.requests.get")
    def test_missing_token_returns_fallback_without_request(self, requests_get):
        weather = get_caiyun_weather(make_settings(token=""))

        self.assertEqual(weather.weather, "未知")
        requests_get.assert_not_called()

    def test_wind_conversions(self):
        self.assertEqual(_beaufort_level(0.5), 0)
        self.assertEqual(_beaufort_level(12.23), 3)
        self.assertEqual(_wind_direction_name(0), "北")
        self.assertEqual(_wind_direction_name(11.25), "北")
        self.assertEqual(_wind_direction_name(11.26), "北东北")
        self.assertEqual(_wind_direction_name(111.58), "东东南")
        self.assertEqual(_wind_direction_name(123.75), "东东南")
        self.assertEqual(_wind_direction_name(123.76), "东南")

    def test_missing_realtime_life_index_uses_fallback_labels(self):
        payload = make_payload()
        payload["result"]["realtime"]["life_index"] = None

        weather = parse_caiyun_weather(payload, "津南区")

        self.assertEqual(weather.ultraviolet, "暂无")
        self.assertEqual(weather.comfort, "暂无")


class FeedTests(unittest.TestCase):
    def test_parses_rss_item_titles(self):
        content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Feed name</title>
            <item><title>First item</title></item>
            <item><title><![CDATA[Second item]]></title></item>
          </channel>
        </rss>
        """

        self.assertEqual(
            parse_feed_titles(content),
            ["First item", "Second item"],
        )

    def test_parses_atom_entry_titles(self):
        content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Feed name</title>
          <entry><title>Atom item</title></entry>
        </feed>
        """

        self.assertEqual(parse_feed_titles(content), ["Atom item"])

    def test_ignores_invalid_xml_control_characters_in_article_content(self):
        content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Valid title</title>
              <description>Broken\x05article content</description>
            </item>
          </channel>
        </rss>
        """

        self.assertEqual(parse_feed_titles(content), ["Valid title"])

    @patch("data_sources.get_rss_titles")
    def test_rss_source_uses_configured_url(self, get_rss_titles):
        get_rss_titles.return_value = ["Item"]
        page_source = PageSource(
            source="rss",
            title="My feed",
            url="https://example.com/feed.xml",
        )

        self.assertEqual(get_information_items(page_source), ["Item"])
        get_rss_titles.assert_called_once_with("https://example.com/feed.xml")


if __name__ == "__main__":
    unittest.main()
