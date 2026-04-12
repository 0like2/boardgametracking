#!/usr/bin/env python3
"""
Baseline calibration — self-SSIM of reference image through identity JPEG pipeline.

Pipeline: decode PNG → re-encode JPEG q=85 → re-decode → SSIM with original.
Goal: baseline_floor ≥ 0.97

Output: .omc/phase0/baseline.json
"""
import json
import sys
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
REF_IMAGE   = ROOT / "177505129178144.png"
OUTPUT_JSON = ROOT / ".omc/phase0/baseline.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

def main():
    print("=== Baseline Calibration ===")

    # ── Imports ───────────────────────────────────────────────────────────────
    try:
        import numpy as np
        from PIL import Image
        import io
        from skimage.metrics import structural_similarity as ssim
    except ImportError as e:
        print(f"ERROR: missing dependency — {e}")
        print("Run: pip install pillow scikit-image numpy")
        sys.exit(1)

    # ── Load reference ────────────────────────────────────────────────────────
    if not REF_IMAGE.exists():
        print(f"ERROR: reference image not found: {REF_IMAGE}")
        sys.exit(1)

    orig = Image.open(REF_IMAGE).convert("RGB")
    arr_orig = np.array(orig)
    print(f"  [ref] {REF_IMAGE.name} — {orig.size} px")

    # ── Identity JPEG pipeline ────────────────────────────────────────────────
    buf = io.BytesIO()
    orig.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    reencoded = Image.open(buf).convert("RGB")
    arr_re = np.array(reencoded)

    # ── SSIM ──────────────────────────────────────────────────────────────────
    score = ssim(arr_orig, arr_re, channel_axis=2, data_range=255)
    print(f"  [SSIM] self-pipeline = {score:.4f}")

    goal = 0.97
    status = "PASS" if score >= goal else "FAIL"
    print(f"  [result] {status} (goal ≥ {goal})")

    # ── Save JSON ─────────────────────────────────────────────────────────────
    result = {
        "baseline_floor": round(float(score), 4),
        "goal": goal,
        "status": status,
        "pipeline": "decode_PNG → JPEG_q85 → decode → SSIM",
        "reference_image": str(REF_IMAGE.name),
        "reference_size": list(orig.size),
    }
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"  [saved] {OUTPUT_JSON}")

    if status == "FAIL":
        print(f"\n  WARNING: baseline_floor {score:.4f} < {goal}. SSIM comparison results may be unreliable.")

    return result

if __name__ == "__main__":
    main()
