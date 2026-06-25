import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Mapping, Tuple


# 用户自定义区 
ENABLED_PAGES = "1,2,3,4"
PAGE_SOURCES = {
    1: {"source": "bilibili", "title": "B站热搜"},
    #1: {"source": "bilibili", "title": "B站热搜"},
    2: {"source": "rss", "title": "少数派","url":"https://sspai.com/feed"},
    3: {"source": "zhihu", "title": "知乎热榜"}
    # RSS/Atom 示例：ß
    # 3: {
    #     "source": "rss",
    #     "title": "少数派",
    #     "url": "https://sspai.com/feed",
    # },
    # "source": "zhihu", "title": "知乎热榜"
}
# 彩云天气在中国大陆使用 GCJ-02（高德）坐标，顺序为经度、纬度。
CAIYUN_LONGITUDE = 121.5554
CAIYUN_LATITUDE = 31.2820
CITY_DISPLAY_NAME = "杨浦区 | 中环和润苑"


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_FONT_PATH = PROJECT_ROOT / "resources" / "fonts" / "zfull-gb.ttf"


SOURCE_NAMES = {
    "zhihu": "知乎热榜",
    "bilibili": "B站热搜",
    "github": "GitHub 热门",
    "rss": "RSS 订阅",
}


def parse_enabled_pages(value: str) -> FrozenSet[int]:
    try:
        pages = frozenset(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError("ENABLED_PAGES 必须是逗号分隔的数字，例如 1,2,3,4") from exc

    invalid_pages = pages - {1, 2, 3, 4}
    if invalid_pages:
        invalid = ", ".join(str(page) for page in sorted(invalid_pages))
        raise ValueError(f"不支持的页面编号: {invalid}")
    return pages


@dataclass(frozen=True)
class PageSource:
    source: str
    title: str
    url: str = ""

    @property
    def cache_key(self) -> Tuple[str, str]:
        return self.source, self.url if self.source == "rss" else ""


def parse_page_sources(
    value: Mapping[int, Mapping[str, str]],
) -> Dict[int, PageSource]:
    page_sources = {}
    for page, raw_config in value.items():
        if page not in {1, 2, 3}:
            raise ValueError(f"信息源只能配置在第 1-3 页，收到第 {page} 页")

        source = raw_config.get("source", "").strip().lower()
        if source not in SOURCE_NAMES:
            supported = ", ".join(SOURCE_NAMES)
            raise ValueError(
                f"第 {page} 页的数据源不受支持: {source or '未填写'}；"
                f"可选 {supported}"
            )

        url = raw_config.get("url", "").strip()
        if source == "rss" and not url:
            raise ValueError(f"第 {page} 页使用 RSS 时必须配置 url")

        page_sources[page] = PageSource(
            source=source,
            title=raw_config.get("title", "").strip() or SOURCE_NAMES[source],
            url=url,
        )
    return page_sources


@dataclass(frozen=True)
class Settings:
    enabled_pages: FrozenSet[int]
    page_sources: Dict[int, PageSource]
    caiyun_longitude: float
    caiyun_latitude: float
    city_display_name: str
    font_path: Path
    zectrix_api_key: str = ""
    mac_address: str = ""
    caiyun_api_token: str = ""


def load_settings() -> Settings:
    return Settings(
        enabled_pages=parse_enabled_pages(ENABLED_PAGES),
        page_sources=parse_page_sources(PAGE_SOURCES),
        caiyun_longitude=CAIYUN_LONGITUDE,
        caiyun_latitude=CAIYUN_LATITUDE,
        city_display_name=CITY_DISPLAY_NAME,
        font_path=DEFAULT_FONT_PATH,
        zectrix_api_key=os.environ.get("ZECTRIX_API_KEY", ""),
        mac_address=os.environ.get("ZECTRIX_MAC", ""),
        caiyun_api_token=os.environ.get("CAIYUN_API_TOKEN", ""),
    )
