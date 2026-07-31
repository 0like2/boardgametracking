"""Build print-shop-ready A3 PDFs (3×3 cards, black bg, 2mm bleed).

Produces two files matching the 무제-2.pdf spec:
  <out>.pdf          — fronts
  <out>_back.pdf     — whole-sheet L-R mirror, for duplex back registration

Each page carries a proper TrimBox (A3, 297×420) and BleedBox (301×424),
so a print shop sees the 2mm bleed and cut line.

Usage:
    python make_print_a3.py inputs/games_delta_2026-07-05.xlsx output/2026-07-05/catalog_print_A3
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import fitz  # PyMuPDF
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.catalog.bgg_client import BggClient
from src.catalog.bgg_repository import BggRepository
from src.catalog.config import load_config
from src.catalog.loader import load_games
from src.catalog.sorter import sort_games
from src.catalog.translator import Translator
from src.catalog.view_model import CardViewModel

_ROOT = Path(__file__).parent
_ASSETS = _ROOT / "src" / "catalog" / "assets"
_TEMPLATES = _ROOT / "src" / "catalog" / "templates"

# --- Geometry (mm) ---
TRIM_W, TRIM_H = 297.0, 420.0          # A3
BLEED = 2.0                            # per side
MEDIA_W, MEDIA_H = TRIM_W + 2 * BLEED, TRIM_H + 2 * BLEED  # 301 × 424
CARD_W = 92.0                          # enlarged card width
NATIVE_W = 63.0
CARD_H = CARD_W * 88.0 / 63.0          # preserve 63:88 ratio
GAP = 5.0
SCALE = CARD_W / NATIVE_W

MM_TO_PT = 72.0 / 25.4


def _load_games(input_path: Path):
    config = load_config(_ROOT / "config.yaml")
    game_inputs = load_games(input_path)
    client = BggClient(
        user_agent=config.bgg.user_agent,
        request_interval_sec=config.bgg.request_interval_sec,
    )
    repo = BggRepository(
        client=client,
        cache_dir=_ROOT / "cache",
        ttl_days=config.bgg.cache_ttl_days,
    )
    games = repo.get_games(game_inputs)
    return sort_games(games)


def _render_html(vms, mirror: bool) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("print_a3.html")
    sheets = [vms[i : i + 9] for i in range(0, len(vms), 9)]
    return template.render(
        sheets=sheets,
        mirror=mirror,
        styles_path=str(_ASSETS / "styles.css"),
        image_path="",
        media_w_mm=MEDIA_W,
        media_h_mm=MEDIA_H,
        trim_w_mm=TRIM_W,
        trim_h_mm=TRIM_H,
        card_w_mm=round(CARD_W, 4),
        card_h_mm=round(CARD_H, 4),
        gap_mm=GAP,
        scale_str=f"{SCALE:.6f}",
    )


async def _html_to_pdf(html: str, out_pdf: Path) -> None:
    from playwright.async_api import async_playwright

    tmp = _ASSETS / "_a3_tmp.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(f"file://{tmp.resolve()}")
            try:
                await page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass
            await page.pdf(
                path=str(out_pdf),
                width=f"{MEDIA_W}mm",
                height=f"{MEDIA_H}mm",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            await browser.close()
    finally:
        if tmp.exists():
            tmp.unlink()


def _inject_boxes(pdf_path: Path) -> None:
    """Set BleedBox = full media, TrimBox = ArtBox = 2mm inset (A3)."""
    doc = fitz.open(pdf_path)
    inset = BLEED * MM_TO_PT
    for page in doc:
        r = page.rect  # points, full media
        media = f"[0 0 {r.width:.4f} {r.height:.4f}]"
        trim = (
            f"[{inset:.4f} {inset:.4f} "
            f"{r.width - inset:.4f} {r.height - inset:.4f}]"
        )
        doc.xref_set_key(page.xref, "BleedBox", media)
        doc.xref_set_key(page.xref, "TrimBox", trim)
        doc.xref_set_key(page.xref, "ArtBox", trim)
    doc.saveIncr()
    doc.close()


def main() -> int:
    input_path = Path(sys.argv[1])
    out_base = Path(sys.argv[2])
    out_base.parent.mkdir(parents=True, exist_ok=True)

    games = _load_games(input_path)
    translator = Translator()
    vms = [CardViewModel.from_game_data(g, translator) for g in games]
    n_sheets = (len(vms) + 8) // 9
    print(
        f"{len(vms)} cards → {n_sheets} A3 sheets "
        f"(card {CARD_W:g}×{CARD_H:.1f}mm, media {MEDIA_W:g}×{MEDIA_H:g}mm)"
    )

    front = out_base.with_suffix(".pdf")
    back = out_base.parent / f"{out_base.name}_back.pdf"

    for mirror, out in [(False, front), (True, back)]:
        html = _render_html(vms, mirror=mirror)
        asyncio.run(_html_to_pdf(html, out))
        _inject_boxes(out)
        label = "back (mirrored)" if mirror else "front"
        kb = out.stat().st_size / 1024
        print(f"  [{label}] {out}  ({kb:.0f} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
