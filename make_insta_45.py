"""Compose individual card PNGs into 4:5 (1080×1350) Instagram-ready images.

Each card is placed sharp-and-centered on a 4:5 canvas. The canvas is filled
with a blurred, zoomed copy of the same card so the frame looks intentional
rather than letterboxed. Card aspect (63:88 ≈ 0.716) is narrower than 4:5
(0.8), so the card fills the full height with slim side margins.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter

# Instagram portrait 4:5
CANVAS_W, CANVAS_H = 1080, 1350
# Fraction of canvas height the card occupies (a little breathing room top/bottom)
CARD_FILL = 0.94
BLUR_RADIUS = 40
BG_DARKEN = 0.82  # multiply blurred bg brightness so the card pops


def cover_fill(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale img to COVER a w×h box (crop overflow), return the box crop."""
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_h = h
        new_w = round(h * src_ratio)
    else:
        new_w = w
        new_h = round(w / src_ratio)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return resized.crop((left, top, left + w, top + h))


def make_one(src: Path, dest: Path) -> None:
    card = Image.open(src).convert("RGB")

    # --- blurred background (cover-fill the whole canvas) ---
    bg = cover_fill(card, CANVAS_W, CANVAS_H).filter(
        ImageFilter.GaussianBlur(BLUR_RADIUS)
    )
    if BG_DARKEN != 1.0:
        bg = Image.eval(bg, lambda p: int(p * BG_DARKEN))

    # --- sharp card, contained by height ---
    target_h = int(CANVAS_H * CARD_FILL)
    scale = target_h / card.height
    target_w = round(card.width * scale)
    if target_w > CANVAS_W:  # safety: never exceed width
        scale = (CANVAS_W * 0.96) / card.width
        target_w = round(card.width * scale)
        target_h = round(card.height * scale)
    card_r = card.resize((target_w, target_h), Image.LANCZOS)

    x = (CANVAS_W - target_w) // 2
    y = (CANVAS_H - target_h) // 2
    bg.paste(card_r, (x, y))
    bg.save(dest, "PNG")


def main() -> int:
    src_dir = Path(sys.argv[1])
    dest_dir = Path(sys.argv[2])
    dest_dir.mkdir(parents=True, exist_ok=True)

    cards = sorted(src_dir.glob("*.png"))
    if not cards:
        print(f"No PNGs found in {src_dir}", file=sys.stderr)
        return 1

    for i, src in enumerate(cards, 1):
        dest = dest_dir / src.name
        make_one(src, dest)
        print(f"  [{i:>3}/{len(cards)}] {dest.name}")

    print(f"Done: {len(cards)} images → {dest_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
