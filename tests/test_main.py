import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import main
from config import PageSource, Settings


class MainTests(unittest.TestCase):
    @patch("main.render_information_page")
    @patch("main.get_information_items")
    @patch("main.load_fonts")
    def test_same_source_can_continue_across_all_three_pages(
        self,
        load_fonts,
        get_information_items,
        render_information_page,
    ):
        settings = Settings(
            enabled_pages=frozenset({1, 2, 3}),
            page_sources={
                1: PageSource("zhihu", "知乎热榜"),
                2: PageSource("zhihu", "知乎热榜"),
                3: PageSource("zhihu", "知乎热榜"),
            },
            caiyun_longitude=117.32,
            caiyun_latitude=38.99,
            city_display_name="测试城市",
            font_path=Path("font.ttf"),
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

        self.assertEqual(set(pages), {1, 2, 3})
        get_information_items.assert_called_once_with(
            PageSource("zhihu", "知乎热榜")
        )
        starts = [
            call.args[2]
            for call in render_information_page.call_args_list
        ]
        self.assertEqual(starts, [0, 6, 12])

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
