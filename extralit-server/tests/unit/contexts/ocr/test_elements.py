"""Tests for the columnar element view of `items` rows."""

import pyarrow as pa
import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size

from extralit_server.contexts.ocr.arrow import ITEM_SCHEMA, item_rows, table_html
from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    new_document,
)
from extralit_server.contexts.ocr.elements import (
    ELEMENT_SCHEMA,
    FIGURE,
    MARKDOWN,
    TABLE,
    elements_table,
)
from extralit_server.contexts.ocr.tables import make_cell

DOCUMENT_ID = "11111111-2222-3333-4444-555555555555"


def bbox(t: float, b: float, left: float = 10.0, right: float = 100.0) -> BoundingBox:
    return BoundingBox(l=left, t=t, r=right, b=b, coord_origin=CoordOrigin.TOPLEFT)


def row(label, reading_order, **overrides):
    base = {
        "document_id": DOCUMENT_ID,
        "self_ref": f"#/texts/{reading_order}",
        "parent_ref": None,
        "label": label,
        "content_layer": "body",
        "level": None,
        "reading_order": reading_order,
        "prov_index": 0,
        "page_no": 1,
        "bbox": [0.0, 0.0, 10.0, 10.0],
        "coord_origin": "TOPLEFT",
        "text": None,
        "html": None,
        "charspan_start": None,
        "charspan_end": None,
    }
    base.update(overrides)
    return base


def elements(rows) -> list[dict]:
    """The projection as dicts — assertions read better than Arrow column slices."""
    return elements_table(pa.Table.from_pylist(list(rows), schema=ITEM_SCHEMA)).to_pylist()


class TestSchema:
    def test_the_projection_conforms_to_the_declared_schema(self):
        table = elements_table(pa.Table.from_pylist([row(DocItemLabel.TEXT, 0, text="x")], schema=ITEM_SCHEMA))

        assert table.schema == ELEMENT_SCHEMA

    def test_an_empty_input_yields_an_empty_table_not_an_error(self):
        table = elements_table(pa.Table.from_pylist([], schema=ITEM_SCHEMA))

        assert table.num_rows == 0
        assert table.schema == ELEMENT_SCHEMA


class TestHeadingBreadcrumb:
    def test_breadcrumb_deepens_and_unwinds_with_heading_level(self):
        rows = [
            row(DocItemLabel.TITLE, 0, text="A Paper"),
            row(DocItemLabel.SECTION_HEADER, 1, level=1, text="Methods"),
            row(DocItemLabel.SECTION_HEADER, 2, level=2, text="Sampling"),
            row(DocItemLabel.TEXT, 3, text="Deep body."),
            row(DocItemLabel.SECTION_HEADER, 4, level=1, text="Results"),
            row(DocItemLabel.TEXT, 5, text="Shallow body."),
        ]

        assert [e["headings"] for e in elements(rows)] == [
            ["A Paper"],
            ["A Paper", "Methods"],
            ["A Paper", "Methods", "Sampling"],
            ["A Paper", "Methods", "Sampling"],
            # Results closes Methods and Sampling but never the title.
            ["A Paper", "Results"],
            ["A Paper", "Results"],
        ]

    def test_a_heading_carries_itself_so_a_chunk_knows_its_own_path(self):
        rows = [row(DocItemLabel.SECTION_HEADER, 0, level=1, text="Methods")]

        assert elements(rows)[0]["headings"] == ["Methods"]

    def test_heading_level_tracks_the_deepest_slot_in_scope(self):
        rows = [
            row(DocItemLabel.TITLE, 0, text="A Paper"),
            row(DocItemLabel.SECTION_HEADER, 1, level=2, text="Sampling"),
            row(DocItemLabel.TEXT, 2, text="Body."),
        ]

        assert [e["heading_level"] for e in elements(rows)] == [0, 2, 2]

    def test_prose_before_any_heading_has_no_breadcrumb(self):
        element = elements([row(DocItemLabel.TEXT, 0, text="Orphan.")])[0]
        assert element["headings"] == []
        assert element["heading_level"] is None

    def test_a_blank_heading_opens_no_slot(self):
        rows = [
            row(DocItemLabel.SECTION_HEADER, 0, level=1, text="   "),
            row(DocItemLabel.TEXT, 1, text="Body."),
        ]

        assert [e["headings"] for e in elements(rows)] == [[]]

    def test_levels_past_h6_share_the_deepest_slot(self):
        # Both render as `######`, so nesting one under the other would be a distinction
        # the markdown cannot carry.
        rows = [
            row(DocItemLabel.SECTION_HEADER, 0, level=7, text="Seven"),
            row(DocItemLabel.SECTION_HEADER, 1, level=99, text="Ninety-nine"),
        ]

        assert [e["headings"] for e in elements(rows)] == [["Seven"], ["Ninety-nine"]]


class TestMarkdownRendering:
    @pytest.mark.parametrize(
        "label, level, text, expected",
        [
            (DocItemLabel.TITLE, None, "A Paper", "# A Paper"),
            (DocItemLabel.SECTION_HEADER, 3, "Deep", "### Deep"),
            (DocItemLabel.SECTION_HEADER, None, "Unlevelled", "# Unlevelled"),
            (DocItemLabel.LIST_ITEM, None, "first", "- first"),
            (DocItemLabel.TEXT, None, "Prose.", "Prose."),
            (DocItemLabel.CODE, None, "x = 1", "```\nx = 1\n```"),
        ],
    )
    def test_rows_render_as_the_markdown_the_chunker_rules_expect(self, label, level, text, expected):
        element = elements([row(label, 0, level=level, text=text)])[0]

        assert element["type"] == MARKDOWN
        assert element["content"] == expected

    def test_heading_level_is_clamped_to_six(self):
        assert elements([row(DocItemLabel.SECTION_HEADER, 0, level=99, text="Deep")])[0]["content"] == "###### Deep"

    def test_surrounding_whitespace_is_stripped_including_newlines(self):
        assert elements([row(DocItemLabel.TEXT, 0, text=" \n\tProse.\n ")])[0]["content"] == "Prose."


class TestCaptions:
    def test_a_caption_is_absorbed_by_its_figure_rather_than_left_as_prose(self):
        rows = [
            row(DocItemLabel.PICTURE, 0),
            row(DocItemLabel.CAPTION, 1, text="Figure 1. A red square."),
        ]

        assert [(e["type"], e["content"]) for e in elements(rows)] == [(FIGURE, "Figure 1. A red square.")]

    def test_a_caption_preceding_its_table_is_absorbed_and_kept(self):
        rows = [
            row(DocItemLabel.CAPTION, 0, text="Table 1. Counts."),
            row(DocItemLabel.TABLE, 1, html="<table><tbody><tr><td>x</td></tr></tbody></table>"),
        ]

        found = elements(rows)

        assert [e["type"] for e in found] == [TABLE]
        # Consumed from the markdown stream, so the table has to carry it or it is lost.
        assert found[0]["content"] == (
            "<table><caption>Table 1. Counts.</caption><tbody><tr><td>x</td></tr></tbody></table>"
        )

    def test_a_table_caption_lands_where_html_allows_a_caption(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html="<table><thead><tr><th>N</th></tr></thead></table>"),
            row(DocItemLabel.CAPTION, 1, text="Table 2. Sizes."),
        ]

        # <caption> is only valid as the first child of <table>.
        assert elements(rows)[0]["content"].startswith("<table><caption>Table 2. Sizes.</caption><thead>")

    def test_a_table_caption_is_escaped(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html="<table><tbody><tr><td>x</td></tr></tbody></table>"),
            row(DocItemLabel.CAPTION, 1, text="Risk & spread <n=42>"),
        ]

        assert "<caption>Risk &amp; spread &lt;n=42&gt;</caption>" in elements(rows)[0]["content"]

    def test_a_caption_survives_a_table_that_produced_no_markup(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html=None),
            row(DocItemLabel.CAPTION, 1, text="Table 3. Unparsed."),
        ]

        assert [(e["type"], e["content"]) for e in elements(rows)] == [(TABLE, "Table 3. Unparsed.")]

    def test_a_caption_keeps_markup_that_is_not_a_table_element(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html="not-a-table"),
            row(DocItemLabel.CAPTION, 1, text="Table 4. Odd."),
        ]

        assert elements(rows)[0]["content"] == "<caption>Table 4. Odd.</caption>not-a-table"

    def test_a_caption_on_a_page_with_no_figure_survives_as_prose(self):
        rows = [
            row(DocItemLabel.PICTURE, 0, page_no=2),
            row(DocItemLabel.CAPTION, 1, page_no=1, text="Orphaned."),
        ]

        assert [(e["type"], e["content"]) for e in elements(rows)] == [(MARKDOWN, "Orphaned.")]

    def test_the_nearer_neighbour_wins_when_a_caption_sits_between_two_figures(self):
        rows = [
            row(DocItemLabel.PICTURE, 0),
            row(DocItemLabel.CAPTION, 1, text="Belongs to the first."),
            row(DocItemLabel.TEXT, 2, text="Prose."),
            row(DocItemLabel.PICTURE, 3),
        ]

        found = elements(rows)

        assert [(e["type"], e["content"]) for e in found] == [
            (FIGURE, "Belongs to the first."),
            (MARKDOWN, "Prose."),
        ]

    def test_two_captions_on_one_figure_are_joined(self):
        rows = [
            row(DocItemLabel.CAPTION, 0, text="Figure 1."),
            row(DocItemLabel.PICTURE, 1),
            row(DocItemLabel.CAPTION, 2, text="A red square."),
        ]

        assert [(e["type"], e["content"]) for e in elements(rows)] == [(FIGURE, "Figure 1. A red square.")]

    def test_an_uncaptioned_figure_yields_nothing_retrievable(self):
        assert elements([row(DocItemLabel.PICTURE, 0)]) == []


class TestProvenance:
    def test_running_headers_and_footers_are_dropped(self):
        rows = [
            row(DocItemLabel.PAGE_HEADER, 0, text="Journal of Things"),
            row(DocItemLabel.TEXT, 1, text="Real body."),
            row(DocItemLabel.PAGE_FOOTER, 2, text="7"),
        ]

        assert [e["content"] for e in elements(rows)] == ["Real body."]

    def test_one_element_per_provenance_row_when_an_item_spans_a_page_break(self):
        spanning = [
            row(DocItemLabel.TEXT, 0, page_no=1, text="first half second half", charspan_start=0, charspan_end=11),
            row(
                DocItemLabel.TEXT,
                0,
                page_no=2,
                prov_index=1,
                text="first half second half",
                charspan_start=11,
                charspan_end=22,
            ),
        ]

        assert [(e["page_no"], e["content"]) for e in elements(spanning)] == [(1, "first half"), (2, "second half")]

    def test_elements_come_back_in_reading_order_whatever_the_row_order(self):
        rows = [row(DocItemLabel.TEXT, 2, text="third"), row(DocItemLabel.TEXT, 0, text="first")]

        assert [e["content"] for e in elements(rows)] == ["first", "third"]

    def test_bbox_and_item_ref_survive_the_round_trip(self):
        element = elements([row(DocItemLabel.TEXT, 0, text="x", bbox=[1.0, 2.0, 3.0, 4.0])])[0]

        assert element["bbox"] == [1.0, 2.0, 3.0, 4.0]
        assert element["item_ref"] == "#/texts/0"


class TestManyDocuments:
    def test_documents_are_projected_in_one_pass_without_bleeding_into_each_other(self):
        rows = []
        for document_id in ("aaaa", "bbbb"):
            for base in (
                row(DocItemLabel.SECTION_HEADER, 0, level=1, text=f"{document_id} heading"),
                row(DocItemLabel.TEXT, 1, text=f"{document_id} body"),
            ):
                rows.append({**base, "document_id": document_id})

        found = elements(reversed(rows))

        assert [(e["document_id"], e["headings"]) for e in found] == [
            ("aaaa", ["aaaa heading"]),
            ("aaaa", ["aaaa heading"]),
            ("bbbb", ["bbbb heading"]),
            ("bbbb", ["bbbb heading"]),
        ]

    def test_a_caption_never_binds_across_a_document_boundary(self):
        rows = [
            {**row(DocItemLabel.PICTURE, 0), "document_id": "aaaa"},
            {**row(DocItemLabel.CAPTION, 0, text="Belongs to bbbb."), "document_id": "bbbb"},
        ]

        # The figure stays uncaptioned and drops out; the caption stays prose in its own document.
        assert [(e["document_id"], e["type"], e["content"]) for e in elements(rows)] == [
            ("bbbb", MARKDOWN, "Belongs to bbbb.")
        ]


class TestTableHtml:
    @pytest.fixture
    def table(self):
        document = new_document("sample")
        append_blocks(
            document,
            PageContext(page_no=1, size=Size(width=612, height=792)),
            [
                LayoutBlock(
                    label=DocItemLabel.TABLE,
                    bbox=bbox(t=200, b=400),
                    cells=[
                        make_cell("Group", row=0, col=0, column_header=True),
                        make_cell("N", row=0, col=1, column_header=True),
                        make_cell("control", row=1, col=0),
                        make_cell("4 < 2", row=1, col=1),
                    ],
                )
            ],
        )
        return document.tables[0]

    def test_header_cells_land_in_thead_not_tbody(self, table):
        assert table_html(table) == (
            "<table>"
            "<thead><tr><th>Group</th><th>N</th></tr></thead>"
            "<tbody><tr><td>control</td><td>4 &lt; 2</td></tr></tbody>"
            "</table>"
        )

    def test_docling_own_exporter_would_have_buried_the_header(self, table):
        # The reason this serializer exists: a row-window chunk cannot repeat a header it
        # cannot find, and docling puts the <th> cells inside <tbody>.
        assert "<thead>" not in table.export_to_html()

    def test_spans_are_carried_as_attributes(self):
        document = new_document("sample")
        append_blocks(
            document,
            PageContext(page_no=1, size=Size(width=612, height=792)),
            [
                LayoutBlock(
                    label=DocItemLabel.TABLE,
                    bbox=bbox(t=200, b=400),
                    cells=[
                        make_cell("Both", row=0, col=0, col_span=2, column_header=True),
                        make_cell("tall", row=1, col=0, row_span=2),
                        make_cell("x", row=1, col=1),
                    ],
                )
            ],
        )

        html = table_html(document.tables[0])

        assert '<th colspan="2">Both</th>' in html
        assert '<td rowspan="2">tall</td>' in html

    def test_a_table_with_no_cells_has_no_html(self):
        document = new_document("sample")
        append_blocks(
            document,
            PageContext(page_no=1, size=Size(width=612, height=792)),
            [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=200, b=400), cells=[])],
        )

        assert table_html(document.tables[0]) is None


class TestAgainstRealProjection:
    def test_elements_line_up_with_a_projected_document(self):
        document = new_document("sample")
        append_blocks(
            document,
            PageContext(page_no=1, size=Size(width=612, height=792)),
            [
                LayoutBlock(label=DocItemLabel.SECTION_HEADER, bbox=bbox(t=10, b=40), text="Methods", level=1),
                LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=50, b=70), text="Body text."),
                LayoutBlock(
                    label=DocItemLabel.TABLE,
                    bbox=bbox(t=200, b=400),
                    cells=[make_cell("N", row=0, col=0, column_header=True), make_cell("42", row=1, col=0)],
                ),
            ],
        )

        found = elements(item_rows(document, DOCUMENT_ID))

        assert [e["type"] for e in found] == [MARKDOWN, MARKDOWN, TABLE]
        assert all(e["headings"] == ["Methods"] for e in found)
        assert "<thead>" in found[-1]["content"]
