"""Tests for the rotation-only ocrmypdf pass."""

from unittest.mock import MagicMock, patch

import pytest

from extralit_server.contexts.document.preprocessing import PDFPreprocessingSettings, PDFPreprocessor

MODULE = "extralit_server.contexts.document.preprocessing"


class TestOcrmypdfArgs:
    def test_ocr_is_off_and_only_rotation_is_paid_for(self):
        args = PDFPreprocessingSettings().get_ocrmypdf_args()

        assert args == {
            "rotate_pages": True,
            "rotate_pages_threshold": 2.0,
            "skip_text": True,
            "tesseract_timeout": 0,
            "tesseract_non_ocr_timeout": 30.0,
            "clean": False,
            "optimize": 0,
            "progress_bar": False,
            "jobs": 1,
        }

    def test_no_ocr_only_knob_survives(self):
        fields = PDFPreprocessingSettings.model_fields

        for dropped in ("language", "force_ocr", "redo_ocr", "skip_big", "pdf_renderer", "output_type", "deskew"):
            assert dropped not in fields


class TestPreprocess:
    def test_rotation_runs_on_every_pdf(self):
        settings = PDFPreprocessingSettings()

        with patch(f"{MODULE}.ocrmypdf") as ocrmypdf:
            ocrmypdf.ocr = MagicMock()
            response = PDFPreprocessor(settings).preprocess(b"%PDF-1.5", "paper.pdf")

        assert ocrmypdf.ocr.call_args.kwargs == settings.get_ocrmypdf_args()
        assert response.metadata.rotation_ran is True
        assert response.metadata.error is None

    def test_a_failed_rotation_returns_the_original_bytes(self):
        with patch(f"{MODULE}.ocrmypdf") as ocrmypdf:
            ocrmypdf.ocr = MagicMock(side_effect=RuntimeError("ghostscript died"))
            response = PDFPreprocessor().preprocess(b"%PDF-1.5 original", "paper.pdf")

        assert response.processed_data == b"%PDF-1.5 original"
        assert response.metadata.rotation_ran is False
        assert "ghostscript died" in response.metadata.error

    def test_a_non_pdf_is_left_alone(self):
        with patch(f"{MODULE}.ocrmypdf") as ocrmypdf:
            ocrmypdf.ocr = MagicMock()
            response = PDFPreprocessor().preprocess(b"not a pdf", "notes.txt")

        ocrmypdf.ocr.assert_not_called()
        assert response.processed_data == b"not a pdf"
        assert response.metadata.rotation_ran is False

    def test_disabling_preprocessing_skips_ocrmypdf(self):
        with patch(f"{MODULE}.ocrmypdf") as ocrmypdf:
            ocrmypdf.ocr = MagicMock()
            response = PDFPreprocessor(PDFPreprocessingSettings(enabled=False)).preprocess(b"%PDF", "paper.pdf")

        ocrmypdf.ocr.assert_not_called()
        assert response.metadata.rotation_ran is False


@pytest.mark.parametrize("attribute", ["analyzer", "enable_analysis"])
def test_the_preprocessor_no_longer_analyzes(attribute):
    # Margins and the thumbnail are the analysis job's business; the in-class path returned a
    # tuple where the metadata expected a dict.
    assert not hasattr(PDFPreprocessor(), attribute)
    assert attribute not in PDFPreprocessingSettings.model_fields
