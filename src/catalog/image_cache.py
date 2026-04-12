"""Download and cache board game box art images with downscaling."""

from __future__ import annotations

import sys
from pathlib import Path

import requests
from PIL import Image

_MAX_EDGE_PX = 1600
_JPEG_QUALITY = 95


def fetch_image(
    cache_key: str,
    image_url: str,
    cache_dir: Path,
    user_agent: str = "BoardGameClubCatalog/1.0",
) -> Path:
    """Download image_url, downscale to ≤1600px on the wider edge, save as JPEG.

    ``cache_key`` is any string that uniquely identifies the game across its
    data source (e.g. ``"bl_17173"`` for Boardlife game 17173 or
    ``"bgg_237182"`` for BGG id 237182). The image is stored at
    ``cache_dir/images/{cache_key}.jpg``. If the file already exists it is
    returned immediately without re-downloading.
    """
    images_dir = cache_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    dest = images_dir / f"{cache_key}.jpg"

    if dest.exists():
        return dest

    url = image_url if image_url.startswith("http") else "https:" + image_url

    headers = {"User-Agent": user_agent}
    try:
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(
            f"Warning: Could not download image for {cache_key}: {exc}",
            file=sys.stderr,
        )
        raise

    raw_bytes = resp.content
    try:
        img = Image.open(__import__("io").BytesIO(raw_bytes))
    except Exception as exc:
        print(
            f"Warning: Could not open image for {cache_key}: {exc}",
            file=sys.stderr,
        )
        raise

    # Convert to RGB (JPEG does not support alpha)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Downscale if wider edge exceeds limit
    w, h = img.size
    wider = max(w, h)
    if wider > _MAX_EDGE_PX:
        scale = _MAX_EDGE_PX / wider
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.LANCZOS)

    img.save(dest, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return dest
