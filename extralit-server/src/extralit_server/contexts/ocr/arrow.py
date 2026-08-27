"""Columnar projection of a `DoclingDocument`.

One row per `(DocItem, ProvenanceItem)` so an item spanning a page break expands naturally
instead of hiding a second page inside a nested column. Lance-native, so `index/lancedb_engine`
can ingest these tables unchanged for cross-document provenance search.
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any, Optional

import pyarrow as pa
from docling_core.types.doc import DoclingDocument, TableCell
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


def _cell_html(cell: TableCell, in_header: bool) -> str:
    tag = "th" if in_header or cell.column_header or cell.row_header else "td"
    spans = ""
    if cell.col_span > 1:
        spans += f' colspan="{cell.col_span}"'
    if cell.row_span > 1:
        spans += f' rowspan="{cell.row_span}"'
    return f"<{tag}{spans}>{html.escape(cell.text or '', quote=False)}</{tag}>"


def table_html(item: TableItem) -> Optional[str]:
    """Serialize a table with a real `<thead>`.

    docling's own exporter puts the header's `<th>` cells inside `<tbody>`, which leaves the
    header unliftable — and a table split into row windows has to repeat it on every chunk.
    """
    cells = list(getattr(item.data, "table_cells", None) or [])
    if not cells:
        return None

    by_row: dict[int, list[TableCell]] = defaultdict(list)
    for cell in cells:
        by_row[cell.start_row_offset_idx].append(cell)
    rows = [sorted(by_row[index], key=lambda c: c.start_col_offset_idx) for index in sorted(by_row)]

    # Only a leading run of all-header rows is a header; a stray `column_header` further down
    # is a mislabelled body cell, not the start of a second one.
    header_rows = 0
    for row in rows:
        if not all(cell.column_header for cell in row):
            break
        header_rows += 1

    def section(tag: str, group: list[list[TableCell]], in_header: bool) -> str:
        if not group:
            return ""
        body = "".join("<tr>" + "".join(_cell_html(c, in_header) for c in row) + "</tr>" for row in group)
        return f"<{tag}>{body}</{tag}>"

    head = section("thead", rows[:header_rows], True)
    body = section("tbody", rows[header_rows:], False)
    return f"<table>{head}{body}</table>"


def _table_html(doc: DoclingDocument, item: DocItem) -> Optional[str]:
    if not isinstance(item, TableItem):
        return None
    try:
        return table_html(item)
    except Exception:  # a malformed table must not sink the whole projection
        return None


def item_rows(doc: DoclingDocument, document_id: str) -> list[dict[str, Any]]:
    """Flatten every item's provenance into rows matching `ITEM_SCHEMA`."""
    rows: list[dict[str, Any]] = []

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
