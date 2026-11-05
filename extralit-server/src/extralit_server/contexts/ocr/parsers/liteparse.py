"""liteparse layout parser: OCR-routed pages, and digital pages when pymupdf is not installed.

Block and cell rects are natively top-left in 72-DPI page points, so nothing is flipped here.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import Optional

import liteparse
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, TableCell

from extralit_server.contexts.ocr.docling_builder import LayoutBlock
from extralit_server.contexts.ocr.tables import make_cell

_LOGGER = logging.getLogger(__name__)

# Only these kinds render as markdown; heading and table cell text is raw, so its `*` is literal.
_MARKDOWN_KINDS = frozenset({"paragraph", "list_item"})
_STRIKETHROUGH = re.compile(r"~~(.+?)~~")
_ESCAPE_OR_EMPHASIS = re.compile(r"\\([!-/:-@\[-`{-~])|\*+")

_LABELS = {
    "heading": DocItemLabel.SECTION_HEADER,
    "paragraph": DocItemLabel.TEXT,
    "list_item": DocItemLabel.LIST_ITEM,
    "code": DocItemLabel.CODE,
    "grid_fallback": DocItemLabel.TEXT,
    "table": DocItemLabel.TABLE,
    "figure": DocItemLabel.PICTURE,
}


def _bbox(rect: liteparse.AnnotationRect) -> BoundingBox:
    return BoundingBox(
        l=rect.x,
        t=rect.y,
        r=rect.x + rect.width,
        b=rect.y + rect.height,
        coord_origin=CoordOrigin.TOPLEFT,
    )


def _plain_text(markdown: str) -> str:
    """Drop inline emphasis; a literal `*` arrives escaped, while an unpaired `~~` is literal."""
    return _ESCAPE_OR_EMPHASIS.sub(lambda m: m[1] or "", _STRIKETHROUGH.sub(r"\1", markdown))


def _table_rows(block: liteparse.LayoutBlock) -> list[list[liteparse.LayoutCell]]:
    """`header` is not repeated in `rows`, so it becomes row 0 and the body shifts down."""
    return [block.header, *(block.rows or [])] if block.header else (block.rows or [])


def _filled_rows(block: liteparse.LayoutBlock) -> list[list[str]]:
    rows = ([cell.text.strip() for cell in row] for row in _table_rows(block))
    return [row for row in rows if any(row)]


def restore_stripped_rows(
    block: liteparse.LayoutBlock, unstripped: Sequence[liteparse.LayoutBlock]
) -> liteparse.LayoutBlock:
    """Swap in the unstripped table when it is this table plus lost leading rows.

    A lost row must fill two cells, because a running title can also fuse onto a table.
    """
    if block.kind != "table":
        return block

    rows = _filled_rows(block)
    for candidate in unstripped:
        if candidate.kind != "table":
            continue
        candidate_rows = _filled_rows(candidate)
        lost = candidate_rows[: -len(rows)] if rows else []
        if lost and candidate_rows[-len(rows) :] == rows and all(sum(map(bool, row)) >= 2 for row in lost):
            return candidate
    return block


def _table_cells(block: liteparse.LayoutBlock) -> list[TableCell]:
    return [
        make_cell(
            cell.text.strip(),
            row=row_index,
            col=col_index,
            column_header=bool(block.header) and row_index == 0,
            bbox=_bbox(cell.bbox) if cell.bbox else None,
        )
        for row_index, row in enumerate(_table_rows(block))
        for col_index, cell in enumerate(row)
    ]


def to_layout_block(block: liteparse.LayoutBlock) -> Optional[LayoutBlock]:
    """Map one liteparse block; rules carry no content, and a block without a bbox cannot be placed."""
    if block.kind == "rule":
        return None

    label = _LABELS.get(block.kind)
    if label is None or block.bbox is None:
        _LOGGER.warning(f"dropping liteparse {block.kind!r} block with bbox {block.bbox}")
        return None

    text = block.text or "\n".join(block.lines or [])
    return LayoutBlock(
        label=label,
        bbox=_bbox(block.bbox),
        text=_plain_text(text) if block.kind in _MARKDOWN_KINDS else text,
        # On a list_item `level` is nesting depth, which must not turn it into a heading.
        level=block.level if label == DocItemLabel.SECTION_HEADER else None,
        cells=_table_cells(block) if label == DocItemLabel.TABLE else None,
        marker=block.marker,
        enumerated=bool(block.ordered),
    )


class LiteParseParser:
    """`PageParser` over liteparse; `parse_pages` blocks, so async callers must run it in a thread."""

    def __init__(self, *, num_workers: Optional[int] = None):
        self._num_workers = num_workers

    def _blocks(
        self, pdf_bytes: bytes, pages: Sequence[int], *, ocr: bool, keep_headers_footers: bool = False
    ) -> dict[int, list[liteparse.LayoutBlock]]:
        engine = liteparse.LiteParse(
            ocr_enabled=ocr,
            extract_blocks=True,
            target_pages=",".join(str(page) for page in pages),
            num_workers=self._num_workers,
            keep_headers_footers=keep_headers_footers,
            quiet=True,
        )
        return {page.page_num: page.blocks or [] for page in engine.parse(pdf_bytes).pages}

    def parse_pages(self, pdf_bytes: bytes, pages: Sequence[int], *, ocr: bool) -> dict[int, list[LayoutBlock]]:
        # liteparse rejects an empty target_pages rather than reading it as "no pages".
        if not pages:
            return {}

        blocks = self._blocks(pdf_bytes, pages, ocr=ocr)

        # Stripping compares pages, so it also eats a table header repeated on each of them.
        table_pages = [page for page, found in blocks.items() if any(b.kind == "table" for b in found)]
        if len(pages) > 1 and table_pages:
            unstripped = self._blocks(pdf_bytes, table_pages, ocr=ocr, keep_headers_footers=True)
            for page, found in unstripped.items():
                blocks[page] = [restore_stripped_rows(block, found) for block in blocks[page]]

        return {
            page: [mapped for block in found if (mapped := to_layout_block(block))] for page, found in blocks.items()
        }


__all__ = ["LiteParseParser", "restore_stripped_rows", "to_layout_block"]
