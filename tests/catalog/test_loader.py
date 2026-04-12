"""Tests for loader.py: Excel/CSV → list[GameInput]."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from src.catalog.errors import InvalidInputError
from src.catalog.loader import load_games

FIXTURES = Path(__file__).parent / "fixtures"


def _write_xlsx(tmp_path: Path, rows: list[list], headers=None) -> Path:
    if headers is None:
        headers = ["bgg_id", "name_kr", "shelf_location", "base_game_id", "accent_kind", "notes"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    p = tmp_path / "test_games.xlsx"
    wb.save(str(p))
    return p


class TestLoadGamesXlsx:
    def test_reads_four_games(self):
        path = Path("inputs/games.xlsx")
        if not path.exists():
            pytest.skip("inputs/games.xlsx not found")
        games = load_games(path)
        assert len(games) == 4

    def test_first_game_fields(self):
        path = Path("inputs/games.xlsx")
        if not path.exists():
            pytest.skip("inputs/games.xlsx not found")
        games = load_games(path)
        brass = next(g for g in games if g.bgg_id == 224517)
        assert brass.name_kr == "브라스: 버밍엄"
        assert brass.shelf_location == "A-1-01"

    def test_expansion_has_base_game_id(self):
        path = Path("inputs/games.xlsx")
        if not path.exists():
            pytest.skip("inputs/games.xlsx not found")
        games = load_games(path)
        prelude = next(g for g in games if g.bgg_id == 247030)
        assert prelude.base_game_id == 167791
        assert prelude.accent_kind == "expansion"


class TestLoadGamesFromTmp:
    def test_basic_load(self, tmp_path):
        p = _write_xlsx(tmp_path, [
            [224517, "브라스", "A-1-01", "", "", ""],
            [174430, "글룸헤이븐", "A-2-03", "", "", ""],
        ])
        games = load_games(p)
        assert len(games) == 2
        assert games[0].bgg_id == 224517
        assert games[1].bgg_id == 174430

    def test_missing_required_column_raises(self, tmp_path):
        p = _write_xlsx(tmp_path, [[224517, "브라스"]], headers=["bgg_id", "name_kr"])
        with pytest.raises(InvalidInputError, match="shelf_location"):
            load_games(p)

    def test_invalid_bgg_id_raises(self, tmp_path):
        p = _write_xlsx(tmp_path, [["abc", "브라스", "A-1-01", "", "", ""]])
        with pytest.raises(InvalidInputError, match="not a valid integer"):
            load_games(p)

    def test_empty_bgg_id_raises(self, tmp_path):
        p = _write_xlsx(tmp_path, [["", "브라스", "A-1-01", "", "", ""]])
        with pytest.raises(InvalidInputError):
            load_games(p)

    def test_empty_name_kr_warns_but_does_not_raise(self, tmp_path, capsys):
        p = _write_xlsx(tmp_path, [[224517, "", "A-1-01", "", "", ""]])
        games = load_games(p)
        assert len(games) == 1
        assert games[0].name_kr == ""
        captured = capsys.readouterr()
        assert "name_kr" in captured.err

    def test_optional_fields_none_when_blank(self, tmp_path):
        p = _write_xlsx(tmp_path, [[224517, "브라스", "A-1-01", "", "", ""]])
        games = load_games(p)
        assert games[0].base_game_id is None
        assert games[0].accent_kind is None
        assert games[0].notes is None

    def test_expansion_accent_kind(self, tmp_path):
        p = _write_xlsx(tmp_path, [[247030, "서막", "B-1-06", 167791, "expansion", "확장"]])
        games = load_games(p)
        assert games[0].base_game_id == 167791
        assert games[0].accent_kind == "expansion"
        assert games[0].notes == "확장"

    def test_unsupported_format_raises(self, tmp_path):
        p = tmp_path / "games.json"
        p.write_text("{}")
        with pytest.raises(InvalidInputError, match="Unsupported"):
            load_games(p)

    def test_csv_load(self, tmp_path):
        p = tmp_path / "games.csv"
        p.write_text("bgg_id,name_kr,shelf_location\n224517,브라스,A-1-01\n", encoding="utf-8")
        games = load_games(p)
        assert len(games) == 1
        assert games[0].bgg_id == 224517
