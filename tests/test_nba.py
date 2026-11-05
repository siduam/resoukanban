import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import nba
from config import DEFAULT_FONT_PATH
from renderers import render_nba_page


TODAY = dt.date(2026, 11, 5)
NOW_BEFORE_15 = dt.datetime(2026, 11, 5, 12, 0, tzinfo=nba.TZ)
NOW_AFTER_15 = dt.datetime(2026, 11, 5, 20, 0, tzinfo=nba.TZ)


def espn_payload():
    return {
        "events": [
            {
                "date": "2026-11-05T00:30Z",
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
                "date": "2026-11-05T03:00Z",
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


def make_game(state="final", start="2026-11-05T00:30Z", **overrides):
    game = {
        "away": "老鹰",
        "home": "凯尔特人",
        "away_code": "ATL",
        "home_code": "BOS",
        "away_score": "108" if state == "final" else ("88" if state == "live" else "-"),
        "home_score": "104" if state == "final" else ("90" if state == "live" else "-"),
        "status": {
            "final": "已结束",
            "live": "3节 · 剩余 04:28",
            "scheduled": "08:30",
        }[state],
        "state": state,
        "start": start,
    }
    game.update(overrides)
    return game


def make_data(today_games, tomorrow_games=None, day_after_games=None):
    return {
        "days": [
            {"date": "2026-11-04", "games": []},
            {"date": "2026-11-05", "games": today_games},
            {"date": "2026-11-06", "games": tomorrow_games or []},
            {"date": "2026-11-07", "games": day_after_games or []},
        ]
    }


class EspnParsingTests(unittest.TestCase):
    def test_maps_teams_scores_and_status(self):
        games = nba.parse_espn_games(
            espn_payload(),
            dt.date(2026, 11, 5),
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

        games = nba.parse_espn_games(payload, dt.date(2026, 11, 5))["games"]

        self.assertEqual(games[1]["status"], "待定")


class OfficialParsingTests(unittest.TestCase):
    def test_maps_official_scoreboard(self):
        payload = {
            "scoreboard": {
                "games": [
                    {
                        "gameStatus": 3,
                        "gameStatusText": "Final",
                        "gameTimeUTC": "2026-11-05T00:00Z",
                        "awayTeam": {"teamTricode": "BOS", "score": "110"},
                        "homeTeam": {"teamTricode": "MIA", "score": "100"},
                    }
                ]
            }
        }

        games = nba.parse_official_games(payload, dt.date(2026, 11, 5))["games"]

        self.assertEqual(games[0]["away"], "凯尔特人")
        self.assertEqual(games[0]["home"], "热火")
        self.assertEqual(games[0]["state"], "final")
        self.assertEqual(games[0]["status"], "已结束")


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DEFAULT_FONT_PATH.exists():
            raise unittest.SkipTest("缺少字体文件")
        cls.font_path = DEFAULT_FONT_PATH

    def render(self, data, now):
        return render_nba_page(data, now, self.font_path)

    def test_before_15_shows_today(self):
        data = make_data(
            [make_game("final"), make_game("live", start="2026-11-05T03:00Z")],
            tomorrow_games=[make_game("scheduled", start="2026-11-06T00:30Z")],
        )

        image, info = self.render(data, NOW_BEFORE_15)

        self.assertEqual(info["label"], "今日")
        self.assertEqual(info["date"], TODAY)
        self.assertEqual(info["count"], 2)
        self.assertEqual(image.size, (400, 300))
        self.assertEqual(image.mode, "1")
        self.assertEqual(image.getextrema()[0], 0)

    def test_after_15_shows_tomorrow(self):
        data = make_data(
            [make_game("final")],
            tomorrow_games=[
                make_game("scheduled", start="2026-11-06T00:30Z"),
                make_game("scheduled", start="2026-11-06T03:00Z"),
            ],
        )

        image, info = self.render(data, NOW_AFTER_15)

        self.assertEqual(info["label"], "明日")
        self.assertEqual(info["date"], dt.date(2026, 11, 6))
        self.assertEqual(info["count"], 2)
        self.assertEqual(image.size, (400, 300))

    def test_15_oclock_is_the_cutoff(self):
        data = make_data(
            [make_game("final")],
            tomorrow_games=[make_game("scheduled", start="2026-11-06T00:30Z")],
        )

        _, before = self.render(
            data, dt.datetime(2026, 11, 5, 14, 59, tzinfo=nba.TZ)
        )
        _, after = self.render(
            data, dt.datetime(2026, 11, 5, 15, 0, tzinfo=nba.TZ)
        )

        self.assertEqual(before["label"], "今日")
        self.assertEqual(after["label"], "明日")

    def test_fifteen_games_fit_on_one_page(self):
        base = dt.datetime(2026, 11, 5, 0, 0, tzinfo=dt.timezone.utc)
        games = [
            make_game(start=(base + dt.timedelta(minutes=30 * index)).strftime("%Y-%m-%dT%H:%MZ"))
            for index in range(15)
        ]

        image, info = self.render(make_data(games), NOW_BEFORE_15)

        self.assertEqual(info["count"], 15)
        self.assertEqual(image.size, (400, 300))
        # 最后一行应该落在页面底部，而不是被裁掉
        bottom = image.crop((0, 260, 400, 300))
        self.assertEqual(bottom.getextrema()[0], 0)

    def test_no_games_falls_back_to_next_matchday(self):
        data = make_data(
            [],
            day_after_games=[make_game("scheduled", start="2026-11-07T00:30Z")],
        )

        image, info = self.render(data, NOW_BEFORE_15)

        self.assertEqual(info["count"], 0)
        self.assertEqual(image.size, (400, 300))
        self.assertEqual(image.getextrema()[0], 0)

    def test_empty_tomorrow_after_15_renders(self):
        data = make_data(
            [make_game("final")],
            day_after_games=[make_game("scheduled", start="2026-11-07T00:30Z")],
        )

        image, info = self.render(data, NOW_AFTER_15)

        self.assertEqual(info["label"], "明日")
        self.assertEqual(info["count"], 0)
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
