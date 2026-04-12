#!/usr/bin/env python3
"""End-to-end entry point that wraps src.catalog.__main__.

Usage (from project root):
    python scripts/build_catalog.py inputs/games.xlsx --out output/catalog.pdf
    python scripts/build_catalog.py inputs/games.xlsx --renderer weasyprint
    python scripts/build_catalog.py inputs/games.xlsx --offline-fixtures tests/catalog/fixtures
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked directly
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.catalog.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
