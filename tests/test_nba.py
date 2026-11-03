import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import nba
from config import DEFAULT_FONT_PATH
from renderers import load_nba_fonts, render_nba_page


def espn_payload():
    return {
        "events": [
            {
                "date": "2026-11-04T00:30Z",
                "competitions": [
                    {
                        "status": {
                            "period": 3,
                            "displayClock": "04:28",
                            "type": {"state": "in"},
                        },
                        "competitors": [
                            {
                                "homeAway": "away",
                                "team": {"abbreviation": "LAL"},
                                "score": "88",
                            },
                            {
                                "homeAway": "home",
                                "team": {"abbreviation": "GSW"},
                                "score": "90",
                            },
                        ],
                    }
                ],
            },
            {
                "date": "2026-11-04T03:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "pre"}},
                        "competitors": [
                            {
                                "homeAway": "away",
                                "team": {"abbreviation": "WSH"},
                                "score": "0",
                            },
                            {
                                "homeAway": "home",
                                "team": {"abbreviation": "SA"},
                                "score": "0",
                            },
                        ],
                    }
                ],
            },
        ]
    }


def make_game(state="final", **overrides):
    game = {
        "away": "老鹰",
        "home": "凯尔特人",
        "away_code": "ATL",
        "home_code": "BOS",
        "away_score": "108" if state == "final" else "-",
        "home_score": "104" if state == "final" else "-",
        "status": "已结束" if state == "final" else "08:00",
        "state": state,
        "start": "2026-11-04T00:30Z",
    }
    game.update(overrides)
    return game


def make_data(today_games, yesterday_games=None, future_games=None):
    return {
        "days": [
            {"date": "2026-11-03", "games": yesterday_games or []},
            {"date": "2026-11-04", "games": today_games},
            {"date": "2026-11-05", "games": future_games or []},
        ],
        "news": [{"title": "测试热点标题", "source": "新浪体育", "age": ""}],
    }


class EspnParsingTests(unittest.TestCase):
    def test_maps_teams_scores_and_status(self):
        games = nba.parse_espn_games(
            espn_payload(),
            dt.date(2026, 11, 4),
        )["games"]

        self.assertEqual(len(games), 2)
        self.assertEqual(games[0]["away"], "湖人")
        self.assertEqual(games[0]["home"], "勇士")
        self.assertEqual(games[0]["state"], "live")
        self.assertEqual(games[0]["status"], "3节 · 剩余 04:28")
        self.assertEqual(games[1]["away"], "奇才")
        self.assertEqual(games[1]["home"], "马刺")
        self.assertEqual(games[1]["state"], "scheduled")
        self.assertEqual(games[1]["status"], "11:00")

    def test_scheduled_game_without_time_falls_back(self):
        payload = espn_payload()
        payload["events"][1]["date"] = ""

        games = nba.parse_espn_games(payload, dt.date(2026, 11, 4))["games"]

        self.assertEqual(games[1]["status"], "待定")


class OfficialParsingTests(unittest.TestCase):
    def test_maps_official_scoreboard(self):
        payload = {
            "scoreboard": {
                "games": [
                    {
                        "gameStatus": 3,
                        "gameStatusText": "Final",
                        "gameTimeUTC": "2026-11-04T00:00Z",
                        "awayTeam": {"teamTricode": "BOS", "score": "110"},
                        "homeTeam": {"teamTricode": "MIA", "score": "100"},
                    }
                ]
            }
        }

        games = nba.parse_official_games(payload, dt.date(2026, 11, 4))["games"]

        self.assertEqual(games[0]["away"], "凯尔特人")
        self.assertEqual(games[0]["home"], "热火")
        self.assertEqual(games[0]["state"], "final")
        self.assertEqual(games[0]["status"], "已结束")


class NewsTests(unittest.TestCase):
    def test_feed_filters_non_nba_items(self):
        payload = {
            "result": {
                "data": {
                    "items": [
                        {"title": "湖人击败勇士取得三连胜"},
                        {"title": "英超本轮焦点战前瞻"},
                        {"title": "NBA"},
                        {"title": "湖人击败勇士取得三连胜"},
                    ]
                }
            }
        }

        self.assertEqual(
            nba._feed_titles(payload),
            ["湖人击败勇士取得三连胜"],
        )

    def test_regex_listing_prefers_newer_dates(self):
        html_text = (
            '<a href="/nba/2026-11-01/doc-old.html">旧的一条中文新闻标题</a>'
            '<a href="/nba/2026-11-03/doc-new.html">新的一条中文新闻标题</a>'
            '<a href="/nba/2026-11-02/doc-mid.html">中间的一条中文新闻</a>'
        )

        self.assertEqual(
            nba._regex_news(html_text),
            ["新的一条中文新闻标题", "中间的一条中文新闻", "旧的一条中文新闻标题"],
        )


class BuildStateTests(unittest.TestCase):
    def setUp(self):
        self.date = dt.date(2026, 11, 4)
        self.now = dt.datetime(2026, 11, 4, 20, 0, tzinfo=nba.TZ)

    def test_live_takes_priority(self):
        data = make_data(
            [make_game("live"), make_game("scheduled", start="2026-11-05T00:00Z")],
        )

        state = nba.build_state(data, self.date, self.now)

        self.assertEqual(state["status"], "LIVE")
        self.assertEqual(state["poll"], 10)
        self.assertEqual(state["focus"]["state"], "live")

    def test_next_when_nothing_live(self):
        data = make_data(
            [make_game("scheduled", start="2026-11-05T00:00Z")],
        )

        state = nba.build_state(data, self.date, self.now)

        self.assertEqual(state["status"], "NEXT")
        self.assertEqual(state["focus"]["state"], "scheduled")

    def test_final_when_today_finished(self):
        data = make_data([make_game("final")])

        state = nba.build_state(data, self.date, self.now)

        self.assertEqual(state["status"], "FINAL")
        self.assertEqual(state["poll"], 120)
        self.assertEqual(len(state["recent_finals"]), 1)

    def test_rest_reuses_previous_results(self):
        data = make_data(
            [],
            yesterday_games=[make_game("final", start="2026-11-03T00:30Z")],
            future_games=[make_game("scheduled", start="2026-11-05T00:00Z")],
        )

        state = nba.build_state(data, self.date, self.now)

        self.assertEqual(state["status"], "REST")
        self.assertEqual(state["poll"], 720)
        self.assertEqual(len(state["recent_finals"]), 1)
        self.assertIsNotNone(state["focus"])


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DEFAULT_FONT_PATH.exists():
            raise unittest.SkipTest("缺少字体文件")
        cls.fonts = load_nba_fonts(DEFAULT_FONT_PATH)

    def test_renders_mono_canvas(self):
        data = make_data([make_game("final")])

        image, state = render_nba_page(
            data,
            dt.date(2026, 11, 4),
            self.fonts,
            dt.datetime(2026, 11, 4, 20, 0, tzinfo=nba.TZ),
        )

        self.assertEqual(image.size, (400, 300))
        self.assertEqual(image.mode, "1")
        self.assertEqual(state["status"], "FINAL")
        self.assertEqual(image.getextrema()[0], 0)

    def test_renders_without_games_or_news(self):
        image, state = render_nba_page(
            {"days": [], "news": []},
            dt.date(2026, 11, 4),
            self.fonts,
            dt.datetime(2026, 11, 4, 20, 0, tzinfo=nba.TZ),
        )

        self.assertEqual(state["status"], "REST")
        self.assertEqual(image.size, (400, 300))


class CacheTests(unittest.TestCase):
    @patch("nba.time.sleep")
    @patch("nba._request")
    def test_falls_back_to_last_successful_cache(self, request, sleep):
        request.side_effect = requests.RequestException("network down")
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(nba, "CACHE_DIR", Path(temp_dir)):
                nba._write_cache("espn.json", {"events": [1]})

                value = nba._cached_json(
                    "测试源",
                    "https://example.com/data.json",
                    "espn.json",
                    {},
                )

        self.assertEqual(value, {"events": [1]})


if __name__ == "__main__":
    unittest.main()
