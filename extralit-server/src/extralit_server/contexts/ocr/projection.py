"""Project a `DoclingDocument` onto the flat wire schema served by the layout route."""

from __future__ import annotations

from collections.abc import Collection
from typing import Optional
from uuid import UUID

from docling_core.types.doc import DoclingDocument

from extralit_server.api.schemas.v1.document.layout import (
    BoundingBoxOut,
    DocumentLayoutOut,
    LayoutItemOut,
    LayoutPageOut,
    ProvenanceOut,
)
from extralit_server.contexts.ocr.arrow import item_rows


def project_layout(
    doc: DoclingDocument,
    document_id: UUID | str,
    pages: Optional[Collection[int]] = None,
    labels: Optional[Collection[str]] = None,
) -> DocumentLayoutOut:
    """Flatten a document, optionally narrowed to some pages or labels.

    Rows come from the same helper the Parquet sidecar uses, so the API and the columnar
    projection can never drift apart.
    """
    document_id = str(document_id)
    wanted_pages = set(pages) if pages else None
    wanted_labels = {label.lower() for label in labels} if labels else None

    grouped: dict[str, LayoutItemOut] = {}
    for row in item_rows(doc, document_id):
        if wanted_labels is not None and (row["label"] or "").lower() not in wanted_labels:
            continue

        page_no = row["page_no"]
        if wanted_pages is not None and page_no not in wanted_pages:
            continue

        item = grouped.get(row["self_ref"])
        if item is None:
            item = LayoutItemOut(
                self_ref=row["self_ref"],
                parent_ref=row["parent_ref"],
                label=row["label"] or "text",
                content_layer=row["content_layer"],
                level=row["level"],
                reading_order=row["reading_order"],
                text=row["text"],
                html=row["html"],
                prov=[],
            )
            grouped[row["self_ref"]] = item

        if page_no is not None and row["bbox"] is not None:
            left, top, right, bottom = row["bbox"]
            item.prov.append(
                ProvenanceOut(
                    page_no=page_no,
                    bbox=BoundingBoxOut(
                        l=left, t=top, r=right, b=bottom, coord_origin=row["coord_origin"] or "TOPLEFT"
                    ),
                    charspan=(row["charspan_start"] or 0, row["charspan_end"] or 0),
                )
            )

    items = sorted(grouped.values(), key=lambda i: i.reading_order)

    page_items = [
        LayoutPageOut(page_no=page_no, width=page.size.width, height=page.size.height)
        for page_no, page in sorted(doc.pages.items())
        if page.size is not None and (wanted_pages is None or page_no in wanted_pages)
    ]

    return DocumentLayoutOut(
        document_id=document_id,
        docling_version=doc.version,
        num_items=len(items),
        num_pages=len(page_items),
        pages=page_items,
        items=items,
    )
