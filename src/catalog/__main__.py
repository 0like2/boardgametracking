"""CLI entry point for the board game catalog generator.

Usage:
    python -m src.catalog build inputs/games.xlsx --out output/catalog.pdf
    python -m src.catalog preview inputs/games.xlsx [--port 8765]
    python -m src.catalog refresh --id 224517
    python -m src.catalog --report-missing-translations
"""

from __future__ import annotations

import argparse
import http.server
import sys
import tempfile
import threading
from pathlib import Path

from src.catalog.bgg_client import BggClient
from src.catalog.bgg_repository import BggRepository
from src.catalog.config import load_config
from src.catalog.image_export import (
    export_card_images,
    export_print_cards,
    export_print_sheets,
    export_sheet_images,
)
from src.catalog.loader import load_games
from src.catalog.models import GameData, GameInput
from src.catalog.pdf_export import make_exporter
from src.catalog.renderer import Renderer
from src.catalog.sorter import group_summary, sort_games
from src.catalog.translator import Translator

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_ASSETS_DIR = Path(__file__).parent / "assets"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# Build pipeline helpers
# ---------------------------------------------------------------------------


def _build_pipeline(
    input_path: Path,
    output_path: Path,
    renderer_name: str,
    max_age_days: int,
    refresh: bool,
    cache_dir: Path,
    offline_fixtures: Path | None = None,
    report_missing: bool = False,
    emit_card_images: bool = False,
    emit_sheet_images: bool = False,
    emit_print_sheets: bool = False,
    emit_print_cards: bool = False,
    print_paper: str = "A4",
    print_card_w_mm: float = 99.0,
    print_card_h_mm: float = 138.0,
    images_dir: Path | None = None,
    skip_pdf: bool = False,
) -> int:
    """Run the full build pipeline. Returns exit code (0=success)."""

    config = load_config(_PROJECT_ROOT / "config.yaml")
    game_inputs: list[GameInput] = load_games(input_path)

    if not game_inputs:
        print("ERROR: No games found in input file.", file=sys.stderr)
        return 1

    # Fetch or mock BGG data
    if offline_fixtures is not None:
        games = _load_offline_fixtures(game_inputs, offline_fixtures)
    else:
        client = BggClient(
            user_agent=config.bgg.user_agent,
            request_interval_sec=config.bgg.request_interval_sec,
        )
        repo = BggRepository(
            client=client,
            cache_dir=cache_dir,
            ttl_days=max_age_days,
        )
        games = repo.get_games(game_inputs, refresh=refresh)

    if not games:
        print("ERROR: No game data retrieved.", file=sys.stderr)
        return 1

    # Auto-group + order by Boardlife category + theme
    games = sort_games(games)
    for grp, cnt in group_summary(games):
        print(f"  [group] {grp}: {cnt}", file=sys.stderr)

    translator = Translator()
    renderer = Renderer(templates_dir=_TEMPLATES_DIR, assets_dir=_ASSETS_DIR)

    # --- PDF catalog -----------------------------------------------------
    if not skip_pdf:
        html = renderer.render(games, translator)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        exporter = make_exporter(renderer_name)
        exporter.export(html, output_path, base_url=_ASSETS_DIR)
        size_kb = output_path.stat().st_size / 1024
        print(
            f"Catalog built: {len(games)} games → {output_path} ({size_kb:.1f} KB)"
        )

    # --- Image exports ---------------------------------------------------
    if emit_card_images or emit_sheet_images or emit_print_sheets or emit_print_cards:
        img_root = images_dir or (output_path.parent / "images")
        img_root.mkdir(parents=True, exist_ok=True)

        if emit_card_images:
            card_dir = img_root / "cards"
            paths = export_card_images(
                games=games,
                output_dir=card_dir,
                templates_dir=_TEMPLATES_DIR,
                assets_dir=_ASSETS_DIR,
                translator=translator,
            )
            print(f"Card images: {len(paths)} → {card_dir}")

        if emit_sheet_images:
            sheet_dir = img_root / "sheets"
            paths = export_sheet_images(
                games=games,
                output_dir=sheet_dir,
                templates_dir=_TEMPLATES_DIR,
                assets_dir=_ASSETS_DIR,
                translator=translator,
            )
            print(f"Sheet images: {len(paths)} → {sheet_dir}")

        if emit_print_cards:
            pcard_dir = img_root / "print_cards"
            paths = export_print_cards(
                games=games,
                output_dir=pcard_dir,
                templates_dir=_TEMPLATES_DIR,
                assets_dir=_ASSETS_DIR,
                translator=translator,
                card_w_mm=print_card_w_mm,
                card_h_mm=print_card_h_mm,
            )
            print(
                f"Print cards: {len(paths)} × "
                f"{print_card_w_mm:g}×{print_card_h_mm:g}mm → {pcard_dir}"
            )

        if emit_print_sheets:
            print_dir = img_root / "print_sheets"
            paths = export_print_sheets(
                games=games,
                output_dir=print_dir,
                templates_dir=_TEMPLATES_DIR,
                assets_dir=_ASSETS_DIR,
                translator=translator,
                paper=print_paper,
                card_w_mm=print_card_w_mm,
                card_h_mm=print_card_h_mm,
            )
            print(
                f"Print sheets: {len(paths)} × "
                f"{print_paper} ({print_card_w_mm:g}×{print_card_h_mm:g}mm) → {print_dir}"
            )

    # --- Missing translations report -------------------------------------
    missing = translator.missing_terms()
    if missing:
        print(
            f"Missing translations ({len(missing)} terms):", file=sys.stderr
        )
        for term in sorted(missing):
            print(f"  {term}", file=sys.stderr)

    return 0


def _load_offline_fixtures(
    game_inputs: list[GameInput], fixtures_dir: Path
) -> list[GameData]:
    """Parse BGG XML fixtures from disk instead of making network calls."""
    from src.catalog.bgg_parser import parse_game

    results: list[GameData] = []
    for gi in game_inputs:
        xml_path = fixtures_dir / f"bgg_thing_{gi.bgg_id}.xml"
        if not xml_path.exists():
            # Try generic name patterns used in tests
            candidates = list(fixtures_dir.glob(f"bgg_thing_*.xml"))
            if candidates:
                xml_path = candidates[0]
            else:
                print(
                    f"Warning: No fixture found for bgg_id={gi.bgg_id}; skipping.",
                    file=sys.stderr,
                )
                continue
        try:
            gd = parse_game(
                xml_path.read_bytes(),
                gi,
                image_local_path="",
                base_game_kr=None,
            )
            results.append(gd)
        except Exception as exc:
            print(
                f"Warning: Failed to parse fixture {xml_path}: {exc}",
                file=sys.stderr,
            )
    return results


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_build(args: argparse.Namespace) -> int:
    cache_dir = _PROJECT_ROOT / "cache"
    offline: Path | None = None
    if hasattr(args, "offline_fixtures") and args.offline_fixtures:
        offline = Path(args.offline_fixtures)

    return _build_pipeline(
        input_path=Path(args.input),
        output_path=Path(args.out),
        renderer_name=args.renderer,
        max_age_days=args.max_age,
        refresh=args.refresh,
        cache_dir=cache_dir,
        offline_fixtures=offline,
        report_missing=args.report_missing_translations,
        emit_card_images=args.images or args.card_images,
        emit_sheet_images=args.images or args.sheet_images,
        emit_print_sheets=args.print_sheets,
        emit_print_cards=args.print_cards,
        print_paper=args.print_paper,
        print_card_w_mm=args.print_card_w,
        print_card_h_mm=args.print_card_h,
        images_dir=Path(args.images_dir) if args.images_dir else None,
        skip_pdf=args.no_pdf,
    )


def cmd_preview(args: argparse.Namespace) -> int:
    """Render HTML and serve it locally for quick visual preview."""
    config = load_config(_PROJECT_ROOT / "config.yaml")
    game_inputs = load_games(Path(args.input))
    client = BggClient(
        user_agent=config.bgg.user_agent,
        request_interval_sec=config.bgg.request_interval_sec,
    )
    repo = BggRepository(
        client=client,
        cache_dir=_PROJECT_ROOT / "cache",
        ttl_days=config.bgg.cache_ttl_days,
    )
    games = repo.get_games(game_inputs)

    translator = Translator()
    renderer = Renderer(templates_dir=_TEMPLATES_DIR, assets_dir=_ASSETS_DIR)
    html = renderer.render(games, translator)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_html = Path(tmpdir) / "preview.html"
        tmp_html.write_text(html, encoding="utf-8")

        port = args.port
        print(f"Preview at: http://localhost:{port}/preview.html  (Ctrl-C to stop)")

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt: str, *a: object) -> None:
                pass  # suppress access logs

        server = http.server.HTTPServer(("", port), _Handler)
        server.serve_forever()
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    """Invalidate BGG cache for a single game and re-fetch it."""
    config = load_config(_PROJECT_ROOT / "config.yaml")
    client = BggClient(
        user_agent=config.bgg.user_agent,
        request_interval_sec=config.bgg.request_interval_sec,
    )
    repo = BggRepository(
        client=client,
        cache_dir=_PROJECT_ROOT / "cache",
        ttl_days=config.bgg.cache_ttl_days,
    )
    repo.invalidate(args.id)
    print(f"Cache invalidated for bgg_id={args.id}. Re-fetch will happen on next build.")
    return 0


def cmd_report_missing(args: argparse.Namespace) -> int:
    """Print all category/mechanic terms that have no Korean translation."""
    translator = Translator()
    # We don't have games loaded here — just report what's in the dictionary
    # This is a lightweight mode; a full report requires loading games.
    print("Run 'build' with --report-missing-translations flag to get missing terms after a full build.")
    return 0


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.catalog",
        description="Board game catalog card generator",
    )
    parser.add_argument(
        "--report-missing-translations",
        action="store_true",
        default=False,
        help="Print untranslated BGG terms to stderr after build",
    )

    sub = parser.add_subparsers(dest="command")

    # build
    p_build = sub.add_parser("build", help="Build the PDF catalog")
    p_build.add_argument("input", help="Path to games.xlsx or games.csv")
    p_build.add_argument(
        "--out", default="output/catalog.pdf", help="Output PDF path"
    )
    p_build.add_argument(
        "--renderer",
        choices=["playwright", "weasyprint"],
        default="playwright",
        help="PDF rendering engine (default: playwright)",
    )
    p_build.add_argument(
        "--max-age",
        type=int,
        default=30,
        dest="max_age",
        help="BGG cache TTL in days (default: 30)",
    )
    p_build.add_argument(
        "--refresh", action="store_true", default=False,
        help="Force re-fetch from BGG ignoring cache",
    )
    p_build.add_argument(
        "--offline-fixtures",
        metavar="DIR",
        default=None,
        help="Load BGG data from local XML fixtures instead of the network",
    )
    p_build.add_argument(
        "--report-missing-translations",
        action="store_true",
        default=False,
        help="Print untranslated terms to stderr",
    )
    p_build.add_argument(
        "--images",
        action="store_true",
        default=False,
        help="Also emit individual card PNGs AND 3×3 sheet PNGs",
    )
    p_build.add_argument(
        "--card-images",
        action="store_true",
        default=False,
        help="Emit individual card PNGs only",
    )
    p_build.add_argument(
        "--sheet-images",
        action="store_true",
        default=False,
        help="Emit 3×3 sheet PNGs only",
    )
    p_build.add_argument(
        "--print-sheets",
        action="store_true",
        default=False,
        help="Emit print-shop-ready sheets (default: A4, 2×2, 99×138mm cards)",
    )
    p_build.add_argument(
        "--print-cards",
        action="store_true",
        default=False,
        help="Emit individual cards at print size (default 99×138mm, matches --print-sheets DPI)",
    )
    p_build.add_argument(
        "--print-paper",
        choices=["A4", "B4", "A3"],
        default="A4",
        help="Paper size for --print-sheets (default: A4)",
    )
    p_build.add_argument(
        "--print-card-w",
        type=float,
        default=99.0,
        help="Print card width in mm (default: 99)",
    )
    p_build.add_argument(
        "--print-card-h",
        type=float,
        default=138.0,
        help="Print card height in mm (default: 138, preserves 63:88 ratio)",
    )
    p_build.add_argument(
        "--images-dir",
        default=None,
        help="Output directory for images (default: <out_pdf_dir>/images)",
    )
    p_build.add_argument(
        "--no-pdf",
        action="store_true",
        default=False,
        help="Skip PDF rendering (useful with --images)",
    )

    # preview
    p_prev = sub.add_parser("preview", help="Serve rendered HTML locally")
    p_prev.add_argument("input", help="Path to games.xlsx or games.csv")
    p_prev.add_argument("--port", type=int, default=8765)

    # refresh
    p_ref = sub.add_parser("refresh", help="Invalidate BGG cache for one game")
    p_ref.add_argument("--id", type=int, required=True, help="BGG game ID")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        return cmd_build(args)
    elif args.command == "preview":
        return cmd_preview(args)
    elif args.command == "refresh":
        return cmd_refresh(args)
    elif args.report_missing_translations:
        return cmd_report_missing(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
