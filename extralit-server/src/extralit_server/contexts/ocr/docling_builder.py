"""Shared seam between layout parsers and `DoclingDocument`.

Parsers normalize whatever their backend produces into `LayoutBlock`s; everything after that
— reading order, provenance, containment dedup — happens here, once, for every parser.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

import xxhash
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
from docling_core.types.doc.document import DocumentOrigin, FloatingItem, NodeItem, PictureItem, TableItem

PDF_MIMETYPE = "application/pdf"

#: Fraction of a text block that must fall inside a table/picture for it to count as duplicated.
CONTAINMENT_THRESHOLD = 0.6

#: Share of the cell text under a block that the block's own words must account for to count as a duplicate.
CELL_SHARE_THRESHOLD = 0.5

#: Labels routed to `add_table` / `add_picture` rather than `add_text`.
TABLE_LABELS = frozenset({DocItemLabel.TABLE, DocItemLabel.DOCUMENT_INDEX})
PICTURE_LABELS = frozenset({DocItemLabel.PICTURE, DocItemLabel.CHART})

#: Captions and footnotes legitimately overlap their figure, so containment must not drop them.
CONTAINMENT_EXEMPT_LABELS = frozenset({DocItemLabel.CAPTION, DocItemLabel.FOOTNOTE})

#: How far either side of a caption its figure or table may sit, nearest first, before after.
CAPTION_REACH = (-1, 1, -2, 2)


@dataclass(frozen=True)
class LayoutBlock:
    """One parser-agnostic layout element, already in top-left page points."""

    label: DocItemLabel
    bbox: BoundingBox
    text: str = ""
    level: Optional[int] = None
    cells: Optional[list[TableCell]] = None
    image: Optional[ImageRef] = None
    marker: Optional[str] = None
    enumerated: bool = False


@dataclass(frozen=True)
class PageContext:
    """The page a batch of blocks belongs to, and the geometry needed to place them."""

    page_no: int
    size: Size

    @property
    def height(self) -> float:
        """Page height in points."""
        return self.size.height

    @property
    def width(self) -> float:
        """Page width in points."""
        return self.size.width


def content_hash(pdf_bytes: bytes) -> int:
    """Fill `DocumentOrigin.binary_hash`. `hash()` is salted per process, so it cannot be used."""
    return xxhash.xxh3_64_intdigest(pdf_bytes)


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


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _carries_text(block_words: list[str], container: LayoutBlock, box: BoundingBox, ctx: PageContext) -> bool:
    """Whether the cells under `box` hold this block's words and little else.

    A cell much longer than the block is a false table swallowing prose, so the block is kept.
    Cells without a bbox count only if they share a word with the block.
    """

    block_set = set(block_words)

    def touches(cell: TableCell) -> bool:
        if cell.bbox is None:
            return not block_set.isdisjoint(_tokens(cell.text))
        return box.intersection_over_self(clamp_to_page(flip_to_top_left(cell.bbox, ctx.height), ctx)) > 0

    under = [cell for cell in container.cells or [] if touches(cell)]
    cell_words = [w for cell in under for w in _tokens(cell.text)]
    if not cell_words:
        return False
    known = set(cell_words)
    covered = sum(w in known for w in block_words) / len(block_words)
    return covered >= CONTAINMENT_THRESHOLD and len(block_words) >= CELL_SHARE_THRESHOLD * len(cell_words)


def is_contained(block: LayoutBlock, bbox: BoundingBox, containers: Sequence[LayoutBlock], ctx: PageContext) -> bool:
    """Whether `block` duplicates a table or picture on its page.

    The bbox must be mostly inside the container; for a table the block's words must also be
    what the cells under it hold, so a false table over real prose or a row it missed drops nothing.
    """
    words = _tokens(block.text)
    for container in containers:
        container_box = clamp_to_page(flip_to_top_left(container.bbox, ctx.height), ctx)
        if bbox.intersection_over_self(container_box) < CONTAINMENT_THRESHOLD:
            continue
        if container.label in PICTURE_LABELS or not words:
            return True
        if _carries_text(words, container, bbox, ctx):
            return True
    return False


def _page_of(item: NodeItem) -> Optional[int]:
    provs = getattr(item, "prov", None) or []
    return provs[0].page_no if provs else None


def link_captions(doc: DoclingDocument) -> None:
    """Attach each unlinked caption to the nearest table or picture on its page, looking back first.

    docling serializes a linked caption inside its owner and nowhere else, so this is what keeps a
    caption out of the prose stream and inside the table or figure that it names.
    """
    body = [ref.resolve(doc) for ref in doc.body.children]
    linked = {ref.cref for item in body if isinstance(item, FloatingItem) for ref in item.captions}
    for index, item in enumerate(body):
        if getattr(item, "label", None) != DocItemLabel.CAPTION or item.self_ref in linked:
            continue
        for offset in CAPTION_REACH:
            owner = body[index + offset] if 0 <= index + offset < len(body) else None
            if isinstance(owner, (TableItem, PictureItem)) and _page_of(owner) == _page_of(item):
                owner.captions.append(item.get_ref())
                break


def append_blocks(
    doc: DoclingDocument,
    ctx: PageContext,
    blocks: Sequence[LayoutBlock],
) -> list[NodeItem]:
    """Add one page's blocks in the order given, dropping text a table or picture already carries."""
    from extralit_server.contexts.ocr.figures import add_picture_block
    from extralit_server.contexts.ocr.tables import add_table_block
    from extralit_server.contexts.ocr.text import add_text_block

    register_page(doc, ctx)
    containers = [b for b in blocks if b.label in TABLE_LABELS or b.label in PICTURE_LABELS]

    added: list[NodeItem] = []
    for block in blocks:
        if block.label in TABLE_LABELS:
            added.append(add_table_block(doc, block, ctx))
        elif block.label in PICTURE_LABELS:
            added.append(add_picture_block(doc, block, ctx))
        elif (item := add_text_block(doc, block, ctx, containers=containers)) is not None:
            added.append(item)

    link_captions(doc)
    return added
