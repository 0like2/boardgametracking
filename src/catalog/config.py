"""Pydantic config schema + YAML loader for the catalog pipeline."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class CardDimensions(BaseModel):
    width_mm: float = 63.0
    height_mm: float = 88.0
    bleed_mm: float = 2.0
    safe_zone_mm: float = 3.0


class PageLayout(BaseModel):
    margin_mm: float = 15.0
    gutter_mm: float = 8.0


class BggConfig(BaseModel):
    user_agent: str = "BoardGameClubCatalog/1.0"
    cache_ttl_days: int = 30
    request_interval_sec: float = 1.5
    batch_size: int = 20


class CatalogConfig(BaseModel):
    card: CardDimensions = CardDimensions()
    page: PageLayout = PageLayout()
    bgg: BggConfig = BggConfig()


def load_config(path: Path = Path("config.yaml")) -> CatalogConfig:
    """Load config.yaml and return a CatalogConfig, falling back to defaults
    if the file does not exist or is empty."""
    if not path.exists():
        return CatalogConfig()
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    # Only pick catalog-relevant keys to avoid clashing with the existing
    # boardlife config in the same file.
    catalog_data = data.get("catalog", data)
    return CatalogConfig.model_validate(catalog_data)
