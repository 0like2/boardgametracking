"""Renderer: converts list[GameData] + Translator into a full HTML string."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.catalog.models import GameData
from src.catalog.translator import Translator
from src.catalog.view_model import CardViewModel

_ASSETS_DIR = Path(__file__).parent / "assets"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


class Renderer:
    """Renders a list of GameData objects into a multi-page catalog HTML string."""

    def __init__(
        self,
        templates_dir: Path | None = None,
        assets_dir: Path | None = None,
        cards_per_page: int = 9,
    ) -> None:
        self._templates_dir = templates_dir or _TEMPLATES_DIR
        self._assets_dir = assets_dir or _ASSETS_DIR
        self.cards_per_page = cards_per_page
        self.env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def render(self, games: list[GameData], translator: Translator) -> str:
        """Convert games to CardViewModels, paginate, and render catalog.html.

        Returns a complete HTML document string ready for PDF export.
        """
        vms = [CardViewModel.from_game_data(g, translator) for g in games]
        pages = [
            vms[i : i + self.cards_per_page]
            for i in range(0, len(vms), self.cards_per_page)
        ]

        # Compute CSS/icon paths relative to the assets dir
        styles_path = str(self._assets_dir / "styles.css")
        icons_path = str(self._assets_dir / "icons")

        template = self.env.get_template("catalog.html")
        return template.render(
            pages=pages,
            styles_path=styles_path,
            icons_path=icons_path,
        )
