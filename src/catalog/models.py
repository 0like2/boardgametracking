"""Domain dataclasses for the board game catalog pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GameInput:
    """Raw user-supplied row from inputs/games.xlsx or games.csv."""

    bgg_id: int
    name_kr: str
    shelf_location: str
    boardlife_url: str | None = None
    base_game_id: int | None = None
    accent_kind: str | None = None  # "new" | "expansion" | None
    notes: str | None = None


@dataclass
class GameData:
    """Merged BGG API response + user input. All category/mechanic/designer
    fields are stored in English canonical form; translation happens only in
    CardViewModel.from_game_data().
    """

    bgg_id: int
    name_kr: str
    name_en: str
    year_published: int | None
    image_url: str
    thumbnail_url: str
    image_local_path: str
    min_players: int
    max_players: int
    best_players: str | None
    min_playing_time: int | None
    max_playing_time: int | None
    playing_time: int
    min_age: int | None
    weight: float | None
    rating: float | None
    categories: list[str] = field(default_factory=list)   # English canonical
    mechanics: list[str] = field(default_factory=list)    # English canonical
    designers: list[str] = field(default_factory=list)    # English canonical
    is_expansion: bool = False
    base_game_id: int | None = None
    base_game_kr: str | None = None
    language_dependence: str | None = None
    shelf_location: str = ""
    accent_kind: str | None = None
    game_type: str = ""  # Boardlife 카테고리 (전략게임/파티게임/아동게임/...)
