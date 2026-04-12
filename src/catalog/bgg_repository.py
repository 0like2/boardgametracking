"""Facade: cache-check → BGG client → parser → GameData with TTL.

As of 2025-07-02 BGG's XML API requires an authorized Bearer token, so when
a game row supplies a `boardlife_url` we prefer to source metadata from
Boardlife (scraped HTML) and only fall back to BGG if Boardlife fails.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

from src.catalog.bgg_client import BggClient
from src.catalog.bgg_parser import parse_game
from src.catalog.boardlife_parser import (
    extract_boardlife_id,
    normalize_boardlife_url,
    parse_boardlife_html,
)
from src.catalog.errors import BggApiError, GameSkipError
from src.catalog.image_cache import fetch_image
from src.catalog.models import GameData, GameInput


class BggRepository:
    """High-level facade that orchestrates the full fetch pipeline.

    Cache layout:
        cache_dir/bgg/{bgg_id}.xml   — raw XML, TTL applies
        cache_dir/images/{bgg_id}.jpg — downscaled image, no TTL
    """

    def __init__(
        self,
        client: BggClient,
        cache_dir: Path,
        ttl_days: int = 30,
    ) -> None:
        self._client = client
        self._cache_dir = cache_dir
        self._ttl_sec = ttl_days * 86_400
        bgg_dir = cache_dir / "bgg"
        bgg_dir.mkdir(parents=True, exist_ok=True)
        self._boardlife_dir = cache_dir / "boardlife"
        self._boardlife_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_game(
        self,
        game_input: GameInput,
        *,
        refresh: bool = False,
        id_to_name_kr: dict[int, str] | None = None,
    ) -> GameData:
        """Fetch (or load from cache) a single game and return GameData.

        Source priority:
          1. Boardlife HTML (if ``boardlife_url`` is set on the input row)
          2. BGG XML API (requires an authorized Bearer token as of 2025-07)

        id_to_name_kr is an optional mapping used to resolve base_game_kr.
        """
        base_game_kr: str | None = None
        if game_input.base_game_id and id_to_name_kr:
            base_game_kr = id_to_name_kr.get(game_input.base_game_id)

        game_data: GameData | None = None
        cache_key: str | None = None  # stable key for image + HTML caches

        # --- Source 1: Boardlife ------------------------------------------
        bl_url = getattr(game_input, "boardlife_url", None)
        bl_id: str | None = None
        if bl_url:
            normalized = normalize_boardlife_url(bl_url)
            bl_id = extract_boardlife_id(normalized)
            if bl_id:
                cache_key = f"bl_{bl_id}"
                try:
                    html_bytes = self._get_boardlife_html(
                        cache_key,
                        normalized,
                        refresh=refresh,
                    )
                    game_data = parse_boardlife_html(
                        html_bytes,
                        game_input,
                        image_local_path="",
                        base_game_kr=base_game_kr,
                    )
                except Exception as exc:
                    print(
                        f"Warning: Boardlife fetch failed for {game_input.name_kr} ({cache_key}): {exc}. Falling back to BGG.",
                        file=sys.stderr,
                    )

        # --- Source 2: BGG (fallback) -------------------------------------
        if game_data is None:
            cache_key = f"bgg_{game_input.bgg_id}"
            try:
                xml_bytes = self._get_xml(game_input.bgg_id, refresh=refresh)
            except (BggApiError, GameSkipError) as exc:
                print(
                    f"Warning: BGG data fetch failed for bgg_id={game_input.bgg_id}: {exc}. Using empty fallback.",
                    file=sys.stderr,
                )
                xml_bytes = (
                    f"<items><item id='{game_input.bgg_id}' type='boardgame'></item></items>"
                ).encode("utf-8")

            game_data = parse_game(
                xml_bytes,
                game_input,
                image_local_path="",
                base_game_kr=base_game_kr,
            )

        # --- Image download + local cache ---------------------------------
        final_image_url = game_data.image_url
        image_key = cache_key or f"bgg_{game_input.bgg_id}"
        try:
            if final_image_url:
                img_path = fetch_image(
                    image_key,
                    final_image_url,
                    self._cache_dir,
                    user_agent=self._client._session.headers.get(
                        "User-Agent", "Mozilla/5.0"
                    ),
                )
                game_data = _replace(game_data, image_local_path=str(img_path))
        except Exception as exc:
            print(
                f"Warning: Image fetch failed for {game_input.name_kr} ({image_key}): {exc}",
                file=sys.stderr,
            )

        return game_data

    # ------------------------------------------------------------------
    # Boardlife HTML cache
    # ------------------------------------------------------------------

    def _boardlife_cache_path(self, cache_key: str) -> Path:
        return self._boardlife_dir / f"{cache_key}.html"

    def _get_boardlife_html(
        self, cache_key: str, url: str, *, refresh: bool
    ) -> bytes:
        """Return cached Boardlife HTML or fetch-and-cache."""
        cache_path = self._boardlife_cache_path(cache_key)
        if not refresh and self._is_fresh(cache_path):
            return cache_path.read_bytes()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.content
        cache_path.write_bytes(data)
        return data

    def get_games(
        self,
        game_inputs: list[GameInput],
        *,
        refresh: bool = False,
    ) -> list[GameData]:
        """Fetch multiple games, batching BGG API calls (max 20 per call).

        Games that fail are skipped with a stderr warning; they are NOT
        included in the returned list.
        """
        # Build a lookup so expansions can resolve base_game_kr
        id_to_name_kr = {gi.bgg_id: gi.name_kr for gi in game_inputs if gi.name_kr}

        results: list[GameData] = []
        for gi in game_inputs:
            try:
                gd = self.get_game(gi, refresh=refresh, id_to_name_kr=id_to_name_kr)
                results.append(gd)
            except (GameSkipError, BggApiError) as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
            except Exception as exc:
                print(
                    f"ERROR: Unexpected error for bgg_id={gi.bgg_id}: {exc}",
                    file=sys.stderr,
                )
        return results

    # ------------------------------------------------------------------
    # Internal cache helpers
    # ------------------------------------------------------------------

    def _cache_path(self, bgg_id: int) -> Path:
        return self._cache_dir / "bgg" / f"{bgg_id}.xml"

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < self._ttl_sec

    def _get_xml(self, bgg_id: int, *, refresh: bool) -> bytes:
        if bgg_id < 0:
            # Local-only game with no BGG ID -> return synthetic empty XML
            return f"<items><item id='{bgg_id}' type='boardgame'></item></items>".encode("utf-8")

        cache_path = self._cache_path(bgg_id)

        if not refresh and self._is_fresh(cache_path):
            return cache_path.read_bytes()

        xml_bytes = self._client.fetch_xml([bgg_id])
        cache_path.write_bytes(xml_bytes)
        return xml_bytes

    def invalidate(self, bgg_id: int) -> None:
        """Remove cached XML for a single game (used by malformed-XML path)."""
        p = self._cache_path(bgg_id)
        if p.exists():
            p.unlink()


def _replace(gd: GameData, **kwargs) -> GameData:
    """Return a new GameData with updated fields (dataclasses.replace equivalent)."""
    import dataclasses
    return dataclasses.replace(gd, **kwargs)
