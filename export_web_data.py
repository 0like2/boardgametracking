"""Parse the cached Boardlife pages into a single games.json for the web app.

Runs fully offline against cache/boardlife/*.html, so it is safe to re-run.
Output shape is the contract consumed by the Next.js app (web/src/lib/games.ts).
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

from src.catalog.boardlife_parser import extract_boardlife_id, parse_boardlife_html
from src.catalog.models import GameInput
from src.catalog.translator import Translator

ROOT = Path(__file__).parent
MASTER = ROOT / "output/2026-07-05/게임목록_3월_5월_7월.xlsx"
CACHE = ROOT / "cache/boardlife"
CARDS = ROOT / "output/2026-07-05/images/cards"
OUT = ROOT / "web/data/games.json"


def extract_description(html: bytes) -> str:
    """Boardlife keeps the Korean blurb in `.content.description`."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for el in soup.select(".content.description"):
        text = el.get_text(" ", strip=True)
        # The "+ 더보기" toggle lives in a sibling; strip it if it leaked in.
        text = re.sub(r"\+?\s*더보기\s*$", "", text).strip()
        if text:
            return text
    return ""


_REC_RE = re.compile(r"추천\s*:?\s*(\d+)(?:\s*-\s*(\d+))?")
_RANK_RE = re.compile(r"종합\s*([\d,]+)\s*위")


def extract_recommended(html: bytes) -> list[int]:
    """`.recommend-player` carries both 베스트 and 추천; the parser only keeps
    베스트, so pull 추천 (playable-but-not-optimal counts) separately."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(".recommend-player")
    if not el:
        return []
    m = _REC_RE.search(el.get_text(" ", strip=True))
    if not m:
        return []
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    return list(range(lo, hi + 1))


def extract_rank(html: bytes) -> int | None:
    """Boardlife's overall rank, stated in the page's meta description."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta:
        return None
    m = _RANK_RE.search(meta.get("content") or "")
    return int(m.group(1).replace(",", "")) if m else None


_BL = "https://boardlife.co.kr"

# Title keywords win over the Boardlife category, because 점수판/개인매트 are
# filed under generic categories but are exactly what people look for.
_KIND_BY_KEYWORD: list[tuple[str, tuple[str, ...]]] = [
    ("점수판", ("점수판", "점수표", "스코어", "득점판", "계산기")),
    ("개인판", ("개인매트", "개인 매트", "개인판", "개인 보드", "플레이어 보드", "플레이 매트", "플레이매트")),
    ("참조표", ("참조표", "참조 표", "리마인더", "도움표", "치트", "cheat")),
    ("요약표", ("요약", "한장", "one sheet", "onesheet", "정리")),
]

_KIND_BY_CATEGORY = {
    "참조표": "참조표",
    "요약룰": "요약표",
    "한국어룰북": "룰북",
    "한글화자료": "한글화",
}


def classify_material(category: str, title: str) -> str:
    low = title.lower()
    for kind, keywords in _KIND_BY_KEYWORD:
        if any(k.lower() in low for k in keywords):
            return kind
    return _KIND_BY_CATEGORY.get(category, "기타")


def extract_boardlife_files(html: bytes) -> list[dict]:
    """The 자료실 index is embedded in every cached game page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()

    for a in soup.select('a[href*="tb=info_files"]'):
        href = a.get("href") or ""
        if href in seen:
            continue
        seen.add(href)

        cat_el = a.select_one(".category")
        title_el = a.select_one(".title")
        if not title_el:
            continue

        category = cat_el.get_text(strip=True) if cat_el else ""
        title = title_el.get_text(" ", strip=True)
        if not title:
            continue

        out.append(
            {
                "kind": classify_material(category, title),
                "category": category,
                "label": title,
                "url": _BL + href if href.startswith("/") else href,
            }
        )
    return out


def shorten(text: str, limit: int = 95) -> str:
    """One-line teaser for the card overlay, cut on a sentence when possible."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text

    head = text[:limit]
    cut = max(head.rfind("."), head.rfind("!"), head.rfind("?"))
    if cut >= limit * 0.5:
        return head[: cut + 1]
    return head.rstrip() + "…"


def slugify(name_en: str, name_kr: str, bl_id: str) -> str:
    """URL slug: ASCII from the English name, falling back to the Boardlife id."""
    base = unicodedata.normalize("NFKD", name_en or "")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base or f"game-{bl_id}"


def card_index(name_kr: str, cards: dict[str, Path]) -> str | None:
    """Card PNGs are named `NNN_한글_이름.png` (spaces → underscores)."""
    key = name_kr.replace(" ", "_").replace("/", "_")
    return cards.get(key)


def main() -> int:
    df = pd.read_excel(MASTER, dtype=str)
    translator = Translator()

    # Map "한글_이름" -> filename for the pre-rendered card PNGs
    cards: dict[str, str] = {}
    for p in sorted(CARDS.glob("*.png")):
        stem = p.stem.split("_", 1)[1] if "_" in p.stem else p.stem
        cards[stem] = p.name

    games: list[dict] = []
    missing_cache: list[str] = []
    missing_card: list[str] = []

    for _, row in df.iterrows():
        name_kr = str(row["한글명"]).strip()
        url = str(row.get("boardlife_url", "")).strip()
        bl_id = extract_boardlife_id(url)
        if not bl_id:
            missing_cache.append(f"{name_kr} (no boardlife url)")
            continue

        html_path = CACHE / f"bl_{bl_id}.html"
        if not html_path.exists():
            missing_cache.append(f"{name_kr} (bl_{bl_id}.html)")
            continue

        raw_bgg = str(row.get("BGG_ID", "")).strip()
        try:
            bgg_id = int(float(raw_bgg))
        except (TypeError, ValueError):
            bgg_id = 0

        raw_html = html_path.read_bytes()
        gi = GameInput(bgg_id=bgg_id, name_kr=name_kr, shelf_location="")
        gd = parse_boardlife_html(raw_html, gi)
        description = extract_description(raw_html)

        card = card_index(name_kr, cards)
        if not card:
            missing_card.append(name_kr)

        # best_players "5" or "3-5" -> explicit list of ints
        best: list[int] = []
        if gd.best_players:
            parts = [int(x) for x in re.findall(r"\d+", gd.best_players)]
            if len(parts) == 2:
                best = list(range(parts[0], parts[1] + 1))
            elif parts:
                best = parts

        games.append(
            {
                "id": bl_id,
                "slug": slugify(gd.name_en, name_kr, bl_id),
                "bggId": bgg_id or None,
                "nameKr": name_kr,
                "nameEn": gd.name_en,
                "summary": shorten(description),
                "description": description,
                "year": gd.year_published,
                "batch": str(row.get("구분", "")).strip(),
                "minPlayers": gd.min_players,
                "maxPlayers": gd.max_players,
                "bestPlayers": best,
                "recPlayers": extract_recommended(raw_html),
                "rank": extract_rank(raw_html),
                "minTime": gd.min_playing_time,
                "maxTime": gd.max_playing_time,
                "minAge": gd.min_age,
                "weight": gd.weight,
                "rating": gd.rating,
                "gameType": gd.game_type,
                "categories": [translator.translate(c) for c in gd.categories],
                "mechanics": [translator.translate(m) for m in gd.mechanics],
                "designers": gd.designers,
                "languageDependence": gd.language_dependence,
                "imageUrl": gd.image_url,
                "cardImage": card,
                "baseGame": None,
                "boardlifeFiles": extract_boardlife_files(raw_html),
                "boardlifeUrl": f"https://boardlife.co.kr/game/{bl_id}",
            }
        )

    # Boardlife has no blurb for most expansions. Naming the base game is more
    # useful than an empty overlay — and it is something we can state for sure.
    by_name = {g["nameKr"]: g for g in games}
    for g in games:
        if g["summary"]:
            continue
        for sep in (":", " - ", "–"):
            if sep not in g["nameKr"]:
                continue
            base_name = g["nameKr"].split(sep)[0].strip()
            base = by_name.get(base_name)
            if not base or base is g:
                continue
            g["baseGame"] = base_name
            g["summary"] = (
                f"「{base_name}」의 확장. {shorten(base['description'], 60)}"
                if base["description"]
                else f"「{base_name}」의 확장입니다."
            )
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(games, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote {len(games)} games -> {OUT}")
    with_best = sum(1 for g in games if g["bestPlayers"])
    with_weight = sum(1 for g in games if g["weight"])
    with_desc = sum(1 for g in games if g["summary"])
    print(f"  best players: {with_best}/{len(games)}")
    print(f"  weight:       {with_weight}/{len(games)}")
    print(f"  summary:      {with_desc}/{len(games)}")
    if missing_cache:
        print(f"  !! no cache ({len(missing_cache)}): {missing_cache[:10]}")
    if missing_card:
        print(f"  !! no card ({len(missing_card)}): {missing_card[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
