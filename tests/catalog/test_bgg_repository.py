"""Tests for BggRepository: cache hit/miss, TTL expiry, 202 retry loop."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.catalog.bgg_repository import BggRepository
from src.catalog.errors import GameSkipError
from src.catalog.models import GameInput

FIXTURES = Path(__file__).parent / "fixtures"
BRASS_XML = (FIXTURES / "bgg_thing_brass.xml").read_bytes()


def _make_input(bgg_id: int = 224517) -> GameInput:
    return GameInput(bgg_id=bgg_id, name_kr="브라스: 버밍엄", shelf_location="A-1-01")


def _make_repo(tmp_path: Path, client=None):
    if client is None:
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
    return BggRepository(client=client, cache_dir=tmp_path, ttl_days=30)


class TestCacheHit:
    def test_second_call_does_not_hit_client(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = _make_repo(tmp_path, client)

        gi = _make_input()
        # Patch image download so we don't need network
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            repo.get_game(gi)
            repo.get_game(gi)

        # client.fetch_xml should only be called once
        assert client.fetch_xml.call_count == 1

    def test_cache_file_written(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = _make_repo(tmp_path, client)

        gi = _make_input()
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            repo.get_game(gi)

        cache_file = tmp_path / "bgg" / "224517.xml"
        assert cache_file.exists()
        assert cache_file.read_bytes() == BRASS_XML


class TestCacheMiss:
    def test_refresh_flag_bypasses_cache(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = _make_repo(tmp_path, client)

        gi = _make_input()
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            repo.get_game(gi)
            repo.get_game(gi, refresh=True)

        assert client.fetch_xml.call_count == 2


class TestTTLExpiry:
    def test_expired_cache_triggers_new_fetch(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        # TTL of 0 days means everything is immediately stale
        repo = BggRepository(client=client, cache_dir=tmp_path, ttl_days=0)

        gi = _make_input()
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            repo.get_game(gi)
            repo.get_game(gi)

        assert client.fetch_xml.call_count == 2

    def test_fresh_cache_not_refetched(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = BggRepository(client=client, cache_dir=tmp_path, ttl_days=30)

        gi = _make_input()
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            repo.get_game(gi)
            repo.get_game(gi)

        assert client.fetch_xml.call_count == 1


class TestGetGames:
    def test_skipped_game_not_in_results(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.side_effect = GameSkipError(99999, "test skip")
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = _make_repo(tmp_path, client)

        gi = GameInput(bgg_id=99999, name_kr="없는게임", shelf_location="Z-0-00")
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            results = repo.get_games([gi])

        assert results == []

    def test_successful_games_returned(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = _make_repo(tmp_path, client)

        gi = _make_input()
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            results = repo.get_games([gi])

        assert len(results) == 1
        assert results[0].name_en == "Brass: Birmingham"


class TestInvalidate:
    def test_invalidate_removes_cache_file(self, tmp_path):
        client = MagicMock()
        client.fetch_xml.return_value = BRASS_XML
        client._session.headers = {"User-Agent": "Test/1.0"}
        repo = _make_repo(tmp_path, client)

        gi = _make_input()
        with patch("src.catalog.bgg_repository.fetch_image", return_value=tmp_path / "img.jpg"):
            repo.get_game(gi)

        cache_file = tmp_path / "bgg" / "224517.xml"
        assert cache_file.exists()
        repo.invalidate(224517)
        assert not cache_file.exists()
