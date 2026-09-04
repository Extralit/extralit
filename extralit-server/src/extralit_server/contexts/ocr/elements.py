"""Typed view of the layout store's `items` rows, one step below chunking.

`arrow.item_rows` flattens a `DoclingDocument` into columns; this reads those columns back as
the three units a chunker dispatches on — a markdown run, a table, or a figure with its caption
— so `contexts/retrieval` never has to know a docling label. Rows in, rows out: chunking re-runs
from the Lance dataset without re-parsing the PDF.

Rendering is docling's, done once at projection time into the `markdown` column. What this adds
is the heading breadcrumb, as window functions over the `items` columns, so a whole workspace is
projected in the same columnar pass as a single document.
"""

from __future__ import annotations

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

#: The deepest breadcrumb slot; anything deeper is nested under the same ancestor anyway.
MAX_HEADING_LEVEL = 6

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


def _labels(labels: frozenset[DocItemLabel]) -> str:
    """A label set as a SQL `IN` list. Enum values only — nothing here is caller input."""
    return "(" + ", ".join(f"'{label.value}'" for label in sorted(labels)) + ")"


def elements_sql(source: str = "items") -> str:
    """The projection, as one statement over anything DuckDB can scan with the `items` columns."""
    slots = range(TITLE_SLOT, MAX_HEADING_LEVEL + 1)
    # Per slot: the latest heading opened there, and the depth of the latest heading at or above
    # it. The slot is still in scope only while those coincide.
    breadcrumb = ",\n        ".join(
        f"last_value(CASE WHEN slot = {s} THEN own_text END IGNORE NULLS) OVER running AS heading_{s},\n        "
        f"last_value(CASE WHEN slot <= {s} THEN slot END IGNORE NULLS) OVER running AS newest_{s}"
        for s in slots
    )
    headings = ", ".join(f"CASE WHEN newest_{s} = {s} THEN heading_{s} END" for s in slots)
    # Python's `str.strip`; DuckDB's bare `trim` takes spaces off and leaves newlines behind.
    strip = r"regexp_replace({}, '^\s+|\s+$', '', 'g')"

    return f"""
WITH sliced AS (
    SELECT * EXCLUDE (label),
        coalesce(label, '{DocItemLabel.TEXT.value}') AS label,
        row_number() OVER (PARTITION BY document_id ORDER BY reading_order, prov_index) AS ord,
        -- A charspan short of the whole text is one page's share of an item that spans a break.
        coalesce(charspan_start > 0 OR charspan_end < length(text), false) AS partial,
        {strip.format("CASE WHEN partial THEN text[charspan_start + 1 : charspan_end] ELSE coalesce(text, '') END")}
            AS own_text,
        -- Markdown is rendered per item, so a partial row falls back to its share of the raw text.
        CASE
            WHEN markdown = '' THEN ''
            WHEN partial OR markdown IS NULL THEN own_text
            ELSE {strip.format("markdown")}
        END AS content,
        CASE
            WHEN own_text = '' THEN NULL
            WHEN label = '{DocItemLabel.TITLE.value}' THEN {TITLE_SLOT}
            WHEN label = '{DocItemLabel.SECTION_HEADER.value}'
                THEN least(greatest(coalesce(level, 1), 1), {MAX_HEADING_LEVEL})
        END AS slot
    FROM {source}
),
breadcrumbs AS (
    SELECT *,
        {breadcrumb}
    FROM sliced
    WINDOW running AS (
        PARTITION BY document_id ORDER BY ord ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )
)
SELECT
    document_id,
    CASE
        WHEN label IN {_labels(TABLE_LABELS)} THEN '{TABLE}'
        WHEN label IN {_labels(PICTURE_LABELS)} THEN '{FIGURE}'
        ELSE '{MARKDOWN}'
    END AS type,
    content, page_no, bbox, label, level, self_ref AS item_ref, reading_order,
    list_filter([{headings}], heading -> heading IS NOT NULL) AS headings,
    newest_{MAX_HEADING_LEVEL} AS heading_level
FROM breadcrumbs
WHERE label NOT IN {_labels(SKIPPED_LABELS)} AND content <> ''
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
