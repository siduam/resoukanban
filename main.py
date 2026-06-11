import argparse
from collections import OrderedDict
from pathlib import Path

from config import Settings, load_settings
from data_sources import get_caiyun_weather, get_information_items
from push import push_images, save_images
from renderers import (
    load_fonts,
    render_information_page,
    render_weather_dashboard,
)


def generate_pages(settings: Settings):
    fonts = load_fonts(settings.font_path)
    pages = {}

    source_groups = OrderedDict()
    for page in sorted(settings.enabled_pages & {1, 2, 3}):
        page_source = settings.page_sources.get(page)
        if page_source is None:
            print(f"警告: Page {page} 未配置信息源，已跳过")
            continue
        source_groups.setdefault(page_source.cache_key, []).append((page, page_source))

    for page_configs in source_groups.values():
        first_source = page_configs[0][1]
        print(f"正在获取 {first_source.title}...")
        titles = get_information_items(first_source)
        next_start = 0
        page_count = len(page_configs)
        for sequence, (page, page_source) in enumerate(page_configs, start=1):
            title = page_source.title
            if page_count > 1:
                title = f"{title} ({sequence}/{page_count})"
            print(f"生成 Page {page}: {title}...")
            pages[page], next_start = render_information_page(
                titles,
                title,
                next_start,
                fonts,
            )

    if 4 in settings.enabled_pages:
        print("生成 Page 4: 彩云天气看板...")
        weather = get_caiyun_weather(settings)
        pages[4] = render_weather_dashboard(weather, settings, fonts)

    return pages


def build_parser():
    parser = argparse.ArgumentParser(description="生成并推送极趣墨水屏看板")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="只生成本地预览图，不调用极趣云 API",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("preview"),
        help="预览图输出目录，默认是 ./preview",
    )
    return parser


def run(argv=None):
    args = build_parser().parse_args(argv)
    settings = load_settings()

    if not args.preview and (not settings.zectrix_api_key or not settings.mac_address):
        print("错误: 请先配置 ZECTRIX_API_KEY 和 ZECTRIX_MAC")
        return 1

    if args.preview:
        print("开始生成本地预览，不会推送到设备...")
    else:
        print("开始执行墨水屏推送任务...")

    pages = generate_pages(settings)

    if args.preview:
        saved_paths = save_images(pages, args.output_dir)
        for path in saved_paths:
            print(f"已生成: {path}")
        print("本地预览生成完毕。")
    else:
        push_images(
            pages,
            api_key=settings.zectrix_api_key,
            mac_address=settings.mac_address,
        )
        print("所有任务执行完毕。")

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
