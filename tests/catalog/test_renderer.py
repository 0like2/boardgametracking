"""Tests for Renderer: HTML snapshot and structure checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.catalog.models import GameData
from src.catalog.renderer import Renderer
from src.catalog.translator import Translator


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
        categories=["Economic", "Strategy"],
        mechanics=["Worker Placement"],
        designers=["Gavan Brown", "Matt Tolman"],
        is_expansion=False,
        base_game_id=None,
        base_game_kr=None,
        language_dependence=None,
        shelf_location="A-1-01",
        accent_kind=None,
    )
    defaults.update(overrides)
    return GameData(**defaults)


@pytest.fixture
def renderer() -> Renderer:
    return Renderer()


@pytest.fixture
def translator() -> Translator:
    return Translator()


class TestRendererHTML:
    def test_renders_html_string(self, renderer: Renderer, translator: Translator):
        games = [_make_game()]
        html = renderer.render(games, translator)
        assert isinstance(html, str)
        assert len(html) > 100

    def test_contains_doctype(self, renderer: Renderer, translator: Translator):
        html = renderer.render([_make_game()], translator)
        assert "<!DOCTYPE html>" in html

    def test_contains_korean_title(self, renderer: Renderer, translator: Translator):
        html = renderer.render([_make_game()], translator)
        assert "브라스: 버밍엄" in html

    def test_contains_english_title(self, renderer: Renderer, translator: Translator):
        html = renderer.render([_make_game()], translator)
        assert "Brass: Birmingham" in html

    def test_contains_rating(self, renderer: Renderer, translator: Translator):
        html = renderer.render([_make_game(rating=8.678)], translator)
        assert "8.7" in html

    def test_contains_translated_category(
        self, renderer: Renderer, translator: Translator
    ):
        html = renderer.render([_make_game(categories=["Economic"])], translator)
        assert "경제" in html

    def test_expansion_label_present(
        self, renderer: Renderer, translator: Translator
    ):
        html = renderer.render(
            [_make_game(is_expansion=True, base_game_kr="글룸헤이븐")], translator
        )
        assert "확장판" in html
        assert "글룸헤이븐" in html

    def test_expansion_label_absent_for_base_game(
        self, renderer: Renderer, translator: Translator
    ):
        html = renderer.render([_make_game(is_expansion=False)], translator)
        assert "expansion-banner" not in html

    def test_shelf_text_in_html(self, renderer: Renderer, translator: Translator):
        html = renderer.render([_make_game(shelf_location="B-2-05")], translator)
        assert "B-2-05" in html

    def test_pagination_creates_pages(
        self, renderer: Renderer, translator: Translator
    ):
        games = [_make_game(bgg_id=i, name_kr=f"게임 {i}", name_en=f"Game {i}") for i in range(1, 6)]
        html = renderer.render(games, translator)
        # 5 games with 4 per page = 2 pages
        assert html.count('class="page"') == 2

    def test_single_page_for_four_games(
        self, renderer: Renderer, translator: Translator
    ):
        games = [_make_game(bgg_id=i, name_kr=f"게임 {i}", name_en=f"Game {i}") for i in range(1, 5)]
        html = renderer.render(games, translator)
        assert html.count('class="page"') == 1

    def test_empty_game_list(self, renderer: Renderer, translator: Translator):
        html = renderer.render([], translator)
        assert isinstance(html, str)

    def test_cards_per_page_respected(self, translator: Translator):
        renderer = Renderer(cards_per_page=2)
        games = [_make_game(bgg_id=i, name_kr=f"게임 {i}", name_en=f"Game {i}") for i in range(1, 5)]
        html = renderer.render(games, translator)
        # 4 games with 2 per page = 2 pages
        assert html.count('class="page"') == 2
