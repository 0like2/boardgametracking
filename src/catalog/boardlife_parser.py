"""Parse Boardlife game pages into GameData.

Used as a BGG-XML-API replacement when BGG blocks unauthenticated requests
(as of 2025-07-02, BGG requires registered Bearer tokens).

Fields mapped from Boardlife DOM:

    평점                 -> rating           (JSON-LD aggregateRating)
    #game-weight         -> weight
    #language            -> language_dependence (Korean text)
    #boardgame-title     -> name_kr
    .game-main-info h2.font-17 -> name_en
    #game-rate-year      -> year_published
    dl.bullet (인원/플레이 시간/사용 연령)
    .recommend-player    -> best_players ("베스트:5인" → "5")
    .credits-box 테마    -> categories  (Korean)
    .credits-box 진행방식-> mechanics   (Korean)
    .credit-row 디자이너 -> designers
    og:image             -> image_url
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from bs4 import BeautifulSoup

from src.catalog.models import GameData, GameInput


_YEAR_RE = re.compile(r"(\d{4})")
_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")
_PLAYERS_RE = re.compile(r"(\d+)\s*(?:-\s*(\d+))?\s*명")
_AGE_RE = re.compile(r"(\d+)\s*세")
_TIME_RE = re.compile(r"(\d+)\s*(?:-\s*(\d+))?\s*분")
_BEST_RE = re.compile(r"베스트\s*:?\s*(\d+)(?:\s*-\s*(\d+))?")


def _text(el: Any) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _find_credits_box(soup: BeautifulSoup, title_kr: str) -> list[str]:
    """Return list of <a class='title'> texts for a credits-box with the
    given 'title-info' label (e.g. '테마', '진행방식', '카테고리', '그룹').
    """
    values: list[str] = []
    for box in soup.select(".credits-box"):
        title_el = box.select_one(".title-info")
        if not title_el:
            continue
        label = title_el.get_text(strip=True).split()[0] if title_el.get_text(strip=True) else ""
        if label != title_kr:
            continue
        for a in box.select(".credits-row a.title"):
            txt = a.get_text(strip=True)
            if not txt or txt == "정보없음":
                continue
            # Filter "+N 더보기" pagination links
            if "더보기" in txt:
                continue
            values.append(txt)
        break
    return values


def _find_credit_row(soup: BeautifulSoup, label: str) -> list[str]:
    """Return the list of <a> texts (or raw text) from a .credit-row whose
    <dt class='credit-title'> matches `label` (e.g. '디자이너')."""
    for row in soup.select("dl.credit-row"):
        dt = row.find("dt")
        if not dt:
            continue
        if dt.get_text(strip=True) != label:
            continue
        dd = row.find("dd")
        if not dd:
            return []
        links = dd.find_all("a")
        if links:
            return [a.get_text(strip=True) for a in links if a.get_text(strip=True)]
        raw = dd.get_text(strip=True)
        return [raw] if raw else []
    return []


def _find_bullet(soup: BeautifulSoup, label: str) -> str:
    """Return the dd.data text for a dl.bullet whose dt matches `label`."""
    for dl in soup.select("dl.bullet"):
        dt = dl.find("dt")
        if dt and dt.get_text(strip=True) == label:
            dd = dl.find("dd")
            return _text(dd) if dd else ""
    return ""


def _extract_rating(soup: BeautifulSoup) -> float | None:
    """Try JSON-LD first, then fall back to the main-color span under 평점."""
    for script in soup.find_all("script", type="application/ld+json"):
        raw = (script.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Some pages include trailing commas or comments
            continue
        agg = data.get("aggregateRating") if isinstance(data, dict) else None
        if isinstance(agg, dict):
            val = agg.get("ratingValue")
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    # Fallback: walk the 평점 dl
    for dl in soup.select(".game-main-info dl.line"):
        dt = dl.find("dt")
        if dt and dt.get_text(strip=True) == "평점":
            span = dl.select_one("dd .main-color")
            if span:
                m = _NUM_RE.search(span.get_text())
                if m:
                    try:
                        return float(m.group(1))
                    except ValueError:
                        return None
    return None


def _extract_weight(soup: BeautifulSoup) -> float | None:
    el = soup.find(id="game-weight")
    if not el:
        return None
    m = _NUM_RE.search(el.get_text())
    if not m:
        return None
    try:
        v = float(m.group(1))
        return None if v == 0.0 else v
    except ValueError:
        return None


def _extract_players(soup: BeautifulSoup) -> tuple[int, int, str | None]:
    """Returns (min_players, max_players, best_players_str)."""
    raw = _find_bullet(soup, "인원")
    min_p, max_p = 1, 1
    m = _PLAYERS_RE.search(raw)
    if m:
        min_p = int(m.group(1))
        max_p = int(m.group(2)) if m.group(2) else min_p

    best_str: str | None = None
    rp = soup.select_one(".recommend-player")
    if rp:
        bm = _BEST_RE.search(rp.get_text(" ", strip=True))
        if bm:
            best_str = bm.group(1)
            if bm.group(2):
                best_str = f"{bm.group(1)}-{bm.group(2)}"
    return min_p, max_p, best_str


def _extract_time(soup: BeautifulSoup) -> tuple[int | None, int | None, int]:
    """Returns (min_playtime, max_playtime, playing_time)."""
    raw = _find_bullet(soup, "플레이 시간")
    m = _TIME_RE.search(raw)
    if not m:
        return None, None, 0
    mn = int(m.group(1))
    mx = int(m.group(2)) if m.group(2) else mn
    return mn, mx, mx


def _extract_age(soup: BeautifulSoup) -> int | None:
    raw = _find_bullet(soup, "사용 연령")
    m = _AGE_RE.search(raw)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def _extract_year(soup: BeautifulSoup) -> int | None:
    el = soup.find(id="game-rate-year")
    if not el:
        return None
    m = _YEAR_RE.search(el.get_text())
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def _extract_name_en(soup: BeautifulSoup) -> str:
    # English subtitle sits as an h2.font-17 inside .game-main-info, near #game-rate-year
    main = soup.select_one(".game-main-info")
    if not main:
        return ""
    for h2 in main.select("h2.font-17"):
        # Filter out section headers that contain Korean like '게임 평점 정보'
        txt = h2.get_text(strip=True)
        # Skip section headers (they contain Korean punctuation / words like 정보)
        if "정보" in txt:
            continue
        return txt
    return ""


def _extract_language_dependence(soup: BeautifulSoup) -> str | None:
    el = soup.find(id="language")
    if not el:
        return None
    txt = el.get_text(strip=True)
    return txt or None


def _extract_image_url(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        val = meta["content"]
        if "boardlife_m.png" in val or "thumbnail_no.jpg" in val:
            return ""
        return val
    return ""


def parse_boardlife_html(
    html_bytes: bytes,
    game_input: GameInput,
    image_local_path: str = "",
    base_game_kr: str | None = None,
) -> GameData:
    """Parse a Boardlife game detail page (HTML bytes) into a GameData.

    Falls back gracefully on missing fields: rating/weight/etc. may be None
    and categories/mechanics may be empty lists.
    """
    soup = BeautifulSoup(html_bytes, "html.parser")

    name_kr = game_input.name_kr
    if not name_kr:
        title_el = soup.find(id="boardgame-title")
        if title_el:
            name_kr = title_el.get_text(strip=True)
        if not name_kr:
            name_kr = "Unknown"

    name_en = _extract_name_en(soup) or name_kr

    year = _extract_year(soup)
    rating = _extract_rating(soup)
    weight = _extract_weight(soup)
    min_p, max_p, best_p = _extract_players(soup)
    min_t, max_t, playing_time = _extract_time(soup)
    age = _extract_age(soup)
    language_dep = _extract_language_dependence(soup)

    # Boardlife "테마" ≈ BGG boardgamecategory
    categories = _find_credits_box(soup, "테마")
    # Boardlife "진행방식" ≈ BGG boardgamemechanic
    mechanics = _find_credits_box(soup, "진행방식")
    designers = _find_credit_row(soup, "디자이너")
    # Boardlife "카테고리" is the high-level game type (1 entry expected)
    types = _find_credits_box(soup, "카테고리")
    game_type = types[0] if types else ""

    image_url = _extract_image_url(soup)

    is_expansion = bool(game_input.base_game_id)

    return GameData(
        bgg_id=game_input.bgg_id,
        name_kr=name_kr,
        name_en=name_en,
        year_published=year,
        image_url=image_url,
        thumbnail_url=image_url,
        image_local_path=image_local_path,
        min_players=min_p,
        max_players=max_p,
        best_players=best_p,
        min_playing_time=min_t,
        max_playing_time=max_t,
        playing_time=playing_time,
        min_age=age,
        weight=weight,
        rating=rating,
        categories=categories,
        mechanics=mechanics,
        designers=designers,
        is_expansion=is_expansion,
        base_game_id=game_input.base_game_id,
        base_game_kr=base_game_kr,
        language_dependence=language_dep,
        shelf_location=game_input.shelf_location,
        accent_kind=game_input.accent_kind,
        game_type=game_type,
    )


def normalize_boardlife_url(url: str) -> str:
    """Convert collection-style URLs (?game=123) into canonical /game/123."""
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "game" in qs:
        return f"https://boardlife.co.kr/game/{qs['game'][0]}"
    return url


def extract_boardlife_id(url: str) -> str | None:
    """Extract the Boardlife game id from any supported URL form.

    Accepts:
        https://boardlife.co.kr/game/17173           -> "17173"
        https://boardlife.co.kr/game/17173/something -> "17173"
        https://boardlife.co.kr/xxx?game=17173       -> "17173"
    Returns None if no id can be found.
    """
    import urllib.parse

    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "game" in qs and qs["game"]:
        return qs["game"][0]
    # path like /game/17173 or /game/17173/credits
    parts = [p for p in parsed.path.split("/") if p]
    for i, p in enumerate(parts):
        if p == "game" and i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate.isdigit():
                return candidate
    return None


def _smoke_test(path: str, bgg_id: int = 0) -> None:  # pragma: no cover
    """Quick manual test: python -m src.catalog.boardlife_parser <html>"""
    from src.catalog.models import GameInput

    gi = GameInput(bgg_id=bgg_id, name_kr="", shelf_location="")
    with open(path, "rb") as f:
        gd = parse_boardlife_html(f.read(), gi)
    print(gd)


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) > 1:
        _smoke_test(sys.argv[1])
