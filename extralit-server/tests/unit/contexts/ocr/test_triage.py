"""Tests for the structural triage pass."""

from pathlib import Path

import pytest

from extralit_server.contexts.ocr.triage import triage_pdf

FIXTURES = Path(__file__).parents[3] / "fixtures" / "pdf"


@pytest.fixture
def pdf_bytes():
    return (FIXTURES / "sample.pdf").read_bytes()


class TestTriagePdf:
    def test_reports_structure_with_one_indexed_pages(self, pdf_bytes):
        result = triage_pdf(pdf_bytes)

        assert result.page_count == 1
        assert result.pdf_type
        assert 0 not in result.pages_needing_ocr
        assert all(page >= 1 for page in result.pages_needing_ocr)

    def test_ocr_reasons_are_keyed_by_page(self, pdf_bytes):
        result = triage_pdf(pdf_bytes)

        for page, reasons in result.ocr_reasons_by_page.items():
            assert int(page) >= 1
            assert reasons

    def test_an_unreadable_pdf_is_unknown_rather_than_an_error(self):
        result = triage_pdf(b"not a pdf at all")

        assert result.pdf_type == "unknown"
        assert result.page_count == 0
        assert result.pages_needing_ocr == []
