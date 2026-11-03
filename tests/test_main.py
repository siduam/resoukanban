import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import main
from config import PageSource, Settings


def make_settings(enabled_pages, page_sources=None):
    return Settings(
        enabled_pages=frozenset(enabled_pages),
        page_sources=page_sources or {},
        caiyun_longitude=117.32,
        caiyun_latitude=38.99,
        city_display_name="测试城市",
        font_path=Path("dummy.ttf"),
    )


class MainTests(unittest.TestCase):
    @patch("main.render_information_page")
    @patch("main.get_information_items")
    @patch("main.load_fonts")
    def test_same_source_can_continue_across_info_pages(
        self,
        load_fonts,
        get_information_items,
        render_information_page,
    ):
        settings = make_settings(
            {1, 3},
            {
                1: PageSource("zhihu", "知乎热榜"),
                3: PageSource("zhihu", "知乎热榜"),
            },
        )
        get_information_items.return_value = [
            f"知乎 {index}"
            for index in range(20)
        ]
        render_information_page.side_effect = lambda items, title, start, fonts: (
            Image.new("1", (400, 300), 255),
            start + 6,
        )

        pages = main.generate_pages(settings)

        self.assertEqual(set(pages), {1, 3})
        get_information_items.assert_called_once_with(
            PageSource("zhihu", "知乎热榜")
        )
        starts = [
            call.args[2]
            for call in render_information_page.call_args_list
        ]
        self.assertEqual(starts, [0, 6])

    @patch("main.generate_nba_page")
    @patch("main.render_information_page")
    @patch("main.get_information_items")
    @patch("main.load_fonts")
    def test_nba_page_is_generated_for_page_two(
        self,
        load_fonts,
        get_information_items,
        render_information_page,
        generate_nba_page,
    ):
        settings = make_settings(
            {1, 2},
            {1: PageSource("zhihu", "知乎热榜")},
        )
        get_information_items.return_value = ["标题"]
        render_information_page.return_value = (
            Image.new("1", (400, 300), 255),
            1,
        )
        generate_nba_page.return_value = Image.new("1", (400, 300), 255)

        pages = main.generate_pages(settings)

        self.assertEqual(set(pages), {1, 2})
        generate_nba_page.assert_called_once_with(settings)

    @patch("main.generate_nba_page")
    @patch("main.render_information_page")
    @patch("main.get_information_items")
    @patch("main.load_fonts")
    def test_nba_failure_keeps_other_pages(
        self,
        load_fonts,
        get_information_items,
        render_information_page,
        generate_nba_page,
    ):
        settings = make_settings(
            {1, 2},
            {1: PageSource("zhihu", "知乎热榜")},
        )
        get_information_items.return_value = ["标题"]
        render_information_page.return_value = (
            Image.new("1", (400, 300), 255),
            1,
        )
        generate_nba_page.side_effect = RuntimeError("boom")

        pages = main.generate_pages(settings)

        self.assertEqual(set(pages), {1})

    @patch("main.push_images")
    @patch("main.generate_pages")
    def test_preview_saves_images_without_device_credentials(
        self,
        generate_pages,
        push_images,
    ):
        generate_pages.return_value = {1: Image.new("1", (400, 300), 255)}

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = main.run(["--preview", "--output-dir", temp_dir])

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / "page_1.png").exists())
            push_images.assert_not_called()

    @patch("main.push_images")
    @patch("main.generate_pages")
    @patch("main.load_settings")
    def test_pages_option_filters_enabled_pages(
        self,
        load_settings,
        generate_pages,
        push_images,
    ):
        load_settings.return_value = make_settings({1, 2, 3, 4})
        generate_pages.return_value = {2: Image.new("1", (400, 300), 255)}

        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = main.run(
                ["--pages", "2", "--preview", "--output-dir", temp_dir]
            )

        self.assertEqual(exit_code, 0)
        filtered_settings = generate_pages.call_args[0][0]
        self.assertEqual(filtered_settings.enabled_pages, frozenset({2}))

    def test_pages_option_rejects_unknown_page(self):
        self.assertEqual(main.run(["--pages", "5"]), 1)

    @patch("main.generate_pages")
    def test_push_mode_requires_device_credentials(self, generate_pages):
        with patch.dict(
            "os.environ",
            {"ZECTRIX_API_KEY": "", "ZECTRIX_MAC": ""},
            clear=False,
        ):
            exit_code = main.run([])

        self.assertEqual(exit_code, 1)
        generate_pages.assert_not_called()


if __name__ == "__main__":
    unittest.main()
