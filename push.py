from io import BytesIO
from pathlib import Path
from typing import Dict, List

import requests
from PIL import Image


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def save_images(images: Dict[int, Image.Image], output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for page_id, image in sorted(images.items()):
        path = output_dir / f"page_{page_id}.png"
        image.save(path)
        saved_paths.append(path)
    return saved_paths


def push_image(image: Image.Image, page_id: int, api_key: str, mac_address: str):
    url = (
        "https://cloud.zectrix.com/open/v1/devices/"
        f"{mac_address}/display/image"
    )
    headers = {"X-API-Key": api_key}
    files = {
        "images": (
            f"page_{page_id}.png",
            image_to_png_bytes(image),
            "image/png",
        )
    }
    data = {"dither": "true", "pageId": str(page_id)}

    try:
        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=30,
        )
        if response.ok:
            print(f"Page {page_id} 推送成功: {response.status_code}")
        else:
            print(f"Page {page_id} 推送失败: HTTP {response.status_code}")
    except requests.RequestException as exc:
        print(f"Page {page_id} 推送失败: {exc}")


def push_images(
    images: Dict[int, Image.Image],
    api_key: str,
    mac_address: str,
):
    for page_id, image in sorted(images.items()):
        push_image(image, page_id, api_key, mac_address)
