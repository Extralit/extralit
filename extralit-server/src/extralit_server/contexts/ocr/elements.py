"""Typed view of the layout store's `items` rows, one step below chunking.

`arrow.item_rows` flattens a `DoclingDocument` into columns; this reads those columns back as
the three units a chunker dispatches on — a markdown run, a table, or a figure with its caption
— so `contexts/retrieval` never has to know a docling label. Rows are the only input, which is
what lets chunking re-run from the Lance dataset without re-parsing the PDF.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Optional

from docling_core.types.doc import DocItemLabel

from extralit_server.contexts.ocr.docling_builder import PICTURE_LABELS, TABLE_LABELS

MARKDOWN = "markdown"
TABLE = "table"
FIGURE = "figure"

#: Running page furniture: repeated on every page, retrievable on none of them.
SKIPPED_LABELS = frozenset({DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER})

#: Headings open a breadcrumb slot. A title sits above every section header, whatever its level.
TITLE_SLOT = 0

_MAX_HEADING_LEVEL = 6


@dataclass(frozen=True)
class Element:
    """One retrievable unit, carrying the provenance a hit needs to point back at the page."""

    type: str
    content: str
    page_no: Optional[int]
    bbox: Optional[tuple[float, float, float, float]]
    label: str
    level: Optional[int]
    item_ref: str
    reading_order: int
    headings: tuple[str, ...] = ()


def _text_of(row: Mapping, siblings: int) -> str:
    """A row's own text, sliced to its provenance when one item spans several of them."""
    text = row.get("text") or ""
    if siblings < 2:
        return text
    start, end = row.get("charspan_start"), row.get("charspan_end")
    if start is None or end is None or end <= start:
        return text
    return text[start:end]


def _markdown(label: str, text: str, level: Optional[int]) -> str:
    """Render a row as the markdown the recursive chunker's rules are written against."""
    if label == DocItemLabel.TITLE:
        return f"# {text}"
    if label == DocItemLabel.SECTION_HEADER:
        return "#" * min(max(level or 1, 1), _MAX_HEADING_LEVEL) + f" {text}"
    if label == DocItemLabel.LIST_ITEM:
        return f"- {text}"
    if label == DocItemLabel.CODE:
        return f"```\n{text}\n```"
    return text


def _heading_slot(label: str, level: Optional[int]) -> Optional[int]:
    if label == DocItemLabel.TITLE:
        return TITLE_SLOT
    if label == DocItemLabel.SECTION_HEADER:
        return max(level or 1, 1)
    return None


def _push_heading(stack: list[tuple[int, str]], slot: int, text: str) -> None:
    """Open a breadcrumb slot, closing every slot at or below it."""
    while stack and stack[-1][0] >= slot:
        stack.pop()
    stack.append((slot, text))


def _bbox_of(row: Mapping) -> Optional[tuple[float, float, float, float]]:
    bbox = row.get("bbox")
    return tuple(float(v) for v in bbox) if bbox else None  # ty: ignore[invalid-return-type]


def _captionable(rows: Sequence[Mapping], index: int) -> Optional[int]:
    """Index of the figure or table a caption at `index` belongs to.

    docling puts a caption after its figure, but parsers that sort geometrically can put it
    either side, so the nearer neighbour on the same page wins.
    """
    page = rows[index].get("page_no")
    best: Optional[tuple[int, int]] = None
    for offset in (-1, 1, -2, 2):
        neighbour = index + offset
        if not 0 <= neighbour < len(rows):
            continue
        row = rows[neighbour]
        if row.get("page_no") != page:
            continue
        if row.get("label") in TABLE_LABELS or row.get("label") in PICTURE_LABELS:
            distance = abs(offset)
            if best is None or distance < best[0]:
                best = (distance, neighbour)
    return best[1] if best else None


def elements_from_items(rows: Iterable[Mapping]) -> list[Element]:
    """Read `items` rows back into elements, in reading order.

    One element per row, so an item spanning a page break stays two elements with two bboxes
    rather than one element that claims to be in two places.
    """
    ordered = sorted(rows, key=lambda r: (r.get("reading_order") or 0, r.get("prov_index") or 0))
    provs: dict[str, int] = {}
    for row in ordered:
        provs[row.get("self_ref")] = provs.get(row.get("self_ref"), 0) + 1

    # Captions are consumed by the figure or table they describe, so resolve them first.
    captions: dict[int, str] = {}
    consumed: set[int] = set()
    for index, row in enumerate(ordered):
        if row.get("label") != DocItemLabel.CAPTION:
            continue
        owner = _captionable(ordered, index)
        if owner is None:
            continue
        text = _text_of(row, provs.get(row.get("self_ref"), 1)).strip()
        if not text:
            continue
        captions[owner] = f"{captions[owner]} {text}" if owner in captions else text
        consumed.add(index)

    elements: list[Element] = []
    stack: list[tuple[int, str]] = []

    for index, row in enumerate(ordered):
        label = row.get("label") or DocItemLabel.TEXT
        if label in SKIPPED_LABELS or index in consumed:
            continue

        level = row.get("level")
        text = _text_of(row, provs.get(row.get("self_ref"), 1)).strip()

        slot = _heading_slot(label, level)
        if slot is not None and text:
            _push_heading(stack, slot, text)

        if label in TABLE_LABELS:
            kind, content = TABLE, (row.get("html") or "")
        elif label in PICTURE_LABELS:
            kind, content = FIGURE, captions.get(index, "")
        else:
            kind, content = MARKDOWN, _markdown(label, text, level) if text else ""

        if not content:
            continue

        elements.append(
            Element(
                type=kind,
                content=content,
                page_no=row.get("page_no"),
                bbox=_bbox_of(row),
                label=str(label),
                level=level,
                item_ref=row.get("self_ref"),
                reading_order=row.get("reading_order") or 0,
                headings=tuple(heading for _, heading in stack),
            )
        )

    return elements
