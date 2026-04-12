"""Parse BGG XML API2 <thing> responses into GameData domain objects."""

from __future__ import annotations

import sys
from typing import Any

from lxml import etree

from src.catalog.errors import FieldMissingError, GameSkipError
from src.catalog.models import GameData, GameInput

MIN_POLL_VOTES = 30  # Noise cutoff for suggested_numplayers poll


def extract_best_players(poll_xml: Any) -> str | None:
    """Determine the recommended player count from a BGG suggested_numplayers poll.

    Implements the algorithm from plan §4.4.

    Returns a string like "3", "3-4", or None if data is insufficient.
    """
    total_votes = int(poll_xml.get("totalvotes", "0"))
    if total_votes < MIN_POLL_VOTES:
        return None

    candidates: list[tuple[int, int, int, int]] = []  # (np, best, rec, not_rec)
    for results in poll_xml.findall("results"):
        np_str = results.get("numplayers", "")
        if "+" in np_str:
            # e.g. "5+" — skip for now
            continue
        try:
            np = int(np_str)
        except ValueError:
            continue
        votes = {
            r.get("value"): int(r.get("numvotes", "0"))
            for r in results.findall("result")
        }
        candidates.append(
            (
                np,
                votes.get("Best", 0),
                votes.get("Recommended", 0),
                votes.get("Not Recommended", 0),
            )
        )

    # 2. Winners: Best > Recommended + NotRecommended (strict)
    winners = [np for (np, b, r, nr) in candidates if b > r + nr]
    if not winners:
        return None

    # 3. Single winner
    if len(winners) == 1:
        return str(winners[0])

    # 4. Contiguous range
    winners.sort()
    if winners[-1] - winners[0] == len(winners) - 1:
        return f"{winners[0]}-{winners[-1]}"

    # 5. Disjoint winners — pick the one with the highest Best vote count
    winner_set = set(winners)
    best_by_votes = max(
        ((np, b) for (np, b, _, _) in candidates if np in winner_set),
        key=lambda x: x[1],
    )
    return str(best_by_votes[0])


def _extract_language_dependence(thing_xml: Any) -> str | None:
    """Return the plurality language-dependence level from the BGG poll."""
    for poll in thing_xml.findall("poll"):
        if poll.get("name") != "language_dependence":
            continue
        best_votes = -1
        best_value: str | None = None
        for results in poll.findall("results"):
            for result in results.findall("result"):
                v = int(result.get("numvotes", "0"))
                if v > best_votes:
                    best_votes = v
                    best_value = result.get("value")
        return best_value
    return None


def parse_game(
    xml_bytes: bytes,
    game_input: GameInput,
    image_local_path: str = "",
    base_game_kr: str | None = None,
) -> GameData:
    """Parse raw BGG XML bytes into a GameData object.

    Raises FieldMissingError if name_en or image_url is absent.
    Raises GameSkipError for structurally invalid XML.
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise GameSkipError(game_input.bgg_id, f"XML parse error: {exc}") from exc

    # BGG batches multiple <thing> elements; find ours by id
    thing = None
    for el in root.findall("item"):
        if int(el.get("id", "0")) == game_input.bgg_id:
            thing = el
            break
    if thing is None:
        # Fallback: single-item response
        thing = root if root.tag == "item" else (root.find("item") or root)

    if thing is None or thing.tag not in {"item", "things"}:
        raise GameSkipError(game_input.bgg_id, "No <item> element found in XML.")

    # is_expansion
    item_type = thing.get("type", "boardgame")
    is_expansion = item_type == "boardgameexpansion"

    # name_en (fallback to kr if missing)
    name_en = ""
    for name_el in thing.findall("name"):
        if name_el.get("type") == "primary":
            name_en = name_el.get("value", "").strip()
            break
    if not name_en:
        name_en = game_input.name_kr or "Unknown"

    # image / thumbnail (optional for local/indie games)
    image_url_raw = (thing.findtext("image") or "").strip()
    if image_url_raw:
        image_url = image_url_raw if image_url_raw.startswith("http") else "https:" + image_url_raw
    else:
        image_url = ""

    thumbnail_url_raw = (thing.findtext("thumbnail") or "").strip()
    if thumbnail_url_raw:
        thumbnail_url = thumbnail_url_raw if thumbnail_url_raw.startswith("http") else "https:" + thumbnail_url_raw
    else:
        thumbnail_url = image_url

    # year_published
    year_el = thing.find("yearpublished")
    year_published: int | None = None
    if year_el is not None:
        try:
            year_published = int(year_el.get("value", ""))
        except (ValueError, TypeError):
            pass

    # player counts
    def _int_attr(tag: str, attr: str = "value") -> int | None:
        el = thing.find(tag)
        if el is None:
            return None
        try:
            return int(el.get(attr, ""))
        except (ValueError, TypeError):
            return None

    min_players = _int_attr("minplayers") or 1
    max_players = _int_attr("maxplayers") or min_players
    min_playing_time = _int_attr("minplaytime")
    max_playing_time = _int_attr("maxplaytime")
    playing_time = _int_attr("playingtime") or (max_playing_time or min_playing_time or 0)
    min_age = _int_attr("minage")

    # statistics (require stats=1 in query)
    stats_el = thing.find("statistics/ratings")
    weight: float | None = None
    rating: float | None = None
    if stats_el is not None:
        def _float_val(tag: str) -> float | None:
            el = stats_el.find(tag)
            if el is None:
                return None
            # BGG uses value="" attribute; fall back to text content
            raw = el.get("value") or (el.text or "")
            try:
                v = float(raw)
                return None if v == 0.0 else v
            except (ValueError, TypeError):
                return None

        weight = _float_val("averageweight")
        rating = _float_val("average")

    # categories / mechanics / designers
    categories: list[str] = []
    mechanics: list[str] = []
    designers: list[str] = []
    for link in thing.findall("link"):
        link_type = link.get("type", "")
        value = link.get("value", "").strip()
        if link_type == "boardgamecategory":
            categories.append(value)
        elif link_type == "boardgamemechanic":
            mechanics.append(value)
        elif link_type == "boardgamedesigner":
            designers.append(value)

    # best_players from poll
    best_players: str | None = None
    for poll in thing.findall("poll"):
        if poll.get("name") == "suggested_numplayers":
            best_players = extract_best_players(poll)
            break

    # language_dependence
    language_dependence = _extract_language_dependence(thing)

    # name_kr fallback
    name_kr = game_input.name_kr or name_en
    if not game_input.name_kr:
        print(
            f"Warning: name_kr missing for bgg_id={game_input.bgg_id}; using English name.",
            file=sys.stderr,
        )

    return GameData(
        bgg_id=game_input.bgg_id,
        name_kr=name_kr,
        name_en=name_en,
        year_published=year_published,
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        image_local_path=image_local_path,
        min_players=min_players,
        max_players=max_players,
        best_players=best_players,
        min_playing_time=min_playing_time,
        max_playing_time=max_playing_time,
        playing_time=playing_time,
        min_age=min_age,
        weight=weight,
        rating=rating,
        categories=categories,
        mechanics=mechanics,
        designers=designers,
        is_expansion=is_expansion or bool(game_input.base_game_id),
        base_game_id=game_input.base_game_id,
        base_game_kr=base_game_kr,
        language_dependence=language_dependence,
        shelf_location=game_input.shelf_location,
        accent_kind=game_input.accent_kind,
    )
