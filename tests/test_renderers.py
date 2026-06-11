import unittest

from config import load_settings
from data_sources import Forecast, WeatherData
from renderers import (
    CANVAS_SIZE,
    load_fonts,
    render_information_page,
    render_weather_dashboard,
)


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.fonts = load_fonts(cls.settings.font_path)

    def test_information_page_returns_next_item_index(self):
        titles = [f"第 {index} 条测试标题" for index in range(1, 21)]
        image, next_index = render_information_page(
            titles,
            "知乎热榜 (1/2)",
            0,
            self.fonts,
        )

        self.assertEqual(image.size, CANVAS_SIZE)
        self.assertEqual(image.mode, "1")
        self.assertGreater(next_index, 0)
        self.assertLess(next_index, len(titles))

    def test_weather_renders_supplied_data(self):
        weather = WeatherData(
            city="津南区",
            weather="晴",
            update_time="12:05",
            temp_curr=24,
            temp_low=18,
            temp_high=28,
            wind_info="2级 东南",
            humidity="50%",
            feel_temp="24.0°C",
            ultraviolet="弱",
            comfort="舒适",
            sunrise="05:00 AM",
            sunset="07:00 PM",
            forecasts=[
                Forecast("06-12", "多云", 19, 29),
                Forecast("06-13", "晴", 20, 30),
            ],
        )

        image = render_weather_dashboard(
            weather,
            self.settings,
            self.fonts,
        )

        self.assertEqual(image.size, CANVAS_SIZE)
        self.assertEqual(image.mode, "1")


if __name__ == "__main__":
    unittest.main()
