"""Automatic grouping + ordering of GameData for catalog rendering.

Groups are derived from Boardlife metadata (``game_type`` = 카테고리 and
``categories`` = 테마). Within each group, expansions follow their base
game and the rest is sorted by Korean name.
"""

from __future__ import annotations

from src.catalog.models import GameData

# Display order of groups (first group appears first in the catalog)
GROUP_ORDER: list[str] = [
    "파티/가족",
    "전략/경제",
    "추리/미스터리",
    "테마/어드벤처",
    "추상/2인",
    "전쟁",
    "아동",
    "기타",
]


_MYSTERY_THEMES = {"살인/미스터리", "추리", "미스터리"}


def _group_from_fields(gd: GameData) -> str:
    """Raw group derivation from a single GameData, ignoring base-game inheritance."""
    themes = set(gd.categories or [])

    # Theme-first: murder mystery wins over whatever the high-level category
    # says, because that's how people search for these games ("머더미스터리끼리")
    if themes & _MYSTERY_THEMES:
        return "추리/미스터리"

    gt = gd.game_type or ""
    if "파티" in gt or "가족" in gt:
        return "파티/가족"
    if "전략" in gt:
        return "전략/경제"
    if "테마" in gt:
        return "테마/어드벤처"
    if "추상" in gt:
        return "추상/2인"
    if "전쟁" in gt:
        return "전쟁"
    if "아동" in gt:
        return "아동"
    return "기타"


def build_group_map(games: list[GameData]) -> dict[int, str]:
    """Return {id(game_obj): group_name} with expansion-base inheritance applied.

    Uses Python object identity (``id()``) — not ``bgg_id`` — because the
    input catalog may contain duplicate bgg_ids (e.g. a local game that
    hasn't been matched to BGG, or two rows sharing the same placeholder).
    """
    by_bgg: dict[int, GameData] = {}
    for g in games:
        by_bgg.setdefault(g.bgg_id, g)
    detected_by_obj = _detect_expansion_bases(games)

    result: dict[int, str] = {}
    for g in games:
        own = _group_from_fields(g)
        if own != "기타":
            result[id(g)] = own
            continue
        base: GameData | None = None
        if g.base_game_id and g.base_game_id in by_bgg:
            base = by_bgg[g.base_game_id]
        elif id(g) in detected_by_obj:
            base = detected_by_obj[id(g)]
        result[id(g)] = _group_from_fields(base) if base is not None else own
    return result


def _detect_expansion_bases(
    games: list[GameData],
) -> dict[int, GameData]:
    """Return {id(expansion_game): base_game_obj} via name-prefix heuristic.

    Detection rules:
      1. Name contains ":" (or "：", " - ") -> prefix before the separator.
      2. If that prefix exactly matches another game's ``name_kr``, treat
         this as an expansion of that game.

    Keyed by ``id()`` rather than ``bgg_id`` so that rows sharing a
    duplicated bgg_id don't collide in the lookup map.
    """
    name_to_game: dict[str, GameData] = {}
    for g in games:
        key = (g.name_kr or "").strip()
        if key:
            name_to_game.setdefault(key, g)

    result: dict[int, GameData] = {}
    for g in games:
        name = (g.name_kr or "").strip()
        if not name:
            continue
        for sep in (":", "：", " - "):
            if sep in name:
                prefix = name.split(sep, 1)[0].strip()
                if prefix and prefix != name and prefix in name_to_game:
                    base = name_to_game[prefix]
                    if base is not g:
                        result[id(g)] = base
                        break
    return result


def sort_games(games: list[GameData]) -> list[GameData]:
    """Return a new list of games sorted by (group, base-game affinity, name).

    Sort rules:
      1. Group order as defined in ``GROUP_ORDER``
      2. Within a group, expansions follow their base game (if the base is
         in the same group); otherwise by Korean name
      3. Expansions inherit their base game's group (so "도미니언: 약속된
         번영" follows "도미니언" even when the expansion row lacks category
         metadata on Boardlife)
      4. Ties broken by ``name_kr`` ascending
    """
    by_bgg: dict[int, GameData] = {}
    for g in games:
        by_bgg.setdefault(g.bgg_id, g)

    # Heuristic base detection (xlsx has no base_game_id column)
    detected_bases = _detect_expansion_bases(games)

    group_map = build_group_map(games)

    def effective_base(g: GameData) -> GameData | None:
        if g.base_game_id and g.base_game_id in by_bgg:
            return by_bgg[g.base_game_id]
        return detected_bases.get(id(g))

    def sort_key(g: GameData) -> tuple:
        group = group_map.get(id(g), "기타")
        try:
            group_idx = GROUP_ORDER.index(group)
        except ValueError:
            group_idx = len(GROUP_ORDER)

        base = effective_base(g)
        if base is not None:
            anchor_name = base.name_kr or base.name_en
            expansion_flag = 1  # expansion sorts after base
        else:
            anchor_name = g.name_kr or g.name_en
            expansion_flag = 0

        return (
            group_idx,
            anchor_name.lower() if anchor_name else "",
            expansion_flag,
            (g.name_kr or g.name_en or "").lower(),
        )

    return sorted(games, key=sort_key)


def group_summary(games: list[GameData]) -> list[tuple[str, int]]:
    """For logging: return [(group_name, count), ...] in display order."""
    group_map = build_group_map(games)
    counts: dict[str, int] = {}
    for g in games:
        grp = group_map.get(id(g), "기타")
        counts[grp] = counts.get(grp, 0) + 1
    result: list[tuple[str, int]] = []
    for grp in GROUP_ORDER:
        if grp in counts:
            result.append((grp, counts[grp]))
    # Any unexpected groups (shouldn't happen, but safe)
    for grp in counts:
        if grp not in GROUP_ORDER:
            result.append((grp, counts[grp]))
    return result
