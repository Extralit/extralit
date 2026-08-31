"""Typed view of the layout store's `items` rows, one step below chunking.

`arrow.item_rows` flattens a `DoclingDocument` into columns; this reads those columns back as
the three units a chunker dispatches on — a markdown run, a table, or a figure with its caption
— so `contexts/retrieval` never has to know a docling label. Rows in, rows out: chunking re-runs
from the Lance dataset without re-parsing the PDF.

The whole projection is one DuckDB statement over the `items` columns. Reading breadcrumbs and
captions out row by row would mean pulling every document's text into Python to build strings
that go straight back into Arrow; as SQL it stays columnar, pushes the projection down to Lance,
and does a whole workspace in the same pass as a single document.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

import pyarrow as pa
from docling_core.types.doc import DocItemLabel

from extralit_server.contexts.ocr.docling_builder import PICTURE_LABELS, TABLE_LABELS

if TYPE_CHECKING:
    import duckdb

MARKDOWN = "markdown"
TABLE = "table"
FIGURE = "figure"

#: Running page furniture: repeated on every page, retrievable on none of them.
SKIPPED_LABELS = frozenset({DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER})

#: Headings open a breadcrumb slot. A title sits above every section header, whatever its level.
TITLE_SLOT = 0

#: Both the deepest renderable heading and the deepest breadcrumb slot; `######` has no successor.
MAX_HEADING_LEVEL = 6

#: How far either side of a caption its figure or table may sit, nearest first, before after.
CAPTION_REACH = (-1, 1, -2, 2)

ELEMENT_SCHEMA = pa.schema(
    [
        ("document_id", pa.string()),
        ("type", pa.string()),
        ("content", pa.string()),
        ("page_no", pa.int32()),
        ("bbox", pa.list_(pa.float32(), 4)),
        ("label", pa.string()),
        ("level", pa.int8()),
        ("item_ref", pa.string()),
        ("reading_order", pa.int32()),
        ("headings", pa.list_(pa.string())),
        ("heading_level", pa.int8()),
    ]
)


def _labels(labels: Iterable[DocItemLabel]) -> str:
    """Render a label set as a SQL `IN` list. Enum values only — nothing here is caller input."""
    return "(" + ", ".join(f"'{label.value}'" for label in sorted(labels)) + ")"


#: Python's `str.strip`; DuckDB's bare `trim` takes spaces off and leaves newlines behind.
_STRIP = r"regexp_replace({0}, '^\s+|\s+$', '', 'g')"

_RUNNING = "PARTITION BY document_id ORDER BY ord ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"

_HEADING_LEVEL = f"least(greatest(coalesce(level, 1), 1), {MAX_HEADING_LEVEL})"


def _breadcrumb_columns() -> str:
    """One text and two positions per slot: a slot is in scope only if nothing has closed it."""
    parts = []
    for slot in range(TITLE_SLOT, MAX_HEADING_LEVEL + 1):
        parts += [
            f"last_value(CASE WHEN slot = {slot} THEN own_text END IGNORE NULLS) OVER running AS heading_{slot}",
            f"max(CASE WHEN slot = {slot} THEN ord END) OVER running AS opened_{slot}",
            f"max(CASE WHEN slot <= {slot} THEN ord END) OVER running AS covered_{slot}",
        ]
    return ",\n        ".join(parts)


def _breadcrumb_list() -> str:
    """A slot survives only while the newest heading at or above it is still its own."""
    slots = ", ".join(
        f"CASE WHEN opened_{slot} = covered_{slot} THEN heading_{slot} END"
        for slot in range(TITLE_SLOT, MAX_HEADING_LEVEL + 1)
    )
    return f"list_filter(list_value({slots}), heading -> heading IS NOT NULL)"


def _caption_owner() -> str:
    """The figure or table a caption binds to: nearest on the same page, looking back first."""
    branches = []
    for offset in CAPTION_REACH:
        window, distance = ("lag" if offset < 0 else "lead"), abs(offset)
        neighbour = f"{window}({{0}}, {distance}) OVER document"
        branches.append(
            f"WHEN {neighbour.format('label')} IN {_labels(TABLE_LABELS | PICTURE_LABELS)}"
            f" AND {neighbour.format('page_no')} IS NOT DISTINCT FROM page_no"
            f" THEN {neighbour.format('ord')}"
        )
    return (
        "CASE WHEN label <> 'caption' OR own_text = '' THEN NULL\n            "
        + "\n            ".join(branches)
        + "\n        END"
    )


#: A caption is consumed by its owner, so a table that drops it drops the only prose naming it.
_CAPTION_TAG = (
    "'<caption>' || replace(replace(replace(caption, '&', '&amp;'), '<', '&lt;'), '>', '&gt;') || '</caption>'"
)

_TABLE_CONTENT = f"""CASE
                WHEN coalesce(html, '') = '' THEN coalesce(caption, '')
                WHEN coalesce(caption, '') = '' THEN html
                WHEN starts_with(html, '<table') AND position('>' IN html) > 0
                    THEN substr(html, 1, position('>' IN html)) || {_CAPTION_TAG}
                         || substr(html, position('>' IN html) + 1)
                ELSE {_CAPTION_TAG} || html
            END"""

_CONTENT = f"""CASE
            WHEN label IN {_labels(TABLE_LABELS)} THEN {_TABLE_CONTENT}
            WHEN label IN {_labels(PICTURE_LABELS)} THEN coalesce(caption, '')
            WHEN own_text = '' THEN ''
            WHEN label = '{DocItemLabel.TITLE.value}' THEN '# ' || own_text
            WHEN label = '{DocItemLabel.SECTION_HEADER.value}'
                THEN repeat('#', {_HEADING_LEVEL}) || ' ' || own_text
            WHEN label = '{DocItemLabel.LIST_ITEM.value}' THEN '- ' || own_text
            WHEN label = '{DocItemLabel.CODE.value}' THEN '```' || chr(10) || own_text || chr(10) || '```'
            ELSE own_text
        END"""


def elements_sql(source: str = "items") -> str:
    """The projection, as one statement over anything DuckDB can scan with the `items` columns."""
    return f"""
WITH ordered AS (
    SELECT
        document_id, self_ref, level, reading_order, page_no, bbox, html, text,
        charspan_start, charspan_end,
        coalesce(label, '{DocItemLabel.TEXT.value}') AS label,
        row_number() OVER document AS ord,
        count(*) OVER (PARTITION BY document_id, self_ref) AS provs
    FROM {source}
    WINDOW document AS (PARTITION BY document_id ORDER BY reading_order, prov_index)
),
sliced AS (
    SELECT * EXCLUDE (text, charspan_start, charspan_end, provs),
        {
        _STRIP.format(
            '''CASE
            WHEN provs >= 2 AND charspan_start IS NOT NULL AND charspan_end IS NOT NULL
                 AND charspan_end > charspan_start
            THEN substr(coalesce(text, ''), charspan_start + 1, charspan_end - charspan_start)
            ELSE coalesce(text, '')
        END'''
        )
    } AS own_text
    FROM ordered
),
slotted AS (
    SELECT *,
        CASE
            WHEN own_text = '' THEN NULL
            WHEN label = '{DocItemLabel.TITLE.value}' THEN {TITLE_SLOT}
            WHEN label = '{DocItemLabel.SECTION_HEADER.value}' THEN {_HEADING_LEVEL}
        END AS slot
    FROM sliced
),
breadcrumbs AS (
    SELECT *,
        {_breadcrumb_columns()},
        last_value(slot IGNORE NULLS) OVER running AS heading_level
    FROM slotted
    WINDOW running AS ({_RUNNING})
),
neighbours AS (
    SELECT * EXCLUDE (slot),
        {_breadcrumb_list()} AS headings,
        {_caption_owner()} AS owner_ord
    FROM breadcrumbs
    WINDOW document AS (PARTITION BY document_id ORDER BY ord)
),
captions AS (
    SELECT document_id, owner_ord, string_agg(own_text, ' ' ORDER BY ord) AS caption
    FROM neighbours
    WHERE owner_ord IS NOT NULL
    GROUP BY document_id, owner_ord
),
projected AS (
    SELECT
        element.document_id,
        element.ord,
        CASE
            WHEN label IN {_labels(TABLE_LABELS)} THEN '{TABLE}'
            WHEN label IN {_labels(PICTURE_LABELS)} THEN '{FIGURE}'
            ELSE '{MARKDOWN}'
        END AS type,
        {_CONTENT} AS content,
        element.page_no, element.bbox, element.label, element.level,
        element.self_ref AS item_ref, element.reading_order,
        element.headings, element.heading_level
    FROM neighbours AS element
    LEFT JOIN captions
        ON captions.document_id = element.document_id AND captions.owner_ord = element.ord
    WHERE label NOT IN {_labels(SKIPPED_LABELS)}
      AND element.owner_ord IS NULL
)
SELECT document_id, type, content, page_no, bbox, label, level, item_ref, reading_order,
       headings, heading_level
FROM projected
WHERE content <> ''
ORDER BY document_id, ord
"""


def elements_table(items: Any, *, connection: Optional[duckdb.DuckDBPyConnection] = None) -> pa.Table:
    """Project `items` rows into elements, in reading order, one per provenance row.

    An item spanning a page break stays two elements with two bboxes rather than one element
    claiming to be in two places. `items` is anything DuckDB registers — an Arrow table, a Lance
    dataset — and every document in it is projected in the same pass.
    """
    import duckdb

    own = connection is None
    connection = connection or duckdb.connect()
    try:
        connection.register("_items", items)
        table = connection.execute(elements_sql("_items")).to_arrow_table()
    finally:
        connection.unregister("_items")
        if own:
            connection.close()
    return table.cast(ELEMENT_SCHEMA)
