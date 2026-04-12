"""Load inputs/games.xlsx or games.csv into a list of GameInput."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.catalog.errors import InvalidInputError
from src.catalog.models import GameInput

_REQUIRED_COLUMNS = {"bgg_id", "name_kr", "shelf_location"}


def load_games(path: Path) -> list[GameInput]:
    """Read an Excel or CSV file and return validated GameInput objects.

    Raises InvalidInputError on structural problems (missing columns, invalid
    bgg_id types).  Individual rows with empty name_kr emit a stderr warning
    and are included with the BGG primary name as a placeholder (empty string
    kept — the caller / renderer handles the fallback).
    """
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise InvalidInputError(f"Unsupported file format: {suffix}")

    # Normalise column names: strip whitespace, lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise InvalidInputError(
            f"Input file is missing required columns: {sorted(missing)}"
        )

    games: list[GameInput] = []
    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-based, header is row 1

        # --- bgg_id ---
        raw_id = str(row["bgg_id"]).strip().replace("/", "")
        if not raw_id or raw_id.lower() == "nan":
            # Assign fake BGG ID for local/indie games
            bgg_id = -row_num
        else:
            try:
                bgg_id = int(float(raw_id))
            except ValueError:
                raise InvalidInputError(
                    f"Row {row_num}: bgg_id '{raw_id}' is not a valid integer."
                )

        # --- name_kr ---
        name_kr = str(row.get("name_kr", "")).strip()
        if not name_kr or name_kr.lower() == "nan":
            print(
                f"Warning: Row {row_num} (bgg_id={bgg_id}) has empty name_kr.",
                file=sys.stderr,
            )
            name_kr = ""

        # --- shelf_location ---
        shelf_location = str(row.get("shelf_location", "")).strip()
        if shelf_location.lower() == "nan":
            shelf_location = ""

        # --- optional fields ---
        boardlife_url: str | None = None
        raw_bl_url = str(row.get("boardlife_url", "")).strip()
        if raw_bl_url and raw_bl_url.lower() != "nan":
            boardlife_url = raw_bl_url

        base_game_id: int | None = None
        raw_base = str(row.get("base_game_id", "")).strip()
        if raw_base and raw_base.lower() not in {"nan", ""}:
            try:
                base_game_id = int(float(raw_base))
            except ValueError:
                print(
                    f"Warning: Row {row_num}: base_game_id '{raw_base}' is not valid; ignoring.",
                    file=sys.stderr,
                )

        accent_kind: str | None = None
        raw_accent = str(row.get("accent_kind", "")).strip()
        if raw_accent and raw_accent.lower() not in {"nan", ""}:
            if raw_accent in {"new", "expansion"}:
                accent_kind = raw_accent
            else:
                print(
                    f"Warning: Row {row_num}: accent_kind '{raw_accent}' is not 'new' or 'expansion'; ignoring.",
                    file=sys.stderr,
                )

        notes: str | None = None
        raw_notes = str(row.get("notes", "")).strip()
        if raw_notes and raw_notes.lower() != "nan":
            notes = raw_notes

        games.append(
            GameInput(
                bgg_id=bgg_id,
                name_kr=name_kr,
                shelf_location=shelf_location,
                boardlife_url=boardlife_url,
                base_game_id=base_game_id,
                accent_kind=accent_kind,
                notes=notes,
            )
        )

    return games
