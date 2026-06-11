import unittest

from config import parse_enabled_pages, parse_page_sources


class ParseEnabledPagesTests(unittest.TestCase):
    def test_parses_page_numbers(self):
        self.assertEqual(parse_enabled_pages("1, 2,4"), frozenset({1, 2, 4}))

    def test_rejects_unknown_page(self):
        with self.assertRaisesRegex(ValueError, "不支持的页面编号"):
            parse_enabled_pages("1,5")


class ParsePageSourcesTests(unittest.TestCase):
    def test_parses_builtin_and_rss_sources(self):
        sources = parse_page_sources(
            {
                1: {"source": "zhihu", "title": ""},
                2: {
                    "source": "rss",
                    "title": "Example",
                    "url": "https://example.com/feed.xml",
                },
            }
        )

        self.assertEqual(sources[1].title, "知乎热榜")
        self.assertEqual(
            sources[2].cache_key,
            ("rss", "https://example.com/feed.xml"),
        )

    def test_rejects_rss_without_url(self):
        with self.assertRaisesRegex(ValueError, "必须配置 url"):
            parse_page_sources({1: {"source": "rss", "title": "Example"}})

    def test_rejects_source_on_weather_page(self):
        with self.assertRaisesRegex(ValueError, "第 1-3 页"):
            parse_page_sources({4: {"source": "zhihu"}})


if __name__ == "__main__":
    unittest.main()
