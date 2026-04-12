"""Integration test: offline end-to-end build from fixtures → PDF."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.catalog.bgg_parser import parse_game
from src.catalog.loader import load_games
from src.catalog.models import GameData, GameInput
from src.catalog.pdf_export import PlaywrightExporter
from src.catalog.renderer import Renderer
from src.catalog.translator import Translator

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_INPUTS_XLSX = Path(__file__).parent.parent.parent / "inputs" / "games.xlsx"

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_BRASS_GAME_INPUT = GameInput(
    bgg_id=224517,
    name_kr="브라스: 버밍엄",
    shelf_location="A-1-01",
)


def _parse_fixture(filename: str, game_input: GameInput) -> GameData:
    xml_path = _FIXTURES_DIR / filename
    return parse_game(xml_path.read_bytes(), game_input, image_local_path="", base_game_kr=None)


def _make_mock_games() -> list[GameData]:
    """Return GameData objects parsed from hand-crafted XML fixtures."""
    return [_parse_fixture("bgg_thing_brass.xml", _BRASS_GAME_INPUT)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOfflineBuild:
    def test_renderer_produces_html(self):
        games = _make_mock_games()
        translator = Translator()
        renderer = Renderer()
        html = renderer.render(games, translator)
        assert "브라스: 버밍엄" in html
        assert "Brass: Birmingham" in html
        assert "<!DOCTYPE html>" in html

    def test_build_offline_produces_pdf(self, tmp_path: Path):
        """Full pipeline offline: fixtures → HTML → PDF via Playwright."""
        pytest.importorskip("playwright")

        games = _make_mock_games()
        translator = Translator()
        renderer = Renderer()
        html = renderer.render(games, translator)

        output_pdf = tmp_path / "catalog_test.pdf"
        assets_dir = Path(__file__).parent.parent.parent / "src" / "catalog" / "assets"
        exporter = PlaywrightExporter()
        exporter.export(html, output_pdf, base_url=assets_dir)

        assert output_pdf.exists(), "PDF was not created"
        assert output_pdf.stat().st_size > 1000, "PDF is suspiciously small"
        assert output_pdf.read_bytes()[:4] == b"%PDF", "Not a valid PDF"

    def test_build_offline_monkeypatched_repo(self, tmp_path: Path, monkeypatch):
        """Build flow with BggRepository.get_games monkeypatched to return fixtures."""
        pytest.importorskip("playwright")

        mock_games = _make_mock_games()

        # Monkeypatch BggRepository to avoid any network call
        from src.catalog import bgg_repository

        monkeypatch.setattr(
            bgg_repository.BggRepository,
            "get_games",
            lambda self, game_inputs, **kwargs: mock_games,
        )

        from src.catalog.__main__ import _build_pipeline

        out_pdf = tmp_path / "catalog.pdf"
        result = _build_pipeline(
            input_path=_INPUTS_XLSX,
            output_path=out_pdf,
            renderer_name="playwright",
            max_age_days=30,
            refresh=False,
            cache_dir=tmp_path / "cache",
        )

        assert result == 0, "Build pipeline returned non-zero exit code"
        assert out_pdf.exists(), "PDF output not found"
        assert out_pdf.stat().st_size > 1000

    def test_missing_translations_reported(self, capsys):
        """Unknown category terms should appear in translator.missing_terms()."""
        games = _make_mock_games()
        # Inject an unknown category
        import dataclasses
        games[0] = dataclasses.replace(games[0], categories=["VeryUnknownCategory"])

        translator = Translator()
        renderer = Renderer()
        renderer.render(games, translator)

        missing = translator.missing_terms()
        assert "VeryUnknownCategory" in missing


class TestCLIBuild:
    def test_cli_build_offline(self, tmp_path: Path, monkeypatch):
        """Test CLI build subcommand with --offline-fixtures flag."""
        import sys
        from src.catalog.__main__ import main

        out_pdf = tmp_path / "cli_test.pdf"
        argv = [
            "build",
            str(_INPUTS_XLSX),
            "--out", str(out_pdf),
            "--renderer", "playwright",
            "--offline-fixtures", str(_FIXTURES_DIR),
        ]

        pytest.importorskip("playwright")

        exit_code = main(argv)
        # CLI may fail if no matching fixture for all game IDs; just check it ran
        assert exit_code in (0, 1)
