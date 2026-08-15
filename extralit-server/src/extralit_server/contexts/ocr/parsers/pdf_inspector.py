"""pdf-inspector layout parser (MIT, zero deps, the always-available default).

Three quirks are normalized here and nowhere else:
  1. Page indexing differs across pdf-inspector's own API — `TextItem.page` and
     `StructureElement.page` are 1-indexed, `PdfClassification.pages_needing_ocr` is 0-indexed.
  2. `TextItem.y` is PDF-native bottom-left, so every bbox is flipped to docling's top-left.
  3. It returns no page dimensions at all, so MediaBox is read with pikepdf.
"""

from __future__ import annotations

import io
import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any, Optional

import pdf_inspector
import pikepdf
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, DoclingDocument, Size, TableCell

from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, append_blocks, new_document
from extralit_server.contexts.ocr.tables import make_cell

_LOGGER = logging.getLogger(__name__)

#: Structure-tree roles resolved through /RoleMap, mapped to docling labels.
_ROLE_LABELS: dict[str, tuple[DocItemLabel, Optional[int]]] = {
    "Title": (DocItemLabel.TITLE, None),
    "P": (DocItemLabel.TEXT, None),
    "Table": (DocItemLabel.TABLE, None),
    "Figure": (DocItemLabel.PICTURE, None),
    "Caption": (DocItemLabel.CAPTION, None),
    "LI": (DocItemLabel.LIST_ITEM, None),
    "LBody": (DocItemLabel.LIST_ITEM, None),
    "Formula": (DocItemLabel.FORMULA, None),
    "Code": (DocItemLabel.CODE, None),
}

#: Two spans are on the same line when their baselines agree within this fraction of font size.
_LINE_TOLERANCE = 0.5
#: Consecutive lines join into one paragraph when their vertical gap is under this multiple of size.
_PARAGRAPH_GAP = 1.8
#: A font must exceed the modal body size by this factor before it reads as a heading.
_HEADING_SIZE_RATIO = 1.15


def role_to_label(role: str) -> tuple[DocItemLabel, Optional[int]]:
    """Map a structure-tree role onto a docling label, recovering heading level from H1..H6."""
    if len(role) == 2 and role[0] == "H" and role[1].isdigit():
        return DocItemLabel.SECTION_HEADER, int(role[1])
    return _ROLE_LABELS.get(role, (DocItemLabel.TEXT, None))


def page_sizes(pdf_bytes: bytes) -> dict[int, Size]:
    """Read each page's MediaBox, keyed by docling's 1-indexed page_no."""
    sizes: dict[int, Size] = {}
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            box = [float(v) for v in page.MediaBox]
            width, height = abs(box[2] - box[0]), abs(box[3] - box[1])
            if int(page.get("/Rotate", 0) or 0) % 180 == 90:
                width, height = height, width
            sizes[index] = Size(width=width, height=height)
    return sizes


def classify(pdf_bytes: bytes) -> dict[str, Any]:
    """Cheap classification used to route parsers and to surface scanned pages."""
    result = pdf_inspector.classify_pdf_bytes(pdf_bytes)
    return {
        "page_count": result.page_count,
        "pdf_type": str(result.pdf_type),
        "confidence": result.confidence,
        # classify_pdf reports 0-indexed pages; docling page_no is 1-indexed.
        "pages_needing_ocr": sorted(p + 1 for p in (result.pages_needing_ocr or [])),
    }


def _structure_roles(pdf_bytes: bytes) -> dict[tuple[int, int], str]:
    """Map (page_no, mcid) -> role for tagged PDFs. Untagged files yield an empty map."""
    try:
        elements = pdf_inspector.extract_structure_elements_bytes(pdf_bytes)
    except Exception as e:
        _LOGGER.debug(f"no structure tree available: {e}")
        return {}
    return {(el.page, el.mcid): el.role for el in elements if el.mcid is not None}


def _to_bbox(item: Any) -> BoundingBox:
    """A pdf-inspector item's rect, still in PDF-native bottom-left coordinates."""
    return BoundingBox(
        l=item.x,
        r=item.x + item.width,
        b=item.y,
        t=item.y + item.height,
        coord_origin=CoordOrigin.BOTTOMLEFT,
    )


def _union(bboxes: Sequence[BoundingBox]) -> BoundingBox:
    return BoundingBox(
        l=min(b.l for b in bboxes),
        r=max(b.r for b in bboxes),
        b=min(b.b for b in bboxes),
        t=max(b.t for b in bboxes),
        coord_origin=CoordOrigin.BOTTOMLEFT,
    )


def _body_size(items: Sequence[Any]) -> float:
    """The modal font size, treated as body text when no structure tree says otherwise."""
    sizes = Counter(round(i.font_size, 1) for i in items if i.item_type == "text" and i.font_size)
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _heading_levels(items: Sequence[Any], body_size: float) -> dict[float, int]:
    """Rank the font sizes above body size, largest first, into heading levels 1..N."""
    larger = sorted(
        {
            round(i.font_size, 1)
            for i in items
            if i.item_type == "text" and i.font_size and i.font_size > body_size * _HEADING_SIZE_RATIO
        },
        reverse=True,
    )
    return {size: level for level, size in enumerate(larger, start=1)}


def _group_lines(items: Sequence[Any]) -> list[list[Any]]:
    """Cluster spans sharing a baseline into lines, top of page first."""
    lines: list[list[Any]] = []
    for item in sorted(items, key=lambda i: (-i.y, i.x)):
        tolerance = max(item.font_size, 1.0) * _LINE_TOLERANCE
        if lines and abs(lines[-1][0].y - item.y) <= tolerance:
            lines[-1].append(item)
        else:
            lines.append([item])
    return [sorted(line, key=lambda i: i.x) for line in lines]


def _merge_paragraph(lines: list[list[Any]]) -> list[list[Any]]:
    """Join vertically adjacent lines of the same size into one block."""
    blocks: list[list[Any]] = []
    for line in lines:
        size = max((i.font_size for i in line), default=0.0)
        if blocks:
            previous = blocks[-1]
            prev_size = max((i.font_size for i in previous), default=0.0)
            gap = min(i.y for i in previous) - max(i.y + i.height for i in line)
            if abs(prev_size - size) < 0.5 and 0 <= gap <= size * _PARAGRAPH_GAP:
                previous.extend(line)
                continue
        blocks.append(list(line))
    return blocks


def _line_text(items: Sequence[Any]) -> str:
    return " ".join(i.text.strip() for i in items if i.text and i.text.strip())


def _table_cells(items: Sequence[Any]) -> list[TableCell]:
    """Recover a grid from the spans inside a table region, by row then column position."""
    rows = _group_lines(items)
    if not rows:
        return []

    # Column boundaries come from the distinct left edges seen anywhere in the table.
    starts = sorted({round(i.x) for row in rows for i in row})
    columns: list[float] = []
    for start in starts:
        if not columns or start - columns[-1] > 5:
            columns.append(start)

    cells: list[TableCell] = []
    for row_index, row in enumerate(rows):
        for item in row:
            text = (item.text or "").strip()
            if not text:
                continue
            col_index = max(i for i, c in enumerate(columns) if round(item.x) >= c - 5)
            cells.append(
                make_cell(
                    text,
                    row=row_index,
                    col=col_index,
                    column_header=row_index == 0,
                    bbox=_to_bbox(item),
                )
            )
    return cells


def _blocks_for_page(
    items: Sequence[Any],
    roles: dict[tuple[int, int], str],
    page_no: int,
) -> list[LayoutBlock]:
    """Turn one page's positioned items into ordered layout blocks."""
    blocks: list[LayoutBlock] = []

    images = [i for i in items if i.item_type != "text"]
    text_items = [i for i in items if i.item_type == "text"]

    tagged = [i for i in text_items if i.mcid is not None and (page_no, i.mcid) in roles]
    untagged = [i for i in text_items if i not in tagged]

    for image in images:
        role = roles.get((page_no, image.mcid)) if image.mcid is not None else None
        label = role_to_label(role)[0] if role else DocItemLabel.PICTURE
        blocks.append(LayoutBlock(label=label, bbox=_to_bbox(image)))

    grouped: dict[int, list[Any]] = defaultdict(list)
    for item in tagged:
        grouped[item.mcid].append(item)

    for mcid, group in grouped.items():
        label, level = role_to_label(roles[(page_no, mcid)])
        bbox = _union([_to_bbox(i) for i in group])
        if label == DocItemLabel.TABLE:
            blocks.append(LayoutBlock(label=label, bbox=bbox, cells=_table_cells(group)))
        else:
            blocks.append(LayoutBlock(label=label, bbox=bbox, text=_line_text(group), level=level))

    if untagged:
        body_size = _body_size(untagged)
        levels = _heading_levels(untagged, body_size)
        for group in _merge_paragraph(_group_lines(untagged)):
            size = round(max((i.font_size for i in group), default=0.0), 1)
            level = levels.get(size)
            label = DocItemLabel.SECTION_HEADER if level else DocItemLabel.TEXT
            blocks.append(
                LayoutBlock(
                    label=label,
                    bbox=_union([_to_bbox(i) for i in group]),
                    text=_line_text(group),
                    level=level,
                )
            )

    # Reading order: top of the page down, ties broken left to right (still bottom-left coords).
    blocks.sort(key=lambda b: (-b.bbox.t, b.bbox.l))
    return blocks


def parse(
    pdf_bytes: bytes,
    *,
    name: str,
    pages: Optional[Sequence[int]] = None,
    filename: Optional[str] = None,
) -> DoclingDocument:
    """Parse PDF bytes into a `DoclingDocument`. `pages` is a 1-indexed allowlist."""
    doc = new_document(name, filename=filename, binary_hash=hash(pdf_bytes) & 0xFFFFFFFF)

    sizes = page_sizes(pdf_bytes)
    roles = _structure_roles(pdf_bytes)
    wanted = set(pages) if pages else None

    by_page: dict[int, list[Any]] = defaultdict(list)
    for item in pdf_inspector.extract_text_with_positions_bytes(pdf_bytes):
        by_page[item.page].append(item)

    for page_no in sorted(sizes):
        if wanted is not None and page_no not in wanted:
            continue
        ctx = PageContext(page_no=page_no, size=sizes[page_no])
        append_blocks(doc, ctx, _blocks_for_page(by_page.get(page_no, []), roles, page_no))

    return doc
