"""PyMuPDF layout parser (AGPL, optional `pymupdf` extra).

The higher-fidelity of the two: `find_tables()` yields per-cell geometry, which pdf-inspector
cannot provide. Coordinates are natively top-left in points, so nothing is flipped here.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Optional

import pymupdf
import pymupdf4llm
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, DoclingDocument, Size, TableCell

from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    content_hash,
    new_document,
)
from extralit_server.contexts.ocr.tables import make_cell

_LOGGER = logging.getLogger(__name__)

_TEXT_BLOCK = 0
_IMAGE_BLOCK = 1


def _bbox(rect: Sequence[float]) -> BoundingBox:
    """pymupdf rects are already top-left in page points."""
    left, top, right, bottom = (float(v) for v in rect)
    return BoundingBox(l=left, t=top, r=right, b=bottom, coord_origin=CoordOrigin.TOPLEFT)


def _header_levels(doc: pymupdf.Document, pages: Optional[Sequence[int]]) -> Optional[Any]:
    """Prefer the PDF outline for heading levels; fall back to font-size ranking."""
    try:
        if doc.get_toc():
            return pymupdf4llm.TocHeaders(doc)
    except Exception as e:
        _LOGGER.debug(f"outline unusable, ranking by font size instead: {e}")

    # IdentifyHeaders rejects indices past the end, so only pass pages that exist.
    indices = None
    if pages:
        indices = [p - 1 for p in pages if 0 < p <= doc.page_count]
        if not indices:
            return None
    return pymupdf4llm.IdentifyHeaders(doc, pages=indices)


def _heading_level(headers: Optional[Any], span: dict, page: pymupdf.Page) -> Optional[int]:
    """`get_header_id` returns a markdown prefix like '## '; its hash count is the level."""
    if headers is None:
        return None
    try:
        marker = headers.get_header_id(span, page=page)
    except Exception:
        return None
    level = marker.count("#")
    return level or None


def _block_text(block: dict) -> str:
    lines = []
    for line in block.get("lines", []):
        text = "".join(span.get("text", "") for span in line.get("spans", []))
        if text.strip():
            lines.append(text.strip())
    return " ".join(lines)


def _dominant_span(block: dict) -> Optional[dict]:
    """The largest span in a block decides whether the block reads as a heading."""
    spans = [span for line in block.get("lines", []) for span in line.get("spans", [])]
    return max(spans, key=lambda s: s.get("size", 0)) if spans else None


def _table_cells(table: Any) -> list[TableCell]:
    """Build cells from `find_tables()`, keeping the per-cell rects it hands back."""
    rows = table.extract()
    has_header = bool(table.header) and not table.header.external
    cells: list[TableCell] = []

    for row_index, (row, row_obj) in enumerate(zip(rows, table.rows, strict=False)):
        for col_index, value in enumerate(row):
            text = (value or "").strip()
            if not text:
                continue
            rect = row_obj.cells[col_index] if col_index < len(row_obj.cells) else None
            cells.append(
                make_cell(
                    text,
                    row=row_index,
                    col=col_index,
                    column_header=has_header and row_index == 0,
                    bbox=_bbox(rect) if rect else None,
                )
            )
    return cells


def _blocks_for_page(page: pymupdf.Page, headers: Any) -> list[LayoutBlock]:
    """Turn one page into ordered layout blocks."""
    blocks: list[LayoutBlock] = []

    try:
        tables = page.find_tables()
    except Exception as e:
        _LOGGER.warning(f"table detection failed on page {page.number + 1}: {e}")
        tables = None

    table_rects = []
    for table in getattr(tables, "tables", []) or []:
        bbox = _bbox(table.bbox)
        table_rects.append(pymupdf.Rect(*table.bbox))
        blocks.append(LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox, cells=_table_cells(table)))

    for block in page.get_text("dict").get("blocks", []):
        rect = pymupdf.Rect(block["bbox"])

        if block.get("type") == _IMAGE_BLOCK:
            blocks.append(LayoutBlock(label=DocItemLabel.PICTURE, bbox=_bbox(block["bbox"])))
            continue

        if block.get("type") != _TEXT_BLOCK:
            continue

        # Text inside a detected table is already carried by its cells.
        if any(rect.intersects(t) and (rect & t).get_area() >= rect.get_area() * 0.6 for t in table_rects):
            continue

        text = _block_text(block)
        if not text:
            continue

        span = _dominant_span(block)
        level = _heading_level(headers, span, page) if span else None
        blocks.append(
            LayoutBlock(
                label=DocItemLabel.SECTION_HEADER if level else DocItemLabel.TEXT,
                bbox=_bbox(block["bbox"]),
                text=text,
                level=level,
            )
        )

    blocks.sort(key=lambda b: (b.bbox.t, b.bbox.l))
    return blocks


def parse(
    pdf_bytes: bytes,
    *,
    name: str,
    pages: Optional[Sequence[int]] = None,
    filename: Optional[str] = None,
) -> DoclingDocument:
    """Parse PDF bytes into a `DoclingDocument`. `pages` is a 1-indexed allowlist."""
    doc = new_document(name, filename=filename, binary_hash=content_hash(pdf_bytes))
    wanted = set(pages) if pages else None

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        headers = _header_levels(pdf, pages)
        for index in range(pdf.page_count):
            page_no = index + 1
            if wanted is not None and page_no not in wanted:
                continue
            page = pdf[index]
            ctx = PageContext(page_no=page_no, size=Size(width=page.rect.width, height=page.rect.height))
            append_blocks(doc, ctx, _blocks_for_page(page, headers))

    return doc
