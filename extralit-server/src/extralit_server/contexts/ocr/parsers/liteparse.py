"""liteparse layout parser: OCR-routed pages, and digital pages when pymupdf is not installed.

Block and cell rects are natively top-left in 72-DPI page points, so nothing is flipped here.
"""

from __future__ import annotations

import bisect
import itertools
import logging
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
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


def _contains(rect: liteparse.AnnotationRect, item: liteparse.TextItem) -> bool:
    x, y = item.x + item.width / 2, item.y + item.height / 2
    return rect.x <= x <= rect.x + rect.width and rect.y <= y <= rect.y + rect.height


def _union(rects: Sequence[liteparse.AnnotationRect]) -> liteparse.AnnotationRect:
    left, top = min(r.x for r in rects), min(r.y for r in rects)
    right, bottom = max(r.x + r.width for r in rects), max(r.y + r.height for r in rects)
    return liteparse.AnnotationRect(x=left, y=top, width=right - left, height=bottom - top)


def restore_stripped_header(
    block: liteparse.LayoutBlock, page_blocks: Sequence[liteparse.LayoutBlock], items: Sequence[liteparse.TextItem]
) -> liteparse.LayoutBlock:
    """Rebuild a header that stripping removed from `blocks`; `text_items` still hold its words.

    Stripping treats a header repeated on each page as furniture. Words count as that header
    only if they sit one line above the body, in no other block, across at least two columns.
    """
    if block.kind != "table" or block.header or block.bbox is None:
        return block

    body = list(itertools.dropwhile(lambda row: not any(c.text.strip() for c in row), block.rows or []))
    rects = [cell.bbox for cell in body[0]] if body else []
    if len(rects) < 2 or None in rects:
        return block

    lefts = [rect.x for rect in rects]
    top = min(rect.y for rect in rects)
    others = [b.bbox for b in page_blocks if b is not block and b.bbox]

    columns: dict[int, list[liteparse.TextItem]] = defaultdict(list)
    for item in items:
        above_body = item.y + item.height <= top + 1 and item.y + 2 * item.height >= top
        over_table = item.x < block.bbox.x + block.bbox.width and item.x + item.width > block.bbox.x
        if item.text.strip() and above_body and over_table and not any(_contains(rect, item) for rect in others):
            column = bisect.bisect_right(lefts, item.x + item.width / 2) - 1
            columns[max(column, 0)].append(item)
    if len(columns) < 2:
        return block

    header = []
    for index in range(len(rects)):
        words = sorted(columns.get(index, []), key=lambda item: item.x)
        boxes = [liteparse.AnnotationRect(x=w.x, y=w.y, width=w.width, height=w.height) for w in words]
        header.append(
            liteparse.LayoutCell(text=" ".join(w.text.strip() for w in words), bbox=_union(boxes) if boxes else None)
        )

    bbox = _union([block.bbox, *(cell.bbox for cell in header if cell.bbox)])
    return replace(block, header=header, rows=body, bbox=bbox)


def _table_cells(block: liteparse.LayoutBlock) -> list[TableCell]:
    """`header` is not repeated in `rows`, so it becomes row 0 and the body shifts down."""
    grid = [block.header, *(block.rows or [])] if block.header else (block.rows or [])
    return [
        make_cell(
            cell.text.strip(),
            row=row_index,
            col=col_index,
            column_header=bool(block.header) and row_index == 0,
            bbox=_bbox(cell.bbox) if cell.bbox else None,
        )
        for row_index, row in enumerate(grid)
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

    def parse_pages(self, pdf_bytes: bytes, pages: Sequence[int], *, ocr: bool) -> dict[int, list[LayoutBlock]]:
        # liteparse rejects an empty target_pages rather than reading it as "no pages".
        if not pages:
            return {}

        engine = liteparse.LiteParse(
            ocr_enabled=ocr,
            extract_blocks=True,
            target_pages=",".join(str(page) for page in pages),
            num_workers=self._num_workers,
            # True fuses running titles onto body paragraphs; see restore_stripped_header for the cost of False.
            keep_headers_footers=False,
            quiet=True,
        )
        return {
            page.page_num: [
                mapped
                for block in page.blocks or []
                if (mapped := to_layout_block(restore_stripped_header(block, page.blocks, page.text_items)))
            ]
            for page in engine.parse(pdf_bytes).pages
        }


__all__ = ["LiteParseParser", "restore_stripped_header", "to_layout_block"]
