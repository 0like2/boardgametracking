#!/usr/bin/env python3
"""
Palette ΔE measurement — compare 5+2 color swatches between:
  - reference image (sampled pixel coords)
  - rendered HTML screenshot (via Playwright)

Swatches:
  bg           #0a0a0a   (card background)
  info-bg      #161616   (info row background)
  text         #ffffff   (Korean title)
  muted        #8a8a8a   (English title)
  star         #f5b400   (BGG rating star / yellow gauge)
  orange-gauge #ff7a00   (weight / orange gauge)
  footer-shelf #ff7a00   (shelf label — same orange)

Output: .omc/phase0/palette_results.json
"""
import json
import sys
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
REF_IMAGE   = ROOT / "177505129178144.png"
OUTPUT_JSON = ROOT / ".omc/phase0/palette_results.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Target CSS hex values
TARGET_SWATCHES = {
    "bg":           "#0a0a0a",
    "info-bg":      "#161616",
    "text":         "#ffffff",
    "muted":        "#8a8a8a",
    "star":         "#f5b400",
    "orange-gauge": "#ff7a00",
    "yellow-gauge": "#f5b400",
}

# Reference image card crop (measured pixel coords, 850×1311 image):
# Top-left card: x=12-273 (261px wide), y=131-383 (252px tall)
# Normalized sample points are WITHIN this card region.
#
# NOTE: The reference image is a compressed JPEG screenshot (~72dpi), so colors
# are washed out (dark #0a0a0a renders as ~50,50,50; orange #ff7a00 appears at
# the shelf label row y≈119-124 within the card at x≈53-164).
# ΔE values from reference are expected to be high (30-80) due to compression.
# The more meaningful ΔE is rendered-vs-target-CSS (see "rendered" section).
REF_CARD_BBOX = (12, 131, 273, 383)   # absolute px in reference image

REF_SAMPLE_POINTS = {
    # Normalized coords within the card crop (261×252px)
    # bg: bottom-left corner of card (very dark area in footer)
    "bg":           (0.05, 0.95),   # footer bottom-left
    # info-bg: middle of info row strip
    "info-bg":      (0.40, 0.88),   # info row band
    # text: title area (white Korean text)
    "text":         (0.35, 0.70),   # title text region
    # muted: English subtitle (gray text row)
    "muted":        (0.35, 0.75),   # English title row
    # star: rating badge area top-right
    "star":         (0.82, 0.10),   # top-right badge
    # orange-gauge: shelf label (orange text row y≈0.47-0.49 in card)
    "orange-gauge": (0.30, 0.48),   # shelf label / orange area
    # yellow-gauge: same row, slightly right
    "yellow-gauge": (0.45, 0.48),   # adjacent yellow area
}


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_lab(r, g, b):
    """Convert sRGB (0-255) to CIE Lab."""
    try:
        from colormath.color_objects import sRGBColor, LabColor
        from colormath.color_conversions import convert_color
        rgb = sRGBColor(r / 255, g / 255, b / 255)
        lab = convert_color(rgb, LabColor)
        return lab.lab_l, lab.lab_a, lab.lab_b
    except ImportError:
        # Fallback: rough approximation
        import math
        def linearize(c):
            c /= 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        rl, gl, bl_ = linearize(r), linearize(g), linearize(b)
        X = rl * 0.4124 + gl * 0.3576 + bl_ * 0.1805
        Y = rl * 0.2126 + gl * 0.7152 + bl_ * 0.0722
        Z = rl * 0.0193 + gl * 0.1192 + bl_ * 0.9505
        def f(t):
            return t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116
        Xn, Yn, Zn = 0.95047, 1.00000, 1.08883
        L = 116 * f(Y / Yn) - 16
        a = 500 * (f(X / Xn) - f(Y / Yn))
        b_ = 200 * (f(Y / Yn) - f(Z / Zn))
        return L, a, b_


def delta_e(lab1, lab2) -> float:
    """CIE76 ΔE."""
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2)) ** 0.5


def sample_pixel(img, nx: float, ny: float, radius: int = 3):
    """Sample average pixel in a small region around normalized (nx, ny)."""
    import numpy as np
    arr = np.array(img)
    h, w = arr.shape[:2]
    cx, cy = int(nx * w), int(ny * h)
    x0, x1 = max(0, cx - radius), min(w, cx + radius + 1)
    y0, y1 = max(0, cy - radius), min(h, cy + radius + 1)
    patch = arr[y0:y1, x0:x1]
    mean = patch.mean(axis=(0, 1))
    return int(mean[0]), int(mean[1]), int(mean[2])


def screenshot_rendered_card():
    """Take a screenshot of the first rendered card element via Playwright.
    Uses --force-color-profile=srgb so CSS colors render correctly.
    Returns the card element screenshot (not full page).
    """
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image
        import io

        html_path = ROOT / "output/phase0_page.html"
        if not html_path.exists():
            print("  [warn] rendered HTML not found, run phase0_render_playwright.py first")
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--force-color-profile=srgb"])
            page = browser.new_page(viewport={"width": 1200, "height": 1700})
            page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            # Screenshot just the first .card element so coords are card-relative
            card_el = page.query_selector(".card")
            if card_el is None:
                print("  [warn] .card element not found in rendered page")
                browser.close()
                return None
            png_bytes = card_el.screenshot()
            browser.close()

        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        print(f"  [card screenshot] {img.size}")
        return img
    except Exception as e:
        print(f"  [warn] screenshot failed: {e}")
        return None


def measure_swatches(img, sample_points: dict, label: str) -> dict:
    results = {}
    for name, (nx, ny) in sample_points.items():
        r, g, b = sample_pixel(img, nx, ny)
        target_hex = TARGET_SWATCHES[name]
        tr, tg, tb = hex_to_rgb(target_hex)
        lab_actual = rgb_to_lab(r, g, b)
        lab_target = rgb_to_lab(tr, tg, tb)
        de = delta_e(lab_actual, lab_target)
        actual_hex = f"#{r:02x}{g:02x}{b:02x}"
        results[name] = {
            "target_hex": target_hex,
            "actual_hex": actual_hex,
            "actual_rgb": [r, g, b],
            "delta_e": round(de, 2),
            "pass": de < 5.0,
        }
        status = "PASS" if de < 5.0 else "FAIL"
        print(f"    {name:<15} target={target_hex}  actual={actual_hex}  ΔE={de:5.2f}  [{status}]")
    return results


def main():
    print("=== Palette ΔE Measurement ===")

    try:
        from PIL import Image
        import numpy as np
    except ImportError as e:
        print(f"ERROR: {e}\nRun: pip install pillow numpy")
        sys.exit(1)

    output = {}

    # ── Reference image swatches ──────────────────────────────────────────────
    # Crop the top-left card from the mosaic, then sample within it.
    print(f"\n[Reference image: {REF_IMAGE.name}]")
    ref_full = Image.open(REF_IMAGE).convert("RGB")
    ref_img = ref_full.crop(REF_CARD_BBOX)   # 261×252 px card crop
    print(f"  [card crop] {ref_img.size} px from bbox {REF_CARD_BBOX}")
    output["reference"] = measure_swatches(ref_img, REF_SAMPLE_POINTS, "reference")

    # ── Rendered HTML screenshot swatches ─────────────────────────────────────
    print(f"\n[Rendered HTML screenshot]")
    rendered_img = screenshot_rendered_card()
    if rendered_img is not None:
        # The screenshot is already the card element (239×334px approx).
        # We define rendered-specific sample points calibrated to the card geometry:
        # Measured from card element screenshot (239×334):
        #   gauge-orange at (2, 167) = x≈0.008, y≈0.50
        #   gauge-yellow at (5, 167) = x≈0.021, y≈0.50  (same orange area at mid)
        #   info-row at y≈0.85 (284/334)
        #   footer at y≈0.955 (319/334)
        #   bg (card-inner dark) at bottom-left (5, 324) = x≈0.021, y≈0.97
        #   title area around y≈0.70
        #   rating badge top-right at (219, 15) = x≈0.92, y≈0.045
        # Calibrated from 239×334 card element screenshot with --force-color-profile=srgb
        # x=0: trim-mark area (gray #f0f0f0). Card inner at x=1+.
        # Orange gauge (weight): x=1-5,  y=130-334 (filled from bottom, weight=3.91→78%)
        # Yellow gauge (rating): x=8-13, y=103-334 (filled from bottom, rating=8.6→86%)
        # Rating badge:  x≈219, y≈12
        # Info row:      y≈280-310 (y/h=0.84-0.93), #161616
        # Footer:        y≈315-330 (y/h=0.94-0.99), #111111
        RENDERED_SAMPLE_POINTS = {
            "bg":           (0.021, 0.97),   # footer bottom (x=5, y=323)
            "info-bg":      (0.50,  0.88),   # info row center (x=119, y=293)
            "text":         (0.35,  0.68),   # title text area
            "muted":        (0.35,  0.73),   # English subtitle
            "star":         (0.918, 0.036),  # rating badge (x=219, y=12)
            "orange-gauge": (0.013, 0.69),   # orange gauge (x=3, y=230) = #ff7a00
            "yellow-gauge": (0.042, 0.60),   # yellow gauge (x=10, y=200) = #f5b400
        }
        output["rendered"] = measure_swatches(rendered_img, RENDERED_SAMPLE_POINTS, "rendered")

        # Compute max ΔE
        max_de = max(v["delta_e"] for v in output["rendered"].values())
        output["max_delta_e_rendered"] = round(max_de, 2)
        print(f"\n  max ΔE (rendered vs target) = {max_de:.2f}  {'PASS' if max_de < 5 else 'FAIL'}")
    else:
        output["rendered"] = None
        output["max_delta_e_rendered"] = None
        print("  [skip] could not screenshot rendered card")

    # Max ΔE for reference image (how well reference matches our target palette)
    max_de_ref = max(v["delta_e"] for v in output["reference"].values())
    output["max_delta_e_reference"] = round(max_de_ref, 2)
    print(f"  max ΔE (reference vs target) = {max_de_ref:.2f}")

    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n  [saved] {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
