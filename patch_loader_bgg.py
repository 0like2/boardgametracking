from src.catalog.loader import load_games
from pathlib import Path
try:
    load_games(Path("inputs/games.xlsx"))
except Exception as e:
    print("Error:", e)
