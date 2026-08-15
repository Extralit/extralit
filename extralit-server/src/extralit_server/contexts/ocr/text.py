"""Appends a single text `LayoutBlock` to a `DoclingDocument`."""

from __future__ import annotations

from typing import Optional

from docling_core.types.doc import DocItemLabel, DoclingDocument
from docling_core.types.doc.document import NodeItem

from extralit_server.contexts.ocr.docling_builder import (
    CONTAINMENT_EXEMPT_LABELS,
    LayoutBlock,
    PageContext,
    is_contained,
    make_prov,
)


def add_text_block(
    doc: DoclingDocument,
    block: LayoutBlock,
    ctx: PageContext,
    parent: Optional[NodeItem] = None,
) -> Optional[NodeItem]:
    """Add one text block, skipping anything empty or already covered by a table/picture."""
    text = (block.text or "").strip()
    if not text:
        return None

    prov = make_prov(ctx, block.bbox, text)

    if block.label not in CONTAINMENT_EXEMPT_LABELS and is_contained(doc, prov.bbox, ctx.page_no):
        return None

    # add_text dispatches SECTION_HEADER to add_heading but drops the level, so route it here.
    if block.label == DocItemLabel.SECTION_HEADER:
        return doc.add_heading(text=text, level=block.level or 1, prov=prov, parent=parent)

    return doc.add_text(label=block.label, text=text, prov=prov, parent=parent)
