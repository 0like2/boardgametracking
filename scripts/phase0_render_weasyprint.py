#!/usr/bin/env python3
"""
Phase 0 spike — render page.html → output/phase0_weasyprint.pdf using WeasyPrint.
Uses the same HTML as phase0_render_playwright.py (run that first to generate HTML).
Run: python scripts/phase0_render_weasyprint.py

If WeasyPrint or its system deps (Pango/Cairo) are missing, prints a diagnostic
and exits 0 — that outcome is also a valid Phase 0 result.
"""
import sys
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
OUTPUT_PDF = ROOT / "output/phase0_weasyprint.pdf"
OUTPUT_HTML= ROOT / "output/phase0_page.html"

OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)


def main():
    print("=== Phase 0 — WeasyPrint Renderer ===")

    # Check WeasyPrint availability
    try:
        import weasyprint
        print(f"  [weasyprint] version {weasyprint.__version__}")
    except ImportError as e:
        _report_missing("weasyprint", str(e))
        return
    except Exception as e:
        _report_system_dep(str(e))
        return

    # Check HTML exists
    if not OUTPUT_HTML.exists():
        print(f"  [error] HTML not found: {OUTPUT_HTML}")
        print("  Run phase0_render_playwright.py first to generate the HTML.")
        sys.exit(1)

    # Render
    print(f"  [weasyprint] rendering {OUTPUT_HTML.name} …")
    try:
        from weasyprint import HTML
        # base_url set to ROOT so relative file:// paths in HTML resolve correctly
        html_doc = HTML(filename=str(OUTPUT_HTML), base_url=str(ROOT))
        html_doc.write_pdf(str(OUTPUT_PDF))
        size_kb = OUTPUT_PDF.stat().st_size // 1024
        print(f"  [weasyprint] PDF written → {OUTPUT_PDF}  ({size_kb} KB)")
    except Exception as e:
        print(f"\n  [weasyprint] RENDER FAILED: {e}")
        _record_failure(str(e))
        sys.exit(1)

    print(f"\nDone. Output: {OUTPUT_PDF}")


def _report_missing(pkg, detail):
    msg = f"WeasyPrint not installed ({detail}). Run: pip install weasyprint"
    print(f"\n  [SKIP] {msg}")
    _record_failure(msg)


def _report_system_dep(detail):
    msg = (
        f"WeasyPrint import error — likely missing system libs (Pango/Cairo/GDK).\n"
        f"  On macOS: brew install pango cairo gdk-pixbuf libffi\n"
        f"  Detail: {detail}"
    )
    print(f"\n  [SKIP] {msg}")
    _record_failure(msg)


def _record_failure(reason: str):
    note = ROOT / "output/phase0_weasyprint_skip.txt"
    note.write_text(reason)
    print(f"  [note] failure recorded at {note}")


if __name__ == "__main__":
    main()
