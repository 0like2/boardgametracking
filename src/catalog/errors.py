"""Catalog-specific exception hierarchy."""

from __future__ import annotations


class CatalogError(Exception):
    """Base exception for all catalog errors."""


class GameSkipError(CatalogError):
    """Raised when a game must be skipped (non-recoverable fetch failure)."""

    def __init__(self, bgg_id: int, reason: str) -> None:
        self.bgg_id = bgg_id
        self.reason = reason
        super().__init__(f"Skipping game {bgg_id}: {reason}")


class FieldMissingError(CatalogError):
    """Raised when a required field is absent in the BGG response."""

    def __init__(self, bgg_id: int, field: str) -> None:
        self.bgg_id = bgg_id
        self.field = field
        super().__init__(f"Required field '{field}' missing for game {bgg_id}")


class BggApiError(CatalogError):
    """Raised on unrecoverable BGG API errors (e.g. HTTP 200 + <errors> payload)."""

    def __init__(self, bgg_id: int, message: str) -> None:
        self.bgg_id = bgg_id
        super().__init__(f"BGG API error for game {bgg_id}: {message}")


class InvalidInputError(CatalogError):
    """Raised when the user's input file contains invalid data."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
