"""Shared seam between layout parsers and `DoclingDocument`.

Parsers normalize whatever their backend produces into `LayoutBlock`s; everything after that
— reading order, provenance, containment dedup — happens here, once, for every parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ImageRef,
    ProvenanceItem,
    Size,
    TableCell,
)
from docling_core.types.doc.document import DocumentOrigin, NodeItem

PDF_MIMETYPE = "application/pdf"

#: Fraction of a text block that must fall inside a table/picture for it to count as duplicated.
CONTAINMENT_THRESHOLD = 0.6

#: Labels routed to `add_table` / `add_picture` rather than `add_text`.
TABLE_LABELS = frozenset({DocItemLabel.TABLE, DocItemLabel.DOCUMENT_INDEX})
PICTURE_LABELS = frozenset({DocItemLabel.PICTURE, DocItemLabel.CHART})

#: Captions and footnotes legitimately overlap their figure, so containment must not drop them.
CONTAINMENT_EXEMPT_LABELS = frozenset({DocItemLabel.CAPTION, DocItemLabel.FOOTNOTE})


@dataclass(frozen=True)
class LayoutBlock:
    """One parser-agnostic layout element, already in top-left page points."""

    label: DocItemLabel
    bbox: BoundingBox
    text: str = ""
    level: Optional[int] = None
    cells: Optional[list[TableCell]] = None
    image: Optional[ImageRef] = None


@dataclass(frozen=True)
class PageContext:
    """The page a batch of blocks belongs to, and the geometry needed to place them."""

    page_no: int
    size: Size

    @property
    def height(self) -> float:
        return self.size.height

    @property
    def width(self) -> float:
        return self.size.width


def new_document(
    name: str,
    *,
    filename: Optional[str] = None,
    binary_hash: Optional[int] = None,
    mimetype: str = PDF_MIMETYPE,
) -> DoclingDocument:
    """Create an empty `DoclingDocument`, recording an origin when the source is identified."""
    origin = None
    if filename is not None:
        origin = DocumentOrigin(mimetype=mimetype, filename=filename, binary_hash=binary_hash or 0)
    return DoclingDocument(name=name, origin=origin)


def register_page(doc: DoclingDocument, ctx: PageContext) -> None:
    """Register the page size. Must happen before any prov is added, or bboxes get clamped to nothing."""
    if ctx.page_no not in doc.pages:
        doc.add_page(page_no=ctx.page_no, size=ctx.size)


def flip_to_top_left(bbox: BoundingBox, page_height: float) -> BoundingBox:
    """Convert a PDF-native bottom-left bbox to docling's top-left convention."""
    if bbox.coord_origin == CoordOrigin.TOPLEFT:
        return bbox
    return bbox.to_top_left_origin(page_height=page_height)


def clamp_to_page(bbox: BoundingBox, ctx: PageContext) -> BoundingBox:
    """Clip a bbox into the page rect. docling only warns on out-of-page boxes, it does not fix them."""
    return BoundingBox(
        l=max(0.0, min(bbox.l, ctx.width)),
        r=max(0.0, min(bbox.r, ctx.width)),
        t=max(0.0, min(bbox.t, ctx.height)),
        b=max(0.0, min(bbox.b, ctx.height)),
        coord_origin=bbox.coord_origin,
    )


def make_prov(ctx: PageContext, bbox: BoundingBox, text: Optional[str]) -> ProvenanceItem:
    """Build the lineage triple. Charspans are item-local, matching docling-eval's adapters."""
    charspan = (0, len(text)) if text else (0, 0)
    return ProvenanceItem(
        page_no=ctx.page_no,
        bbox=clamp_to_page(flip_to_top_left(bbox, ctx.height), ctx),
        charspan=charspan,
    )


def is_contained(
    doc: DoclingDocument,
    bbox: BoundingBox,
    page_no: int,
    threshold: float = CONTAINMENT_THRESHOLD,
) -> bool:
    """Whether `bbox` is mostly swallowed by a table or picture already on this page."""
    for item in [*doc.tables, *doc.pictures]:
        for prov in item.prov:
            if prov.page_no != page_no:
                continue
            if bbox.intersection_over_self(prov.bbox) >= threshold:
                return True
    return False


def _sort_key(doc: DoclingDocument, node: NodeItem) -> tuple[float, float, float]:
    """Position a body child by the earliest provenance anywhere in its subtree."""
    positions = []
    stack = [node]
    while stack:
        current = stack.pop()
        for prov in getattr(current, "prov", []) or []:
            positions.append((float(prov.page_no), prov.bbox.t, prov.bbox.l))
        stack.extend(child.resolve(doc) for child in current.children)
    return min(positions) if positions else (float("inf"),) * 3


def sort_body_by_position(doc: DoclingDocument) -> None:
    """Restore geometric reading order across text, tables and pictures alike.

    The dedup pass has to add tables and pictures first, which leaves them ahead of every
    paragraph in the body; this puts the page back in the order a reader would see it.
    """
    doc.body.children.sort(key=lambda ref: _sort_key(doc, ref.resolve(doc)))


def append_blocks(
    doc: DoclingDocument,
    ctx: PageContext,
    blocks: list[LayoutBlock],
) -> list[NodeItem]:
    """Add one page's blocks, then restore reading order.

    Tables and pictures go in first so the text pass can drop anything they already contain —
    without that ordering the same words land in the document twice, once as a table cell and
    once as a stray paragraph.
    """
    from extralit_server.contexts.ocr.figures import add_picture_block
    from extralit_server.contexts.ocr.tables import add_table_block
    from extralit_server.contexts.ocr.text import add_text_block

    register_page(doc, ctx)

    added: list[NodeItem] = []
    for block in blocks:
        if block.label in TABLE_LABELS:
            added.append(add_table_block(doc, block, ctx))
        elif block.label in PICTURE_LABELS:
            added.append(add_picture_block(doc, block, ctx))

    for block in blocks:
        if block.label in TABLE_LABELS or block.label in PICTURE_LABELS:
            continue
        item = add_text_block(doc, block, ctx)
        if item is not None:
            added.append(item)

    sort_body_by_position(doc)
    return added
