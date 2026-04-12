#!/usr/bin/env python3
"""
Phase 0 spike — render page.html → output/phase0_playwright.pdf using Playwright/Chromium.
4 cards (varied sample data) in a 2×2 A4 grid.
Run: python scripts/phase0_render_playwright.py
"""
import io
import sys
import shutil
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
ICONS_DIR  = ROOT / "src/catalog/assets/icons"
FONTS_DIR  = ROOT / "src/catalog/assets/fonts"
CACHE_IMG  = ROOT / "cache/images"
OUTPUT_PDF = ROOT / "output/phase0_playwright.pdf"
OUTPUT_HTML= ROOT / "output/phase0_page.html"

OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
CACHE_IMG.mkdir(parents=True, exist_ok=True)

# ── Sample data (4 cards for 2×2 grid) ───────────────────────────────────────
SAMPLES = [
    {
        "name_kr": "브라스: 버밍엄",
        "name_en": "Brass: Birmingham",
        "year": 2018,
        "bgg_id": "224517",
        "image_url": "https://cf.geekdo-images.com/x3zxjr-Vw5iU4yDPg70Jgw__original/img/FpyxH41Y6_ROoePAilPNEhXnzO8=/0x0/filters:format(jpeg)/pic3490053.jpg",
        "min_p": 2, "max_p": 4, "best": "3-4",
        "time": "60-120'", "age": "14+",
        "weight": 3.91, "rating": 8.6,
        "categories_kr": "경제 · 산업혁명",
        "designer": "Gavin Birnbaum",
        "shelf": "A-3-12",
        "expansion_label": None,
    },
    {
        "name_kr": "글룸헤이븐",
        "name_en": "Gloomhaven",
        "year": 2017,
        "bgg_id": "174430",
        "image_url": "https://cf.geekdo-images.com/sZYp_3BTDGjh2unaZfZmuA__imagepagezoom/img/5I8JKGk4sJDkUXTNjPgFjvIXlYU=/fit-in/1024x1024/filters:no_upscale():strip_icc()/pic2437871.jpg",
        "min_p": 1, "max_p": 4, "best": "2",
        "time": "60-120'", "age": "14+",
        "weight": 3.86, "rating": 8.6,
        "categories_kr": "어드벤처 · 던전크롤",
        "designer": "Isaac Childres",
        "shelf": "B-1-05",
        "expansion_label": None,
    },
    {
        "name_kr": "테라포밍 마스",
        "name_en": "Terraforming Mars",
        "year": 2016,
        "bgg_id": "167791",
        "image_url": "https://cf.geekdo-images.com/wg9oOLcsKvDesSUdZQ4rxw__original/img/thIqWDnH9utKuoKVEUqveDixprI=/0x0/filters:format(jpeg)/pic3536616.jpg",
        "min_p": 1, "max_p": 5, "best": "3-4",
        "time": "120'", "age": "12+",
        "weight": 3.24, "rating": 8.4,
        "categories_kr": "전략 · 카드드래프트",
        "designer": "Jacob Fryxelius",
        "shelf": "A-2-08",
        "expansion_label": None,
    },
    {
        "name_kr": "테라포밍 마스: 프렐류드",
        "name_en": "Terraforming Mars: Prelude",
        "year": 2018,
        "bgg_id": "247030",
        "image_url": "https://cf.geekdo-images.com/X3PN-NBSN_jb7xjDUrBlMA__imagepagezoom/img/8oLeXLqH5MoLi1RfEFbHPDZRsck=/fit-in/1024x1024/filters:no_upscale():strip_icc()/pic3913148.jpg",
        "min_p": 1, "max_p": 5, "best": "3-4",
        "time": "120'", "age": "12+",
        "weight": 3.18, "rating": 8.5,
        "categories_kr": "확장 · 전략",
        "designer": "Jacob Fryxelius",
        "shelf": "A-2-09",
        "expansion_label": "확장판 · 테라포밍 마스",
    },
]


# ── Download & cache box art ──────────────────────────────────────────────────
def ensure_images() -> dict:
    """Download all sample images. Returns dict bgg_id → Path."""
    try:
        import requests
        from PIL import Image
    except ImportError as e:
        print(f"  [warn] {e} — images may be missing")
        return {}

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    paths = {}
    for s in SAMPLES:
        gid = s["bgg_id"]
        dst = CACHE_IMG / f"{gid}.jpg"
        if dst.exists():
            print(f"  [cache] {dst.name}")
            paths[gid] = dst
            continue
        print(f"  [download] {gid} from BGG…")
        downloaded = False
        urls_to_try = [s["image_url"]]
        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                w, h = img.size
                if max(w, h) > 1200:
                    scale = 1200 / max(w, h)
                    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                img.save(dst, "JPEG", quality=85)
                print(f"  [saved] {dst.name} ({img.size})")
                paths[gid] = dst
                downloaded = True
                break
            except Exception as e:
                print(f"  [warn] {gid} URL failed ({e})")

        if not downloaded:
            fallback = CACHE_IMG / "167791.jpg" if int(gid) % 2 == 0 else CACHE_IMG / "224517.jpg"
            if fallback.exists():
                shutil.copy(fallback, dst)
                print(f"  [fallback] {gid}.jpg → using {fallback.name}")
                paths[gid] = dst
            else:
                fallback_alt = CACHE_IMG / "224517.jpg"
                if fallback_alt.exists():
                    shutil.copy(fallback_alt, dst)
                    paths[gid] = dst

    return paths


# ── Build view-model dicts ────────────────────────────────────────────────────
def build_cards(img_paths: dict) -> list:
    cards = []
    for s in SAMPLES:
        gid = s["bgg_id"]
        img_path = img_paths.get(gid)
        if img_path and img_path.exists():
            image_path = f"file://{img_path.resolve()}"
        else:
            image_path = ""

        weight_pct = round(s["weight"] / 5 * 100, 1)
        rating_pct = round(s["rating"] / 10 * 100, 1)
        players = f"{s['min_p']}–{s['max_p']}인"

        cards.append({
            "name_kr":        s["name_kr"],
            "name_en":        s["name_en"],
            "year":           str(s["year"]),
            "categories_kr":  s["categories_kr"],
            "weight":         f"{s['weight']:.2f}",
            "rating":         f"{s['rating']:.1f}",
            "weight_pct":     weight_pct,
            "rating_pct":     rating_pct,
            "players":        players,
            "best":           s["best"],
            "time":           s["time"],
            "age":            s["age"],
            "designer":       s["designer"],
            "shelf":          s["shelf"],
            "expansion_label": s["expansion_label"],
            "image_path":     image_path,
        })
        
    full_cards = []
    # Make sure we generate exactly 9 cards
    for i in range(9):
        full_cards.append(cards[i % len(cards)])
    return full_cards


# ── Render HTML via Jinja2 ────────────────────────────────────────────────────
def render_html(cards: list) -> Path:
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("ERROR: jinja2 not installed. Run: pip install jinja2")
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "src/catalog/templates")),
        autoescape=False,
    )
    tmpl = env.get_template("page.html")
    html = tmpl.render(
        cards=cards,
        styles_path=f"file://{(ROOT / 'src/catalog/assets/styles.css').resolve()}",
        icons_path=f"file://{ICONS_DIR.resolve()}",
    )
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  [html] written → {OUTPUT_HTML}")
    return OUTPUT_HTML


# ── Playwright PDF ────────────────────────────────────────────────────────────
def render_pdf(html_path: Path) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed.")
        print("Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print("  [playwright] launching Chromium…")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path.resolve()}", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)  # allow fonts + images to load
        page.pdf(
            path=str(OUTPUT_PDF),
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
    print(f"  [playwright] PDF written → {OUTPUT_PDF}")
    return OUTPUT_PDF


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Phase 0 — Playwright Renderer (4 cards) ===")
    img_paths = ensure_images()
    cards = build_cards(img_paths)
    html = render_html(cards)
    pdf = render_pdf(html)
    print(f"\nDone.")
    print(f"  PDF:  {pdf}")
    print(f"  HTML: {html}")
