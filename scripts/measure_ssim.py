#!/usr/bin/env python3
"""
SSIM comparison: crop a single card from the reference image PNG,
then compare against the same region cropped from each rendered PDF page.

Usage:
    python scripts/measure_ssim.py

Outputs results to stdout and appends to .omc/phase0/ssim_results.json
"""
import json
import sys
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
REF_IMAGE    = ROOT / "177505129178144.png"
PDF_A        = ROOT / "output/phase0_playwright.pdf"
PDF_B        = ROOT / "output/phase0_weasyprint.pdf"
BASELINE_JSON= ROOT / ".omc/phase0/baseline.json"
OUTPUT_JSON  = ROOT / ".omc/phase0/ssim_results.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Reference image card crop: top-left card in the mosaic.
# Measured from 177505129178144.png (850×1311px):
#   3-column layout, card cols: x=12-273, x=295-555, x=578-838
#   Row 0 (shortest): y=131-383 (252px tall) — NOTE: this row appears cropped/smaller
#   Row 1: y=410-778 (368px tall) — full-height cards
#
# We use the TOP-LEFT card (col 0, row 0) at pixel coords:
REF_CARD_CROP = (12, 131, 273, 383)   # (x0, y0, x1, y1) in reference image px

TARGET_SIZE = (240, 336)  # resize both to this before SSIM (≈63×88mm at 96dpi)


def load_reference_card(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    img = Image.open(path).convert("RGB")
    # Use exact measured crop of top-left card in the 3-column mosaic
    card = img.crop(REF_CARD_CROP)
    card = card.resize(TARGET_SIZE, Image.LANCZOS)
    return np.array(card)


def pdf_to_card_array(pdf_path: Path) -> "np.ndarray | None":
    """Render first page of PDF → numpy array, crop top-left card."""
    try:
        import fitz  # PyMuPDF
        HAS_FITZ = True
    except ImportError:
        HAS_FITZ = False

    if HAS_FITZ:
        import numpy as np
        from PIL import Image
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(3, 3)  # 3× zoom → ~216 DPI
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()

        # Crop top-left card: A4 page at 216dpi ≈ 1786×2527px
        # margin 15mm → 15/210*1786 ≈ 128px
        # card 63mm → 63/210*1786 ≈ 536px wide ; 88/297*2527 ≈ 749px tall
        w, h = img.size
        margin_x = int(15 / 210 * w)
        margin_y = int(15 / 297 * h)
        card_w = int(63 / 210 * w)
        card_h = int(88 / 297 * h)
        card = img.crop((margin_x, margin_y, margin_x + card_w, margin_y + card_h))
        card = card.resize(TARGET_SIZE, Image.LANCZOS)
        return np.array(card)

    # Fallback: use pdf2image (requires poppler)
    try:
        from pdf2image import convert_from_path
        import numpy as np
        from PIL import Image

        pages = convert_from_path(str(pdf_path), dpi=150, first_page=1, last_page=1)
        img = pages[0].convert("RGB")
        w, h = img.size
        margin_x = int(15 / 210 * w)
        margin_y = int(15 / 297 * h)
        card_w = int(63 / 210 * w)
        card_h = int(88 / 297 * h)
        card = img.crop((margin_x, margin_y, margin_x + card_w, margin_y + card_h))
        card = card.resize(TARGET_SIZE, Image.LANCZOS)
        return np.array(card)
    except Exception as e:
        print(f"  [warn] PDF rasterization failed ({e}). Trying HTML screenshot fallback.")
        return _html_screenshot_card()


def _html_screenshot_card() -> "np.ndarray | None":
    """Fallback: screenshot the rendered HTML with Playwright."""
    try:
        import numpy as np
        from PIL import Image
        from playwright.sync_api import sync_playwright

        html_path = ROOT / "output/phase0_page.html"
        if not html_path.exists():
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 794, "height": 1123})
            page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
            page.wait_for_timeout(1000)
            png_bytes = page.screenshot(full_page=False)
            browser.close()

        img = Image.open(__import__("io").BytesIO(png_bytes)).convert("RGB")
        # Crop first card: margin ~57px at 96dpi (15mm), card ~240px wide (63mm)
        margin_x = int(15 / 210 * img.width)
        margin_y = int(15 / 297 * img.height)
        card_w = int(63 / 210 * img.width)
        card_h = int(88 / 297 * img.height)
        card = img.crop((margin_x, margin_y, margin_x + card_w, margin_y + card_h))
        card = card.resize(TARGET_SIZE, Image.LANCZOS)
        return np.array(card)
    except Exception as e:
        print(f"  [error] HTML screenshot fallback failed: {e}")
        return None


def compute_ssim(arr_a, arr_b) -> float:
    import numpy as np
    from skimage.metrics import structural_similarity as ssim
    return float(ssim(arr_a, arr_b, channel_axis=2, data_range=255))


def main():
    print("=== SSIM Measurement ===")

    try:
        import numpy as np
        from skimage.metrics import structural_similarity
    except ImportError as e:
        print(f"ERROR: {e}\nRun: pip install scikit-image numpy")
        sys.exit(1)

    # Load baseline
    baseline_floor = 0.97
    if BASELINE_JSON.exists():
        data = json.loads(BASELINE_JSON.read_text())
        baseline_floor = data.get("baseline_floor", 0.97)
        print(f"  [baseline] floor = {baseline_floor:.4f}")

    # Load reference card
    ref_card = load_reference_card(REF_IMAGE)
    print(f"  [ref] card cropped from {REF_IMAGE.name} → {ref_card.shape}")

    results = {"baseline_floor": baseline_floor}

    # Measure Playwright PDF
    if PDF_A.exists():
        print(f"\n  [playwright] loading {PDF_A.name}…")
        card_a = pdf_to_card_array(PDF_A)
        if card_a is not None:
            ssim_a = compute_ssim(ref_card, card_a)
            results["ssim_playwright"] = round(ssim_a, 4)
            status = "PASS" if ssim_a >= baseline_floor else "FAIL"
            print(f"  [playwright] SSIM = {ssim_a:.4f}  [{status}]")
        else:
            print("  [playwright] could not rasterize PDF")
            results["ssim_playwright"] = None
    else:
        print(f"  [playwright] PDF not found: {PDF_A}")
        results["ssim_playwright"] = None

    # Measure WeasyPrint PDF
    skip_note = ROOT / "output/phase0_weasyprint_skip.txt"
    if skip_note.exists():
        reason = skip_note.read_text().strip()
        print(f"\n  [weasyprint] SKIPPED — {reason[:80]}")
        results["ssim_weasyprint"] = None
        results["weasyprint_skip_reason"] = reason
    elif PDF_B.exists():
        print(f"\n  [weasyprint] loading {PDF_B.name}…")
        card_b = pdf_to_card_array(PDF_B)
        if card_b is not None:
            ssim_b = compute_ssim(ref_card, card_b)
            results["ssim_weasyprint"] = round(ssim_b, 4)
            status = "PASS" if ssim_b >= baseline_floor else "FAIL"
            print(f"  [weasyprint] SSIM = {ssim_b:.4f}  [{status}]")
        else:
            print("  [weasyprint] could not rasterize PDF")
            results["ssim_weasyprint"] = None
    else:
        print(f"  [weasyprint] PDF not found: {PDF_B}")
        results["ssim_weasyprint"] = None

    # Delta
    sa = results.get("ssim_playwright")
    sb = results.get("ssim_weasyprint")
    if sa is not None and sb is not None:
        delta = round(abs(sa - sb), 4)
        results["delta_ssim"] = delta
        print(f"\n  [delta] |SSIM_A - SSIM_B| = {delta:.4f}")
        # Decision rule
        if delta <= 0.02 and sa >= baseline_floor and sb >= baseline_floor:
            decision = "B_preferred"  # WeasyPrint wins on determinism
        elif sa is not None and (sb is None or sa >= sb):
            decision = "A_preferred"
        else:
            decision = "B_preferred"
        results["decision"] = decision
        print(f"  [decision] → {decision}")

    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n  [saved] {OUTPUT_JSON}")
    return results


if __name__ == "__main__":
    main()
