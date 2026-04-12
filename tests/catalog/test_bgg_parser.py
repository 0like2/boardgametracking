"""Tests for bgg_parser: XML → GameData and extract_best_players algorithm."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.catalog.bgg_parser import MIN_POLL_VOTES, extract_best_players, parse_game
from src.catalog.errors import FieldMissingError, GameSkipError
from src.catalog.models import GameInput

FIXTURES = Path(__file__).parent / "fixtures"


def _poll_xml(filename: str):
    return etree.parse(str(FIXTURES / filename)).getroot()


def _make_input(bgg_id: int = 224517, name_kr: str = "브라스: 버밍엄") -> GameInput:
    return GameInput(bgg_id=bgg_id, name_kr=name_kr, shelf_location="A-1-01")


# ---------------------------------------------------------------------------
# extract_best_players
# ---------------------------------------------------------------------------

class TestExtractBestPlayers:
    def test_brass_birmingham_returns_3_4(self):
        poll = _poll_xml("poll_brass_birmingham.xml")
        assert extract_best_players(poll) == "3-4"

    def test_split_votes_returns_none(self):
        poll = _poll_xml("poll_split_votes.xml")
        assert extract_best_players(poll) is None

    def test_single_winner_returns_3(self):
        poll = _poll_xml("poll_single_winner.xml")
        assert extract_best_players(poll) == "3"

    def test_no_data_below_min_votes_returns_none(self):
        poll = _poll_xml("poll_no_data.xml")
        # totalvotes=5 < MIN_POLL_VOTES=30
        assert extract_best_players(poll) is None

    def test_disjoint_winners_picks_highest_best_votes(self):
        poll = _poll_xml("poll_disjoint_winners.xml")
        # winners: 2 (150 best) and 5 (200 best) — non-contiguous → pick 5
        assert extract_best_players(poll) == "5"


# ---------------------------------------------------------------------------
# parse_game — full field assertion against bgg_thing_brass.xml
# ---------------------------------------------------------------------------

class TestParseGameBrass:
    @pytest.fixture(autouse=True)
    def load_xml(self):
        self.xml_bytes = (FIXTURES / "bgg_thing_brass.xml").read_bytes()
        self.gi = _make_input()

    def test_name_en(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.name_en == "Brass: Birmingham"

    def test_name_kr_from_input(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.name_kr == "브라스: 버밍엄"

    def test_year_published(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.year_published == 2018

    def test_players(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.min_players == 2
        assert gd.max_players == 4

    def test_best_players(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.best_players == "3-4"

    def test_playing_time(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.playing_time == 120
        assert gd.min_playing_time == 60
        assert gd.max_playing_time == 120

    def test_min_age(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.min_age == 14

    def test_weight(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.weight == pytest.approx(3.89, abs=0.01)

    def test_rating(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.rating == pytest.approx(8.678, abs=0.001)

    def test_categories(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert "Economic" in gd.categories
        assert "Industry / Manufacturing" in gd.categories

    def test_mechanics(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert "Network and Route Building" in gd.mechanics
        assert "Worker Placement" in gd.mechanics

    def test_designers(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert "Martin Wallace" in gd.designers

    def test_is_expansion_false(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.is_expansion is False

    def test_image_url_has_https(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.image_url.startswith("https://")

    def test_language_dependence(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.language_dependence == "No necessary in-game text"

    def test_shelf_location(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.shelf_location == "A-1-01"

    def test_bgg_id(self):
        gd = parse_game(self.xml_bytes, self.gi)
        assert gd.bgg_id == 224517


class TestParseGameExpansion:
    def test_is_expansion_true(self):
        xml_bytes = (FIXTURES / "bgg_thing_expansion.xml").read_bytes()
        gi = GameInput(
            bgg_id=247030,
            name_kr="테라포밍 마스: 서막",
            shelf_location="B-1-06",
            base_game_id=167791,
        )
        gd = parse_game(xml_bytes, gi)
        assert gd.is_expansion is True
        assert gd.base_game_id == 167791


class TestParseGameNoStats:
    def test_weight_none_when_no_statistics(self):
        xml_bytes = (FIXTURES / "bgg_thing_no_stats.xml").read_bytes()
        gi = GameInput(bgg_id=99999, name_kr="테스트 게임", shelf_location="Z-9-99")
        gd = parse_game(xml_bytes, gi)
        assert gd.weight is None
        assert gd.rating is None

    def test_best_players_none_when_no_votes(self):
        xml_bytes = (FIXTURES / "bgg_thing_no_stats.xml").read_bytes()
        gi = GameInput(bgg_id=99999, name_kr="테스트 게임", shelf_location="Z-9-99")
        gd = parse_game(xml_bytes, gi)
        assert gd.best_players is None


class TestParseGameErrors:
    def test_malformed_xml_raises_game_skip(self):
        gi = _make_input()
        with pytest.raises(GameSkipError):
            parse_game(b"<not valid xml", gi)

    def test_missing_name_raises_field_missing(self):
        xml = b"""<?xml version="1.0"?>
<items><item type="boardgame" id="224517">
<image>//cf.geekdo-images.com/img.jpg</image>
<thumbnail>//cf.geekdo-images.com/thumb.jpg</thumbnail>
<minplayers value="2"/><maxplayers value="4"/>
<playingtime value="60"/>
</item></items>"""
        gi = _make_input()
        with pytest.raises(FieldMissingError) as exc_info:
            parse_game(xml, gi)
        assert exc_info.value.field == "name_en"
