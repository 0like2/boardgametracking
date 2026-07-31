"""Render Instagram feed posts (1080×1350) from a short YAML spec.

You write the parts only you know — which game, the photo, who won, what you
thought. Everything else (English name, cover art, 난이도, 평점, 인원, 시간,
소개글) is filled in from web/data/games.json.

    python make_insta.py posts/2026-07.yaml

Spec format — see posts/example.yaml. Three post types:

    review  후기: 플레이 사진 + 등수표 + 후기 + 스탯
    intro   소개: 커버 + 소개글 + 태그 + 스탯
    rules   간단 규칙: 스텝 3~5개 + 승리 조건
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
GAMES_JSON = ROOT / "web/data/games.json"
COVERS = ROOT / "web/public/covers"
TEMPLATES = ROOT / "src/insta/templates"
FONTS_SRC = ROOT / "src/catalog/assets/fonts"
OUT_DIR = ROOT / "output/instagram"

CANVAS_W, CANVAS_H = 1080, 1350
DEVICE_SCALE = 2  # 2160×2700 — well above Instagram's 1080px downscale target

BRAND = "보드게임 컬렉션"
HANDLE = "@boardgame"


def load_games() -> dict[str, dict]:
    games = json.loads(GAMES_JSON.read_text(encoding="utf-8"))
    return {g["nameKr"]: g for g in games}


def find_game(games: dict[str, dict], name: str) -> dict:
    if name in games:
        return games[name]
    # Forgiving match: ignore spaces and punctuation so "브라스 버밍엄" finds
    # "브라스: 버밍엄".
    def norm(s: str) -> str:
        return re.sub(r"[\s:·\-–—!?,.]", "", s)

    target = norm(name)
    hits = [g for k, g in games.items() if norm(k) == target]
    if not hits:
        hits = [g for k, g in games.items() if target in norm(k)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit(f"게임을 찾을 수 없습니다: {name!r}")
    names = ", ".join(h["nameKr"] for h in hits[:5])
    raise SystemExit(f"게임 이름이 모호합니다: {name!r} → {names}")


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def players_text(game: dict) -> str:
    lo, hi = game["minPlayers"], game["maxPlayers"]
    return f"{lo}인" if lo == hi else f"{lo}~{hi}인"


def joined(nums: list[int]) -> str:
    if not nums:
        return ""
    contiguous = all(n == nums[i - 1] + 1 for i, n in enumerate(nums) if i)
    return f"{nums[0]}~{nums[-1]}인" if contiguous and len(nums) > 1 else "·".join(map(str, nums)) + "인"


def time_text(game: dict) -> str:
    lo, hi = game.get("minTime"), game.get("maxTime")
    if lo is None and hi is None:
        return "—"
    if lo is not None and hi is not None and lo != hi:
        return f"{lo}~{hi}분"
    return f"{hi or lo}분"


def common_context(game: dict) -> dict:
    return {
        "game": game,
        "brand": BRAND,
        "handle": HANDLE,
        "players_text": players_text(game),
        "best_text": (
            f"베스트 {joined(game['bestPlayers'])}" if game["bestPlayers"] else "—"
        ),
        "time_text": time_text(game),
        "age_text": f"{game['minAge']}세 이상" if game.get("minAge") else "—",
        "weight_text": f"{game['weight']:.1f}" if game.get("weight") else "—",
        "rating_text": f"{game['rating']:.1f}" if game.get("rating") else "—",
        "cover_url": file_url(COVERS / f"{game['id']}.jpg"),
    }


def build_review(post: dict, game: dict) -> dict:
    ranking = post.get("ranking") or []
    for p in ranking:
        p.setdefault("note", "")
        p.setdefault("score", "")

    photo = post.get("photo")
    if photo:
        photo_path = (ROOT / photo) if not Path(photo).is_absolute() else Path(photo)
        if not photo_path.exists():
            raise SystemExit(f"사진을 찾을 수 없습니다: {photo_path}")
        photo_url = file_url(photo_path)
    else:
        # No photo yet — fall back to the cover so the post still renders.
        photo_url = file_url(COVERS / f"{game['id']}.jpg")

    # A tall scoreboard leaves less room for prose.
    review_lines = 4 if len(ranking) <= 4 else 3

    duration = post.get("duration")
    date = str(post.get("date", "")).strip()

    return {
        **common_context(game),
        "photo_url": photo_url,
        "review_lines": review_lines,
        "ranking": ranking,
        "review": (post.get("review") or "").strip(),
        "date_label": date.replace("-", ".") if date else "",
        "duration_text": f"{duration}분" if duration else time_text(game),
    }


def build_intro(post: dict, game: dict) -> dict:
    intro = (post.get("intro") or game.get("description") or "").strip()
    tags = post.get("tags")
    if tags is None:
        tags = (game.get("categories") or [])[:3] + (game.get("mechanics") or [])[:3]

    return {
        **common_context(game),
        "kicker": post.get("kicker") or " · ".join((game.get("categories") or [])[:2]),
        "intro": intro,
        "intro_lines": post.get("intro_lines", 6),
        "tags": tags,
    }


def build_rules(post: dict, game: dict) -> dict:
    steps = post.get("steps") or []
    if not steps:
        raise SystemExit(f"{game['nameKr']}: rules 포스트에는 steps가 필요합니다.")
    if len(steps) > 5:
        print(f"  ! steps가 {len(steps)}개입니다. 5개까지만 들어갑니다.", file=sys.stderr)
        steps = steps[:5]

    normalised = []
    for s in steps:
        if isinstance(s, str):
            normalised.append({"title": s, "desc": ""})
        else:
            normalised.append({"title": s.get("title", ""), "desc": s.get("desc", "")})

    return {**common_context(game), "steps": normalised, "win": post.get("win", "")}


BUILDERS = {"review": build_review, "intro": build_intro, "rules": build_rules}


def slugify(name: str) -> str:
    base = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "post"


async def render_all(jobs: list[tuple[str, dict, Path]]) -> None:
    from playwright.async_api import async_playwright

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )

    # Playwright reads the CSS and fonts relative to the HTML file, so render
    # into the template dir and clean up afterwards.
    fonts_dir = TEMPLATES / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    for f in FONTS_SRC.glob("*.woff2"):
        shutil.copy2(f, fonts_dir / f.name)

    tmp_files: list[Path] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(
            viewport={"width": CANVAS_W, "height": CANVAS_H},
            device_scale_factor=DEVICE_SCALE,
        )

        for i, (kind, context, dest) in enumerate(jobs, 1):
            html = env.get_template(f"{kind}.html").render(**context)
            tmp = TEMPLATES / f".render_{i}.html"
            tmp.write_text(html, encoding="utf-8")
            tmp_files.append(tmp)

            await page.goto(tmp.as_uri())
            await page.wait_for_timeout(320)  # let webfonts settle

            overflow = await page.evaluate(
                "() => { const p = document.querySelector('.post');"
                " return p.scrollHeight - p.clientHeight; }"
            )
            if overflow > 2:
                print(f"  ! {dest.name}: 내용이 {overflow}px 넘칩니다", file=sys.stderr)

            dest.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(dest))
            print(f"  [{i}/{len(jobs)}] {dest.name}")

        await browser.close()

    for t in tmp_files:
        t.unlink(missing_ok=True)
    shutil.rmtree(fonts_dir, ignore_errors=True)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    spec_path = Path(sys.argv[1])
    if not spec_path.exists():
        raise SystemExit(f"스펙 파일이 없습니다: {spec_path}")

    posts = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or []
    if isinstance(posts, dict):
        posts = [posts]

    games = load_games()
    out_dir = OUT_DIR / spec_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[str, dict, Path]] = []
    for i, post in enumerate(posts, 1):
        kind = post.get("type", "review")
        if kind not in BUILDERS:
            raise SystemExit(f"알 수 없는 type: {kind!r} (review/intro/rules)")
        game = find_game(games, post["game"])
        context = BUILDERS[kind](post, game)
        name = f"{i:02d}_{kind}_{slugify(game['nameEn'] or game['nameKr'])}.png"
        jobs.append((kind, context, out_dir / name))

    print(f"{len(jobs)}개 포스트 → {out_dir}")
    asyncio.run(render_all(jobs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
