"""NBA 赛程数据获取与缓存。

逻辑移植自 zectrix-nba-board（https://github.com/happynailinzz/zectrix-nba-board）
的 scripts/nba_board.py，并按本项目的配置方式做了适配：

- 赛事数据源由 ``Settings.nba_score_source`` 决定，默认 ESPN 公开 scoreboard，
  可切换为 NBA 官方 CDN。
- 时间统一按北京时间（Asia/Shanghai）计算，不依赖运行机器的本地时区。
- 网络请求使用项目已有的 ``requests``；失败重试后回退到最近一次成功缓存。
- 缓存放在 ``~/.cache/resoukanban-nba``，可用 ``RESOUKANBAN_NBA_CACHE`` 覆盖，
  目录不可写时自动降级为无缓存。

页面渲染在 ``renderers.render_nba_page()``，这里只负责拿数据。
"""

import datetime as dt
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests

from config import Settings


TZ = ZoneInfo("Asia/Shanghai")

ESPN_SCOREBOARD = os.environ.get(
    "NBA_ESPN_SCOREBOARD_URL",
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
)
NBA_SCOREBOARD = os.environ.get(
    "NBA_SCOREBOARD_URL",
    "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
)
NBA_SCHEDULE = os.environ.get(
    "NBA_SCHEDULE_URL",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
)

CACHE_DIR = Path(
    os.environ.get(
        "RESOUKANBAN_NBA_CACHE",
        Path.home() / ".cache" / "resoukanban-nba",
    )
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}

TEAM_ZH = {
    "ATL": "老鹰", "BOS": "凯尔特人", "BKN": "篮网", "CHA": "黄蜂", "CHI": "公牛",
    "CLE": "骑士", "DAL": "独行侠", "DEN": "掘金", "DET": "活塞", "GSW": "勇士",
    "HOU": "火箭", "IND": "步行者", "LAC": "快船", "LAL": "湖人", "MEM": "灰熊",
    "MIA": "热火", "MIL": "雄鹿", "MIN": "森林狼", "NOP": "鹈鹕", "NYK": "尼克斯",
    "OKC": "雷霆", "ORL": "魔术", "PHI": "76人", "PHX": "太阳", "POR": "开拓者",
    "SAC": "国王", "SAS": "马刺", "TOR": "猛龙", "UTA": "爵士", "WAS": "奇才",
}

# ESPN 偶尔使用非官方三字母码（GS/NO/NY/UTAH/WSH/SA 等），先归一化再查中文。
ESPN_CODE_ALIAS = {
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "UTAH": "UTA",
    "WSH": "WAS",
    "SA": "SAS",
    "PHO": "PHX",
    "BRK": "BKN",
    "CHO": "CHA",
}


def _write_cache(name: str, value: Any) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / name).write_text(
            json.dumps(value, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _read_cache(name: str, default: Any) -> Any:
    try:
        return json.loads((CACHE_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _request(url: str, referer: str = ""):
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response


def _safe_fetch(label: str, fetcher, default):
    for attempt in range(2):
        try:
            return fetcher()
        except (requests.RequestException, ValueError, KeyError) as exc:
            if attempt:
                print(f"警告: {label} 数据源失败: {exc}")
            else:
                time.sleep(1)
    return default


def _cached_json(label, url, cache_name, default, referer=""):
    value = _safe_fetch(label, lambda: _request(url, referer).json(), None)
    if value is not None:
        _write_cache(cache_name, value)
        return value
    return _read_cache(cache_name, default)


def _esp_code(code: str) -> str:
    return ESPN_CODE_ALIAS.get(code, code)


def _team_name(code: str) -> str:
    return TEAM_ZH.get(code, code)


def parse_espn_games(data: Dict[str, Any], local_date: dt.date) -> Dict[str, Any]:
    """把 ESPN scoreboard JSON 转成与官方源一致的结构。"""
    games = []
    for event in (data or {}).get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        status = competition.get("status") or {}
        state = {"in": "live", "post": "final"}.get(
            (status.get("type") or {}).get("state", "pre"),
            "scheduled",
        )
        competitors = competition.get("competitors") or []
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        home = next((c for c in competitors if c.get("homeAway") == "home"), away)
        away_code = _esp_code((away.get("team") or {}).get("abbreviation", "客队"))
        home_code = _esp_code((home.get("team") or {}).get("abbreviation", "主队"))
        start = event.get("date", "")

        if state == "scheduled":
            try:
                when = dt.datetime.fromisoformat(
                    start.replace("Z", "+00:00")
                ).astimezone(TZ).strftime("%H:%M")
            except (ValueError, TypeError):
                when = "待定"
            status_text = when
        elif state == "live":
            period = status.get("period", 0) or 1
            clock = (status.get("displayClock") or "").strip()
            status_text = (
                "中场休息" if clock in ("", "0.0")
                else f"{period}节 · 剩余 {clock}"
            )
        else:
            status_text = "已结束"

        games.append({
            "away": _team_name(away_code),
            "home": _team_name(home_code),
            "away_code": away_code,
            "home_code": home_code,
            "away_score": away.get("score", "-"),
            "home_score": home.get("score", "-"),
            "status": status_text,
            "state": state,
            "start": start,
        })
    return {"date": local_date.isoformat(), "games": games}


def parse_official_games(data: Dict[str, Any], local_date: dt.date) -> Dict[str, Any]:
    """解析 NBA 官方 Live CDN / scheduleLeagueV2 结构。"""
    games = []
    source_games = (
        (data or {}).get("scoreboard", {}).get("games")
        or (data or {}).get("games")
        or (data or {}).get("leagueSchedule", {}).get("gameDates", [])
    )
    if source_games and isinstance(source_games[0], dict) and "games" in source_games[0]:
        source_games = [game for day in source_games for game in day.get("games", [])]

    for event in source_games:
        away = event.get("awayTeam") or {}
        home = event.get("homeTeam") or {}
        game_status = int(event.get("gameStatus", 1) or 1)
        state = "live" if game_status == 2 else ("final" if game_status == 3 else "scheduled")
        status_text = event.get("gameStatusText") or "未开始"

        if state == "scheduled":
            start = event.get("gameTimeUTC", event.get("gameDateTimeUTC", "")).replace("Z", "+00:00")
            try:
                when = dt.datetime.fromisoformat(start).astimezone(TZ).strftime("%H:%M")
            except (ValueError, TypeError):
                when = "待定"
            status_text = when
        elif state == "live":
            period = event.get("period", 0)
            clock = event.get("gameClock", "")
            clock_match = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", clock)
            if clock_match:
                minutes = int(clock_match.group(2) or 0)
                seconds = int(float(clock_match.group(3) or 0))
                clock = f"{minutes:02d}:{seconds:02d}"
            status_text = "中场休息" if not clock else f"{period}节 · 剩余 {clock}"
        else:
            status_text = "已结束"

        away_code = away.get("teamTricode", "客队")
        home_code = home.get("teamTricode", "主队")
        games.append({
            "away": _team_name(away_code),
            "home": _team_name(home_code),
            "away_code": away_code,
            "home_code": home_code,
            "away_score": away.get("score", "-"),
            "home_score": home.get("score", "-"),
            "status": status_text,
            "state": state,
            "start": event.get("gameTimeUTC", event.get("gameDateTimeUTC", ""))
            or event.get("gameDateUTC", ""),
        })
    return {"date": local_date.isoformat(), "games": games}


def _collect_espn(date: dt.date) -> List[Dict[str, Any]]:
    """拉取美日期窗口，再按北京开赛日重新分桶。

    NBA 比赛按美国日期归档，一个北京日横跨两个美日期（美东傍晚 = 北京凌晨），
    所以对目标北京日 D 需要拉取美日期 D-2..D+2，再把每场按北京时间归桶。
    """
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for offset in range(-2, 3):
        us_day = date + dt.timedelta(days=offset)
        url = f"{ESPN_SCOREBOARD}?dates={us_day:%Y%m%d}"
        data = _cached_json(
            "ESPN 赛程",
            url,
            f"espn-{us_day.isoformat()}.json",
            {},
            referer="https://www.espn.com/",
        )
        try:
            games = parse_espn_games(data, us_day)["games"]
        except (TypeError, ValueError, AttributeError):
            games = []
        for game in games:
            try:
                beijing_date = dt.datetime.fromisoformat(
                    str(game["start"]).replace("Z", "+00:00")
                ).astimezone(TZ).date()
            except (ValueError, TypeError):
                beijing_date = date
            by_date.setdefault(beijing_date.isoformat(), []).append(game)

    days = []
    for offset in range(-1, 3):
        target = (date + dt.timedelta(days=offset)).isoformat()
        days.append({"date": target, "games": by_date.get(target, [])})
    return days


def _collect_official(date: dt.date) -> List[Dict[str, Any]]:
    days = []
    for offset in range(-1, 3):
        day = date + dt.timedelta(days=offset)
        if offset == 0:
            data = _cached_json("NBA 官方赛程", NBA_SCOREBOARD, "scoreboard.json", {})
            days.append(parse_official_games(data, day))
        else:
            schedule = _cached_json("NBA 官方赛程表", NBA_SCHEDULE, "schedule.json", {})
            try:
                games = parse_official_games(schedule, day)["games"]
            except (TypeError, ValueError, AttributeError):
                games = []
            days.append({
                "date": day.isoformat(),
                "games": [
                    game for game in games
                    if str(game.get("start", "")).startswith(day.isoformat())
                ],
            })
    return days


def collect(settings: Settings, date: Optional[dt.date] = None) -> Dict[str, Any]:
    """抓取目标北京日的赛程（昨天/今天/明天/后天）。"""
    date = date or dt.datetime.now(TZ).date()
    if getattr(settings, "nba_score_source", "espn") == "official":
        days = _collect_official(date)
    else:
        days = _collect_espn(date)
    return {"days": days}
