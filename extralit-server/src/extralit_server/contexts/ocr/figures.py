"""Appends a single picture `LayoutBlock` to a `DoclingDocument`."""

from __future__ import annotations

from typing import Optional

from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import NodeItem, PictureItem

from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, make_prov


def add_picture_block(
    doc: DoclingDocument,
    block: LayoutBlock,
    ctx: PageContext,
    parent: Optional[NodeItem] = None,
) -> PictureItem:
    """Add one picture, anchored by its page bbox."""
    prov = make_prov(ctx, block.bbox, text=None)
    return doc.add_picture(prov=prov, image=block.image, parent=parent)
