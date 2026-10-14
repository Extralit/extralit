"""Cheap, structural triage of a PDF (~53 ms over 300 pages).

pdf-inspector reads the page objects; it never rasterizes and bundles no OCR engine, so it can say
which pages *need* OCR but cannot produce text for them. `pages_needing_ocr` is therefore surfaced
as an explicit gap rather than acted on.
"""

from __future__ import annotations

import logging

import pdf_inspector

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata

_LOGGER = logging.getLogger(__name__)


def triage_pdf(pdf_bytes: bytes) -> TriageMetadata:
    """Classify a PDF's structure. Never raises: an unreadable PDF is `pdf_type="unknown"`."""
    try:
        result = pdf_inspector.detect_pdf_bytes(pdf_bytes)
    except Exception as error:
        _LOGGER.warning(f"PDF triage failed: {error}")
        return TriageMetadata(pdf_type="unknown")

    return TriageMetadata(
        pdf_type=str(result.pdf_type),
        confidence=result.confidence,
        page_count=result.page_count,
        # detect_pdf_bytes reports 1-indexed pages (classify_pdf_bytes does not).
        pages_needing_ocr=sorted(result.pages_needing_ocr or []),
        ocr_reasons_by_page={str(entry.page): list(entry.reasons) for entry in (result.ocr_reasons_by_page or [])},
        pages_with_tables=sorted(result.pages_with_tables or []),
        pages_with_columns=sorted(result.pages_with_columns or []),
        has_encoding_issues=bool(result.has_encoding_issues),
    )
