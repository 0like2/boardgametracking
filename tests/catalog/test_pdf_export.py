"""Tests for PdfExporter: PDF round-trip and font checks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.catalog.pdf_export import PlaywrightExporter, WeasyPrintExporter, make_exporter

_SIMPLE_HTML = """\
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Test</title></head>
<body><p>Hello 브라스</p></body>
</html>
"""


class TestMakeExporter:
    def test_playwright_factory(self):
        exp = make_exporter("playwright")
        assert isinstance(exp, PlaywrightExporter)

    def test_weasyprint_factory(self):
        exp = make_exporter("weasyprint")
        assert isinstance(exp, WeasyPrintExporter)

    def test_case_insensitive(self):
        assert isinstance(make_exporter("Playwright"), PlaywrightExporter)
        assert isinstance(make_exporter("WeasyPrint"), WeasyPrintExporter)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown renderer"):
            make_exporter("pdfkit")


class TestPlaywrightExporter:
    def test_creates_pdf(self, tmp_path: Path):
        """Integration test: requires Playwright + Chromium installed."""
        pytest.importorskip("playwright")
        exporter = PlaywrightExporter()
        out = tmp_path / "test.pdf"
        exporter.export(_SIMPLE_HTML, out, base_url=tmp_path)
        assert out.exists()
        assert out.stat().st_size > 0
        # Verify it starts with PDF magic bytes
        assert out.read_bytes()[:4] == b"%PDF"

    def test_cleans_up_tmp_file(self, tmp_path: Path):
        """Temp HTML file should not remain after export."""
        pytest.importorskip("playwright")
        exporter = PlaywrightExporter()
        out = tmp_path / "test.pdf"
        exporter.export(_SIMPLE_HTML, out, base_url=tmp_path)
        tmp_html = tmp_path / "_render_tmp.html"
        assert not tmp_html.exists()


class TestWeasyPrintExporter:
    def test_creates_pdf(self, tmp_path: Path):
        """Integration test: requires WeasyPrint installed."""
        pytest.importorskip("weasyprint")
        exporter = WeasyPrintExporter()
        out = tmp_path / "test.pdf"
        exporter.export(_SIMPLE_HTML, out, base_url=tmp_path)
        assert out.exists()
        assert out.stat().st_size > 0
        assert out.read_bytes()[:4] == b"%PDF"

    def test_raises_if_weasyprint_missing(self, tmp_path: Path):
        """Should raise RuntimeError when WeasyPrint is not importable."""
        exporter = WeasyPrintExporter()
        out = tmp_path / "test.pdf"
        with patch.dict("sys.modules", {"weasyprint": None}):
            with pytest.raises(RuntimeError, match="WeasyPrint is not installed"):
                exporter.export(_SIMPLE_HTML, out, base_url=tmp_path)
