"""Tests for CardViewModel.from_game_data() formatting logic."""

from __future__ import annotations

import pytest

from src.catalog.models import GameData
from src.catalog.translator import Translator
from src.catalog.view_model import CardViewModel


def _make_game(**overrides) -> GameData:
    defaults = dict(
        bgg_id=224517,
        name_kr="브라스: 버밍엄",
        name_en="Brass: Birmingham",
        year_published=2018,
        image_url="https://example.com/img.jpg",
        thumbnail_url="https://example.com/thumb.jpg",
        image_local_path="/cache/images/224517.jpg",
        min_players=2,
        max_players=4,
        best_players="3-4",
        min_playing_time=60,
        max_playing_time=120,
        playing_time=120,
        min_age=14,
        weight=3.89,
        rating=8.678,
        categories=["Economic", "Industry / Manufacturing"],
        mechanics=["Network and Route Building", "Worker Placement"],
        designers=["Gavan Brown", "Matt Tolman", "Martin Wallace"],
        is_expansion=False,
        base_game_id=None,
        base_game_kr=None,
        language_dependence="No necessary in-game text",
        shelf_location="A-1-01",
        accent_kind=None,
    )
    defaults.update(overrides)
    return GameData(**defaults)


def _translator() -> Translator:
    return Translator()


class TestRatingText:
    def test_formats_one_decimal(self):
        vm = CardViewModel.from_game_data(_make_game(rating=8.678), _translator())
        assert vm.rating_text == "8.7"

    def test_dash_when_none(self):
        vm = CardViewModel.from_game_data(_make_game(rating=None), _translator())
        assert vm.rating_text == "—"

    def test_rating_visible_true(self):
        vm = CardViewModel.from_game_data(_make_game(rating=8.0), _translator())
        assert vm.rating_visible is True

    def test_rating_visible_false_when_none(self):
        vm = CardViewModel.from_game_data(_make_game(rating=None), _translator())
        assert vm.rating_visible is False


class TestPlayersText:
    def test_range_when_min_ne_max(self):
        vm = CardViewModel.from_game_data(_make_game(min_players=2, max_players=4), _translator())
        assert vm.players_text == "2-4"

    def test_single_when_equal(self):
        vm = CardViewModel.from_game_data(_make_game(min_players=3, max_players=3), _translator())
        assert vm.players_text == "3"

    def test_best_players_text(self):
        vm = CardViewModel.from_game_data(_make_game(best_players="3-4"), _translator())
        assert vm.best_players_text == "Best 3-4"

    def test_best_players_empty_when_none(self):
        vm = CardViewModel.from_game_data(_make_game(best_players=None), _translator())
        assert vm.best_players_text == ""


class TestTimeText:
    def test_range_when_min_ne_max(self):
        vm = CardViewModel.from_game_data(
            _make_game(min_playing_time=60, max_playing_time=120), _translator()
        )
        assert vm.time_text == "60-120'"

    def test_single_when_equal(self):
        vm = CardViewModel.from_game_data(
            _make_game(min_playing_time=90, max_playing_time=90, playing_time=90), _translator()
        )
        assert vm.time_text == "90'"

    def test_falls_back_to_playing_time(self):
        vm = CardViewModel.from_game_data(
            _make_game(min_playing_time=None, max_playing_time=None, playing_time=75),
            _translator(),
        )
        assert vm.time_text == "75'"


class TestAgeText:
    def test_formats_with_plus(self):
        vm = CardViewModel.from_game_data(_make_game(min_age=14), _translator())
        assert vm.age_text == "14+"

    def test_dash_when_none(self):
        vm = CardViewModel.from_game_data(_make_game(min_age=None), _translator())
        assert vm.age_text == "—"


class TestWeightText:
    def test_formats_one_decimal(self):
        vm = CardViewModel.from_game_data(_make_game(weight=3.89), _translator())
        assert vm.weight_text == "3.9"

    def test_dash_when_none(self):
        vm = CardViewModel.from_game_data(_make_game(weight=None), _translator())
        assert vm.weight_text == "—"


class TestCategoriesDisplay:
    def test_translates_top_two(self):
        vm = CardViewModel.from_game_data(
            _make_game(categories=["Economic", "Strategy"]), _translator()
        )
        assert vm.categories_display == "경제 · 전략"

    def test_only_first_two_used(self):
        vm = CardViewModel.from_game_data(
            _make_game(categories=["Economic", "Strategy", "Fantasy"]), _translator()
        )
        assert "판타지" not in vm.categories_display

    def test_dash_when_empty(self):
        vm = CardViewModel.from_game_data(_make_game(categories=[]), _translator())
        assert vm.categories_display == "—"

    def test_passthrough_unknown_term(self):
        vm = CardViewModel.from_game_data(
            _make_game(categories=["SomethingNew"]), _translator()
        )
        assert "SomethingNew" in vm.categories_display


class TestDesignersDisplay:
    def test_single_designer(self):
        vm = CardViewModel.from_game_data(_make_game(designers=["Vital Lacerda"]), _translator())
        assert vm.designers_display == "Vital Lacerda"

    def test_two_designers_joined(self):
        vm = CardViewModel.from_game_data(
            _make_game(designers=["Gavan Brown", "Matt Tolman"]), _translator()
        )
        assert vm.designers_display == "Gavan Brown, Matt Tolman"

    def test_only_first_two_of_three(self):
        vm = CardViewModel.from_game_data(
            _make_game(designers=["Gavan Brown", "Matt Tolman", "Martin Wallace"]), _translator()
        )
        assert vm.designers_display == "Gavan Brown, Matt Tolman"

    def test_dash_when_empty(self):
        vm = CardViewModel.from_game_data(_make_game(designers=[]), _translator())
        assert vm.designers_display == "—"


class TestShelfText:
    def test_includes_pin_emoji(self):
        vm = CardViewModel.from_game_data(_make_game(shelf_location="A-1-01"), _translator())
        assert vm.shelf_text == "📍 A-1-01"


class TestExpansionLabel:
    def test_none_when_not_expansion(self):
        vm = CardViewModel.from_game_data(
            _make_game(is_expansion=False, base_game_kr=None), _translator()
        )
        assert vm.expansion_label is None

    def test_label_with_base_game_name(self):
        vm = CardViewModel.from_game_data(
            _make_game(is_expansion=True, base_game_kr="테라포밍 마스"), _translator()
        )
        assert vm.expansion_label == "확장판 · 테라포밍 마스"

    def test_label_without_base_game_name(self):
        vm = CardViewModel.from_game_data(
            _make_game(is_expansion=True, base_game_kr=None), _translator()
        )
        assert vm.expansion_label == "확장판"


class TestGaugePct:
    def test_weight_gauge_pct(self):
        vm = CardViewModel.from_game_data(_make_game(weight=3.89), _translator())
        assert vm.weight_gauge_pct == pytest.approx(3.89 / 5 * 100, abs=0.1)

    def test_rating_gauge_pct(self):
        vm = CardViewModel.from_game_data(_make_game(rating=8.678), _translator())
        assert vm.rating_gauge_pct == pytest.approx(8.678 / 10 * 100, abs=0.1)

    def test_gauge_zero_when_none(self):
        vm = CardViewModel.from_game_data(_make_game(weight=None, rating=None), _translator())
        assert vm.weight_gauge_pct == 0.0
        assert vm.rating_gauge_pct == 0.0

    def test_gauge_clamped_at_100(self):
        vm = CardViewModel.from_game_data(_make_game(weight=6.0), _translator())
        assert vm.weight_gauge_pct == 100.0

    def test_image_path_uses_local_when_present(self):
        vm = CardViewModel.from_game_data(
            _make_game(image_local_path="/cache/images/224517.jpg"), _translator()
        )
        assert vm.image_path == "/cache/images/224517.jpg"

    def test_image_path_falls_back_to_url(self):
        vm = CardViewModel.from_game_data(
            _make_game(image_local_path=""), _translator()
        )
        assert vm.image_path == "https://example.com/img.jpg"
