"""CardViewModel: all formatted strings ready for Jinja2 templates."""

from __future__ import annotations

from dataclasses import dataclass

from src.catalog.models import GameData
from src.catalog.translator import Translator


@dataclass(frozen=True)
class CardViewModel:
    """Fully formatted view of a single game card.

    Templates MUST use only these fields — no formatting logic in Jinja2.
    """

    name_kr: str
    name_en: str
    image_path: str              # file:// or absolute path, ready for <img src>
    accent_color: str | None     # CSS color or None (Phase 2 hook)

    rating_text: str             # "8.6" or "—"
    rating_visible: bool

    players_text: str            # "2-4" or "4"
    best_players_text: str       # "Best 3-4" or ""
    time_text: str               # "60-120'" or "60'"
    age_text: str                # "14+" or "—"
    weight_text: str             # "3.8" or "—"

    categories_display: str      # "전략 · 경제" (top 2, Korean)
    mechanics_display_list: list[str]  # ["카드드래프트", "타일놓기"] (up to 3)
    designers_display: str       # "Vital Lacerda" or "A, B"
    shelf_text: str              # "📍 A-3-12"
    expansion_label: str | None  # "확장판 · 글룸헤이븐" or None
    bgg_id_text: str             # "ID: 224517"

    weight_gauge_pct: float      # 0..100
    rating_gauge_pct: float      # 0..100

    @classmethod
    def from_game_data(cls, gd: GameData, translator: Translator) -> "CardViewModel":
        """Convert a GameData domain object into a display-ready CardViewModel."""

        # --- rating ---
        rating_text = f"{gd.rating:.1f}" if gd.rating is not None else "—"
        rating_visible = gd.rating is not None

        # --- players ---
        if gd.min_players != gd.max_players:
            players_text = f"{gd.min_players}-{gd.max_players}"
        else:
            players_text = str(gd.min_players)

        best_players_text = f"Best {gd.best_players}" if gd.best_players else ""

        # --- time ---
        if (
            gd.min_playing_time is not None
            and gd.max_playing_time is not None
            and gd.min_playing_time != gd.max_playing_time
        ):
            time_text = f"{gd.min_playing_time}-{gd.max_playing_time}'"
        else:
            time_text = f"{gd.playing_time}'"

        # --- age ---
        age_text = f"{gd.min_age}+" if gd.min_age is not None else "—"

        # --- weight ---
        weight_text = f"{gd.weight:.1f}" if gd.weight is not None else "—"

        # --- categories: translate top 2, join with " · " ---
        translated_cats = [translator.translate(c) for c in gd.categories[:2]]
        categories_display = " · ".join(translated_cats) if translated_cats else "—"

        # --- mechanics: translate top 3 ---
        mechanics_display_list = [translator.translate(m) for m in gd.mechanics[:3]]

        # --- bgg_id ---
        bgg_id_text = f"ID: {gd.bgg_id}"

        # --- designers: first 1-2, joined with ", " ---
        if len(gd.designers) >= 2:
            designers_display = ", ".join(gd.designers[:2])
        elif gd.designers:
            designers_display = gd.designers[0]
        else:
            designers_display = "—"

        # --- shelf ---
        shelf_text = f"📍 {gd.shelf_location}" if gd.shelf_location else ""

        # --- expansion label ---
        expansion_label: str | None = None
        if gd.is_expansion:
            if gd.base_game_kr:
                expansion_label = f"확장판 · {gd.base_game_kr}"
            else:
                expansion_label = "확장판"

        # --- image path ---
        image_path = gd.image_local_path or gd.image_url

        # --- gauge percentages ---
        weight_gauge_pct = (
            min(100.0, max(0.0, gd.weight / 5.0 * 100.0))
            if gd.weight is not None
            else 0.0
        )
        rating_gauge_pct = (
            min(100.0, max(0.0, gd.rating / 10.0 * 100.0))
            if gd.rating is not None
            else 0.0
        )

        return cls(
            name_kr=gd.name_kr,
            name_en=gd.name_en,
            image_path=image_path,
            accent_color=None,  # Phase 2 hook
            rating_text=rating_text,
            rating_visible=rating_visible,
            players_text=players_text,
            best_players_text=best_players_text,
            time_text=time_text,
            age_text=age_text,
            weight_text=weight_text,
            categories_display=categories_display,
            mechanics_display_list=mechanics_display_list,
            designers_display=designers_display,
            shelf_text=shelf_text,
            expansion_label=expansion_label,
            bgg_id_text=bgg_id_text,
            weight_gauge_pct=weight_gauge_pct,
            rating_gauge_pct=rating_gauge_pct,
        )
