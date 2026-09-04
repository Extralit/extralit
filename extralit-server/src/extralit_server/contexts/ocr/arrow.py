"""Columnar projection of a `DoclingDocument`.

One row per `(DocItem, ProvenanceItem)` so an item spanning a page break expands naturally
instead of hiding a second page inside a nested column. Lance-native, so `index/lancedb_engine`
can ingest these tables unchanged for cross-document provenance search.
"""

from __future__ import annotations

from typing import Any, Optional

import pyarrow as pa
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer, MarkdownParams
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocItem, TableItem

ITEM_SCHEMA = pa.schema(
    [
        ("document_id", pa.string()),
        ("self_ref", pa.string()),
        ("parent_ref", pa.string()),
        ("label", pa.dictionary(pa.int8(), pa.string())),
        ("content_layer", pa.dictionary(pa.int8(), pa.string())),
        ("level", pa.int8()),
        ("reading_order", pa.int32()),
        ("prov_index", pa.int16()),
        ("page_no", pa.int32()),
        ("bbox", pa.list_(pa.float32(), 4)),
        ("coord_origin", pa.dictionary(pa.int8(), pa.string())),
        ("charspan_start", pa.int32()),
        ("charspan_end", pa.int32()),
        ("text", pa.string()),
        ("markdown", pa.string()),
        ("html", pa.string()),
    ]
)

PAGE_SCHEMA = pa.schema(
    [
        ("document_id", pa.string()),
        ("page_no", pa.int32()),
        ("width", pa.float32()),
        ("height", pa.float32()),
    ]
)


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return getattr(value, "value", value)


def _table_html(doc: DoclingDocument, item: DocItem) -> Optional[str]:
    if not isinstance(item, TableItem):
        return None
    try:
        return item.export_to_html(doc=doc) or None
    except Exception:  # a malformed table must not sink the whole projection
        return None


def _serialize(serializer: MarkdownDocSerializer, item: DocItem) -> Optional[str]:
    try:
        return serializer.serialize(item=item).text
    except Exception:  # NULL, not '': a row the renderer could not handle is not a blank one
        return None


def item_rows(doc: DoclingDocument, document_id: str) -> list[dict[str, Any]]:
    """Flatten every item's provenance into rows matching `ITEM_SCHEMA`."""
    rows: list[dict[str, Any]] = []
    # Raw characters and no image placeholder: this column feeds a search index, not a reader.
    markdown = MarkdownDocSerializer(
        doc=doc, params=MarkdownParams(escape_html=False, escape_underscores=False, image_placeholder="")
    )

    for reading_order, (item, _level) in enumerate(doc.iterate_items(with_groups=False)):
        base = {
            "document_id": document_id,
            "self_ref": item.self_ref,
            "parent_ref": item.parent.cref if item.parent else None,
            "label": _enum_value(getattr(item, "label", None)),
            "content_layer": _enum_value(getattr(item, "content_layer", None)),
            "level": getattr(item, "level", None),
            "reading_order": reading_order,
            "text": getattr(item, "text", None) or None,
            "markdown": _serialize(markdown, item),
            "html": _table_html(doc, item),
        }

        provs = list(getattr(item, "prov", []) or [])
        if not provs:
            rows.append(
                {
                    **base,
                    "prov_index": 0,
                    "page_no": None,
                    "bbox": None,
                    "coord_origin": None,
                    "charspan_start": None,
                    "charspan_end": None,
                }
            )
            continue

        for prov_index, prov in enumerate(provs):
            rows.append(
                {
                    **base,
                    "prov_index": prov_index,
                    "page_no": prov.page_no,
                    "bbox": [prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b],
                    "coord_origin": _enum_value(prov.bbox.coord_origin),
                    "charspan_start": prov.charspan[0] if prov.charspan else None,
                    "charspan_end": prov.charspan[1] if prov.charspan else None,
                }
            )

    return rows


def items_table(doc: DoclingDocument, document_id: str) -> pa.Table:
    """Project every `(DocItem, ProvenanceItem)` pair into an Arrow table."""
    return pa.Table.from_pylist(item_rows(doc, document_id), schema=ITEM_SCHEMA)


def page_rows(doc: DoclingDocument, document_id: str) -> list[dict[str, Any]]:
    """One row per registered page, carrying the size every bbox is relative to."""
    return [
        {
            "document_id": document_id,
            "page_no": page_no,
            "width": page.size.width if page.size else None,
            "height": page.size.height if page.size else None,
        }
        for page_no, page in sorted(doc.pages.items())
    ]


def pages_table(doc: DoclingDocument, document_id: str) -> pa.Table:
    """Project page geometry into an Arrow table."""
    return pa.Table.from_pylist(page_rows(doc, document_id), schema=PAGE_SCHEMA)
