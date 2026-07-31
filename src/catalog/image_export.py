"""High-DPI PNG exporters for individual cards and 3×3 sheets.

Two modes:

1. ``export_card_images`` — one PNG per game, exactly 63 × 88 mm @ high DPI.
2. ``export_sheet_images`` — 9 cards per PNG arranged in a 3×3 grid with
   zero gap, exactly 189 × 264 mm @ high DPI.

Rendered via headless Chromium (Playwright). ``device_scale_factor`` is
cranked up so the output has far more pixels than the physical print.
"""

from __future__ import annotations

import asyncio
import math
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.catalog.models import GameData
from src.catalog.translator import Translator
from src.catalog.view_model import CardViewModel

# CSS px per mm (CSS spec: 1mm = 3.7795275591 px)
_MM_TO_PX = 96.0 / 25.4

# 5× oversampling beyond CSS → ~6 µm print dot on 63 mm wide card
_DEVICE_SCALE_FACTOR = 5

# Native card dimensions in mm (must match styles.css .card)
_CARD_W_MM = 63.0
_CARD_H_MM = 88.0

# Sheet dimensions in mm (3× card, zero gap)
_SHEET_W_MM = _CARD_W_MM * 3  # 189mm
_SHEET_H_MM = _CARD_H_MM * 3  # 264mm

_CARDS_PER_SHEET = 9


# ---------------------------------------------------------------------------
# Print sheet layouts (for sending to a print shop)
# ---------------------------------------------------------------------------

# Paper size in mm, portrait
_PAPER_SIZES: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "B4": (257.0, 364.0),
    "A3": (297.0, 420.0),
}


def _plan_print_layout(
    paper_name: str,
    card_w_mm: float,
    card_h_mm: float,
) -> dict:
    """Compute how many scaled cards fit on the given paper + page padding.

    Returns a dict with all values needed by the ``print_sheet.html`` template.
    """
    paper_name = paper_name.upper()
    if paper_name not in _PAPER_SIZES:
        raise ValueError(
            f"Unknown paper size {paper_name!r}. "
            f"Known: {sorted(_PAPER_SIZES)}"
        )
    paper_w, paper_h = _PAPER_SIZES[paper_name]

    cols = int(paper_w // card_w_mm)
    rows = int(paper_h // card_h_mm)
    if cols < 1 or rows < 1:
        raise ValueError(
            f"Card {card_w_mm}×{card_h_mm} mm does not fit on {paper_name} "
            f"({paper_w}×{paper_h} mm)."
        )

    used_w = cols * card_w_mm
    used_h = rows * card_h_mm
    pad_left_mm = (paper_w - used_w) / 2
    pad_top_mm = (paper_h - used_h) / 2

    scale = card_w_mm / _CARD_W_MM  # aspect-preserving width scale
    # Sanity check: scaled height should fit within card_h_mm
    scaled_h = _CARD_H_MM * scale
    if scaled_h > card_h_mm + 0.5:
        # Fall back to height-limited scaling
        scale = card_h_mm / _CARD_H_MM

    return {
        "paper_name": paper_name,
        "paper_w_mm": paper_w,
        "paper_h_mm": paper_h,
        "card_w_mm": card_w_mm,
        "card_h_mm": card_h_mm,
        "cols": cols,
        "rows": rows,
        "cards_per_sheet": cols * rows,
        "pad_left_mm": round(pad_left_mm, 3),
        "pad_top_mm": round(pad_top_mm, 3),
        "scale_str": f"{scale:.6f}",
    }


def export_print_cards(
    games: list[GameData],
    output_dir: Path,
    templates_dir: Path,
    assets_dir: Path,
    translator: Translator,
    card_w_mm: float = 99.0,
    card_h_mm: float = 138.0,
) -> list[Path]:
    """Render each game as a print-sized individual card PNG.

    Uses the same scale math as ``export_print_sheets`` so the DPI on
    screen and on individual prints is identical.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    env = _build_env(templates_dir)
    template = env.get_template("print_card.html")
    styles_path = str(assets_dir / "styles.css")
    icons_path = str(assets_dir / "icons")

    scale = card_w_mm / _CARD_W_MM
    if _CARD_H_MM * scale > card_h_mm + 0.5:
        scale = card_h_mm / _CARD_H_MM
    scale_str = f"{scale:.6f}"

    viewport = (_mm_to_css_px(card_w_mm), _mm_to_css_px(card_h_mm))

    bundles: list[tuple[Path, Path]] = []
    for idx, g in enumerate(games, start=1):
        vm = CardViewModel.from_game_data(g, translator)
        html = template.render(
            card=vm,
            styles_path=styles_path,
            icons_path=icons_path,
            card_w_mm=card_w_mm,
            card_h_mm=card_h_mm,
            scale_str=scale_str,
        )
        tmp = assets_dir / f"_pcard_tmp_{idx:03d}.html"
        tmp.write_text(html, encoding="utf-8")
        slug = _safe_filename(g.name_kr or g.name_en or f"card_{idx}")
        dest = output_dir / f"{idx:03d}_{slug}.png"
        bundles.append((tmp, dest))

    try:
        asyncio.run(
            _screenshot_pages(
                [(tmp, dest, viewport) for tmp, dest in bundles]
            )
        )
    finally:
        for tmp, _ in bundles:
            if tmp.exists():
                tmp.unlink()

    return [dest for _, dest in bundles]


def export_print_sheets(
    games: list[GameData],
    output_dir: Path,
    templates_dir: Path,
    assets_dir: Path,
    translator: Translator,
    paper: str = "A4",
    card_w_mm: float = 99.0,
    card_h_mm: float = 138.0,
) -> list[Path]:
    """Render print-ready sheets with enlarged cards laid out for the given paper.

    Default: A4 portrait, 2×2, 98×137mm cards (preserves 63:88 aspect).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    env = _build_env(templates_dir)
    template = env.get_template("print_sheet.html")
    styles_path = str(assets_dir / "styles.css")
    icons_path = str(assets_dir / "icons")

    plan = _plan_print_layout(paper, card_w_mm, card_h_mm)
    per_sheet = plan["cards_per_sheet"]

    vms = [CardViewModel.from_game_data(g, translator) for g in games]
    chunks = [vms[i : i + per_sheet] for i in range(0, len(vms), per_sheet)]

    page_px = (
        _mm_to_css_px(plan["paper_w_mm"]),
        _mm_to_css_px(plan["paper_h_mm"]),
    )

    bundles: list[tuple[Path, Path]] = []
    for sheet_idx, chunk in enumerate(chunks, start=1):
        empty = per_sheet - len(chunk)
        html = template.render(
            cards=chunk,
            empty_slots=empty,
            styles_path=styles_path,
            icons_path=icons_path,
            **plan,
        )
        tmp = assets_dir / f"_print_tmp_{sheet_idx:02d}.html"
        tmp.write_text(html, encoding="utf-8")
        dest = output_dir / f"print_{plan['paper_name']}_{sheet_idx:02d}.png"
        bundles.append((tmp, dest))

    print(
        f"  [print] {plan['paper_name']} {plan['cols']}×{plan['rows']} "
        f"= {per_sheet}/sheet, {len(chunks)} sheets",
        file=sys.stderr,
    )

    try:
        asyncio.run(
            _screenshot_pages(
                [(tmp, dest, page_px) for tmp, dest in bundles]
            )
        )
    finally:
        for tmp, _ in bundles:
            if tmp.exists():
                tmp.unlink()

    return [dest for _, dest in bundles]


def _mm_to_css_px(mm: float) -> int:
    """Round mm to integer CSS pixels (always up, so nothing clips)."""
    return int(math.ceil(mm * _MM_TO_PX))


_CARD_PX = (_mm_to_css_px(_CARD_W_MM), _mm_to_css_px(_CARD_H_MM))
_SHEET_PX = (_mm_to_css_px(_SHEET_W_MM), _mm_to_css_px(_SHEET_H_MM))


def _safe_filename(name: str) -> str:
    """Make a filesystem-friendly slug from a game name."""
    s = re.sub(r"[^\w\s\-가-힣]", "", name, flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s.strip())
    return s or "untitled"


def _build_env(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )


def export_card_images(
    games: list[GameData],
    output_dir: Path,
    templates_dir: Path,
    assets_dir: Path,
    translator: Translator,
) -> list[Path]:
    """Render every game as a single-card PNG. Returns the list of paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    env = _build_env(templates_dir)
    template = env.get_template("card_solo.html")
    styles_path = str(assets_dir / "styles.css")
    icons_path = str(assets_dir / "icons")

    # Pre-render HTML bundles
    bundles: list[tuple[Path, Path]] = []  # (tmp_html, dest_png)
    for idx, g in enumerate(games, start=1):
        vm = CardViewModel.from_game_data(g, translator)
        html = template.render(
            card=vm,
            styles_path=styles_path,
            icons_path=icons_path,
        )
        # Temp HTML must live inside assets_dir so relative paths work
        tmp = assets_dir / f"_card_tmp_{idx:03d}.html"
        tmp.write_text(html, encoding="utf-8")
        slug = _safe_filename(g.name_kr or g.name_en or f"card_{idx}")
        dest = output_dir / f"{idx:03d}_{slug}.png"
        bundles.append((tmp, dest))

    try:
        asyncio.run(
            _screenshot_pages(
                [(tmp, dest, _CARD_PX) for tmp, dest in bundles]
            )
        )
    finally:
        for tmp, _ in bundles:
            if tmp.exists():
                tmp.unlink()

    return [dest for _, dest in bundles]


def export_sheet_images(
    games: list[GameData],
    output_dir: Path,
    templates_dir: Path,
    assets_dir: Path,
    translator: Translator,
) -> list[Path]:
    """Render 3×3 card sheets. Returns the list of paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    env = _build_env(templates_dir)
    template = env.get_template("sheet.html")
    styles_path = str(assets_dir / "styles.css")
    icons_path = str(assets_dir / "icons")

    vms = [CardViewModel.from_game_data(g, translator) for g in games]
    chunks = [
        vms[i : i + _CARDS_PER_SHEET]
        for i in range(0, len(vms), _CARDS_PER_SHEET)
    ]

    bundles: list[tuple[Path, Path]] = []
    for sheet_idx, chunk in enumerate(chunks, start=1):
        html = template.render(
            cards=chunk,
            styles_path=styles_path,
            icons_path=icons_path,
        )
        tmp = assets_dir / f"_sheet_tmp_{sheet_idx:02d}.html"
        tmp.write_text(html, encoding="utf-8")
        dest = output_dir / f"sheet_{sheet_idx:02d}.png"
        bundles.append((tmp, dest))

    try:
        asyncio.run(
            _screenshot_pages(
                [(tmp, dest, _SHEET_PX) for tmp, dest in bundles]
            )
        )
    finally:
        for tmp, _ in bundles:
            if tmp.exists():
                tmp.unlink()

    return [dest for _, dest in bundles]


def mirror_back_images(
    paths: list[Path],
    output_dir: Path,
) -> list[Path]:
    """Write horizontally-flipped (mirror) copies for double-sided printing.

    When you duplex-print cards whose back is meant to look identical to the
    front, the back sheet must be left-right mirrored so that — after the
    paper is physically flipped along its vertical edge — every card lines up
    with its front. This produces those mirrored backs.

    Each source PNG ``001_foo.png`` becomes ``001_foo_back.png`` under
    ``output_dir``. Returns the list of written paths.
    """
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in paths:
        with Image.open(src) as im:
            flipped = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            dest = output_dir / f"{src.stem}_back{src.suffix}"
            flipped.save(dest)
        written.append(dest)
        print(f"  [back] {dest.name}", file=sys.stderr)
    return written


async def _screenshot_pages(
    jobs: list[tuple[Path, Path, tuple[int, int]]],
) -> None:
    """Open each HTML file in Chromium and save a high-DPI screenshot."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for tmp_html, dest_png, (w, h) in jobs:
                context = await browser.new_context(
                    viewport={"width": w, "height": h},
                    device_scale_factor=_DEVICE_SCALE_FACTOR,
                )
                page = await context.new_page()
                await page.goto(f"file://{tmp_html.resolve()}")
                # Wait for fonts + images inside cards to decode
                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                await page.screenshot(
                    path=str(dest_png),
                    omit_background=False,
                    full_page=False,
                    clip={"x": 0, "y": 0, "width": w, "height": h},
                )
                await context.close()
                print(f"  [img] {dest_png.name}", file=sys.stderr)
        finally:
            await browser.close()
