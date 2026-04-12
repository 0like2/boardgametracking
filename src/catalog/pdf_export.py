"""PDF exporters: abstract base + Playwright and WeasyPrint implementations."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path


class PdfExporter(ABC):
    """Abstract base for HTML → PDF exporters."""

    @abstractmethod
    def export(self, html: str, output_path: Path, base_url: Path) -> None:
        """Write HTML content to output_path as a PDF.

        Args:
            html: Complete HTML document string.
            output_path: Destination PDF file path.
            base_url: Directory used to resolve relative asset paths (CSS, fonts, images).
        """
        ...


class PlaywrightExporter(PdfExporter):
    """Uses headless Chromium via Playwright to render the PDF."""

    def export(self, html: str, output_path: Path, base_url: Path) -> None:
        asyncio.run(self._run(html, output_path, base_url))

    async def _run(self, html: str, output_path: Path, base_url: Path) -> None:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Write HTML to a temp file inside base_url so relative asset
            # paths (CSS, fonts, icons) resolve correctly via file:// URLs.
            tmp = base_url / "_render_tmp.html"
            tmp.write_text(html, encoding="utf-8")
            try:
                await page.goto(f"file://{tmp.resolve()}")
                await page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
            finally:
                if tmp.exists():
                    tmp.unlink()
                await browser.close()


class WeasyPrintExporter(PdfExporter):
    """Uses WeasyPrint to render the PDF (no browser required)."""

    def export(self, html: str, output_path: Path, base_url: Path) -> None:
        try:
            from weasyprint import HTML  # type: ignore[import-untyped]
        except ImportError as e:
            raise RuntimeError(
                "WeasyPrint is not installed. Run: pip install weasyprint"
            ) from e

        HTML(string=html, base_url=str(base_url.resolve())).write_pdf(
            str(output_path)
        )


def make_exporter(renderer_name: str) -> PdfExporter:
    """Factory: return a PdfExporter by name ('playwright' or 'weasyprint')."""
    name = renderer_name.lower().strip()
    if name == "playwright":
        return PlaywrightExporter()
    if name == "weasyprint":
        return WeasyPrintExporter()
    raise ValueError(
        f"Unknown renderer '{renderer_name}'. Choose 'playwright' or 'weasyprint'."
    )
