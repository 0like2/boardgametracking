"""Build web/data/games.b.json — the second owner's collection.

Boardlife rebuilt its game page in 2026-06, so the July cache and the pages we
fetch today use different markup. `src/catalog/boardlife_parser` still matches
the old cache (which the first collection depends on), so the new layout gets
its own reader here rather than a rewrite that would break the other 122 games.

Fully offline once cache/boardlife/*.html and the 자료실 pages are warm.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from export_web_data import classify_material, shorten, slugify

ROOT = Path(__file__).parent
LIST = ROOT / "inputs/collection_b.tsv"
IDS = ROOT / "inputs/collection_b_ids.json"
CACHE = ROOT / "cache/boardlife"
COVERS = ROOT / "web/public/covers"
OUT = ROOT / "web/data/games.b.json"
MAIN = ROOT / "web/data/games.json"

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
_BL = "https://boardlife.co.kr"
_NUM = re.compile(r"(\d+(?:\.\d+)?)")
_RANGE = re.compile(r"(\d+)\s*(?:~|-|–)\s*(\d+)")


def fetch(url: str, path: Path) -> bytes:
    """Cached GET. Boardlife is a hobby site — one request per second."""
    if path.exists():
        return path.read_bytes()
    resp = requests.get(url, headers=UA, timeout=20)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    time.sleep(1.0)
    return resp.content


# --- new-layout field readers -------------------------------------------


def vote_value(soup: BeautifulSoup, label: str) -> str:
    """Community-vote tiles (카테고리 · 난이도 · 베스트/추천 · 언어 의존도).
    Reads '-' when nobody has voted, which is a real answer, not a miss."""
    for item in soup.select(".gvs-item"):
        lab = item.select_one(".gvs-label")
        val = item.select_one(".gvs-value")
        if lab and val and lab.get_text(strip=True) == label:
            return val.get_text(" ", strip=True)
    return ""


def info_value(soup: BeautifulSoup, label: str) -> str:
    """Publisher-stated 인원 / 시간 / 연령 row."""
    for dl in soup.select(".game-info-item"):
        dt = dl.select_one(".game-info-label")
        dd = dl.select_one(".game-info-value")
        if dt and dd and dt.get_text(strip=True) == label:
            return dd.get_text(" ", strip=True)
    return ""


def num(text: str) -> float | None:
    m = _NUM.search(text or "")
    return float(m.group(1)) if m else None


def span(text: str) -> tuple[int | None, int | None]:
    """'2-4명' -> (2, 4); '30분' -> (30, 30); '' -> (None, None)."""
    if not text:
        return None, None
    m = _RANGE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    v = num(text)
    return (int(v), int(v)) if v is not None else (None, None)


def counts(text: str) -> list[int]:
    """'2인' -> [2]; '3~4인' -> [3, 4]; '-' -> []."""
    lo, hi = span(text)
    return list(range(lo, hi + 1)) if lo is not None else []


def credits(soup: BeautifulSoup, label: str) -> list[str]:
    for dl in soup.select(".game-credit-row"):
        dt = dl.find("dt")
        if dt and dt.get_text(strip=True) == label:
            return [a.get_text(strip=True) for a in dl.select("dd a")] or [
                p.strip()
                for p in (dl.find("dd").get_text(",", strip=True) if dl.find("dd") else "").split(",")
                if p.strip()
            ]
    return []


def rating_of(soup: BeautifulSoup) -> float | None:
    """JSON-LD carries the same 평점 the header shows, already parsed."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads((script.string or "").strip())
        except (json.JSONDecodeError, AttributeError):
            continue
        agg = data.get("aggregateRating") if isinstance(data, dict) else None
        if isinstance(agg, dict):
            try:
                return float(agg["ratingValue"])
            except (KeyError, TypeError, ValueError):
                pass
    return None


def rank_of(soup: BeautifulSoup) -> int | None:
    for label in soup.select(".game-rank-label"):
        if label.get_text(strip=True) == "전체":
            m = _NUM.search(label.parent.get_text(" ", strip=True).replace(",", ""))
            if m:
                return int(float(m.group(1)))
    return None


def bgg_id_of(soup: BeautifulSoup) -> int | None:
    for a in soup.select("a.game-link-item"):
        m = re.search(r"boardgame/(\d+)", a.get("href") or "")
        if m:
            return int(m.group(1))
    return None


def files_of(bl_id: str) -> list[dict]:
    """자료실 index. The game page only teases the top row, so read the board."""
    html = fetch(f"{_BL}/game/{bl_id}/board/info/info_files",
                 CACHE / f"bl_{bl_id}_files.html")
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.select('a[href*="tb=info_files"]'):
        href = a.get("href") or ""
        title_el = a.select_one(".post-title-txt")
        if not title_el or href in seen:
            continue
        seen.add(href)
        cat_el = a.select_one(".post-cat")
        category = cat_el.get_text(strip=True) if cat_el else ""
        title = title_el.get_text(" ", strip=True)
        out.append({
            "kind": classify_material(category, title),
            "category": category,
            "label": title,
            "url": _BL + href if href.startswith("/") else href,
        })
    return out


def cover(bl_id: str, image_url: str) -> None:
    """Covers are served from /covers/<boardlife id>.jpg, shared by both sites."""
    path = COVERS / f"{bl_id}.jpg"
    if path.exists() or not image_url:
        return
    resp = requests.get(image_url, headers=UA, timeout=30)
    if resp.ok:
        path.write_bytes(resp.content)
        time.sleep(0.3)


def text_of(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


# --- build ---------------------------------------------------------------


def main() -> int:
    ids = {r["no"]: r for r in json.loads(IDS.read_text())}
    # 21 of these titles are also in the first collection, so their cached page
    # is July's markup. Re-fetching would replace a cache the other exporter
    # still needs, so reuse what that run already parsed off the same page.
    already = {g["id"]: g for g in json.loads(MAIN.read_text())}
    rows = list(csv.reader(LIST.open(encoding="utf-8"), delimiter="\t"))
    COVERS.mkdir(parents=True, exist_ok=True)

    games: list[dict] = []
    for row in rows:
        entry = ids.get(row[0])
        if not entry or not entry["id"]:
            continue
        bl_id = str(entry["id"])
        # The owner's own numbers, used only where Boardlife has no votes yet.
        own_players = row[2] if len(row) > 2 else ""
        own_weight = num(row[3]) if len(row) > 3 else None
        own_rating = num(row[4]) if len(row) > 4 else None
        own_time = row[5] if len(row) > 5 else ""

        html = fetch(f"{_BL}/game/{bl_id}", CACHE / f"bl_{bl_id}.html")
        soup = BeautifulSoup(html, "html.parser")

        if not soup.select(".gvs-item"):  # pre-rebuild page
            done = dict(already[bl_id])
            done.pop("cardImage", None)
            done["batch"] = ""
            games.append(done)
            continue

        name_kr = text_of(soup, "#boardgame-title") or entry["name"]
        name_en = text_of(soup, ".game-title-en")
        description = text_of(soup, ".game-description")
        short = text_of(soup, ".game-short-title")

        min_p, max_p = span(info_value(soup, "인원") or own_players)
        min_t, max_t = span(info_value(soup, "시간") or own_time)
        best_raw, _, rec_raw = vote_value(soup, "베스트 / 추천").partition("/")

        og = soup.find("meta", property="og:image")
        image_url = og["content"] if og and og.get("content") else ""
        cover(bl_id, image_url)

        category = vote_value(soup, "카테고리").strip("-").strip()
        lang = vote_value(soup, "언어 의존도").strip()
        year = num(text_of(soup, "#game-rate-year"))

        games.append({
            "id": bl_id,
            "slug": slugify(name_en, name_kr, bl_id),
            "bggId": bgg_id_of(soup),
            "nameKr": name_kr,
            "nameEn": name_en,
            "summary": shorten(short or description),
            "description": description,
            "year": int(year) if year else None,
            "batch": "",
            "minPlayers": min_p or 1,
            "maxPlayers": max_p or min_p or 1,
            "bestPlayers": counts(best_raw),
            "recPlayers": counts(rec_raw),
            "rank": rank_of(soup),
            "minTime": min_t,
            "maxTime": max_t,
            "minAge": int(num(info_value(soup, "연령")) or 0) or None,
            "weight": num(vote_value(soup, "난이도")) or own_weight,
            "rating": rating_of(soup) or own_rating,
            "gameType": category,
            "categories": [category] if category else [],
            "mechanics": [],  # the rebuilt page no longer lists them
            "designers": credits(soup, "디자이너"),
            "languageDependence": lang if lang and lang != "-" else None,
            "imageUrl": image_url,
            "baseGame": None,
            "boardlifeFiles": files_of(bl_id),
            "boardlifeUrl": f"{_BL}/game/{bl_id}",
        })

    OUT.write_text(json.dumps(games, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(games)} games -> {OUT}")
    for field in ("weight", "rating", "summary", "bestPlayers", "boardlifeFiles"):
        n = sum(1 for g in games if g[field])
        print(f"  {field:<16} {n}/{len(games)}")
    missing = [g["nameKr"] for g in games if not g["summary"]]
    if missing:
        print(f"  !! 설명 없음 ({len(missing)}): {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
