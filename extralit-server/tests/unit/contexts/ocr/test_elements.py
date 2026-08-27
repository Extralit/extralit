"""Tests for the typed element view of `items` rows."""

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size

from extralit_server.contexts.ocr.arrow import item_rows, table_html
from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    new_document,
)
from extralit_server.contexts.ocr.elements import FIGURE, MARKDOWN, TABLE, elements_from_items
from extralit_server.contexts.ocr.tables import make_cell

DOCUMENT_ID = "11111111-2222-3333-4444-555555555555"


def bbox(t: float, b: float, left: float = 10.0, right: float = 100.0) -> BoundingBox:
    return BoundingBox(l=left, t=t, r=right, b=b, coord_origin=CoordOrigin.TOPLEFT)


def row(label, reading_order, **overrides):
    base = {
        "self_ref": f"#/texts/{reading_order}",
        "label": label,
        "level": None,
        "reading_order": reading_order,
        "prov_index": 0,
        "page_no": 1,
        "bbox": [0.0, 0.0, 10.0, 10.0],
        "text": None,
        "html": None,
        "charspan_start": None,
        "charspan_end": None,
    }
    base.update(overrides)
    return base


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

        elements = elements_from_items(rows)

        assert [e.headings for e in elements] == [
            ("A Paper",),
            ("A Paper", "Methods"),
            ("A Paper", "Methods", "Sampling"),
            ("A Paper", "Methods", "Sampling"),
            # Results closes Methods and Sampling but never the title.
            ("A Paper", "Results"),
            ("A Paper", "Results"),
        ]

    def test_a_heading_carries_itself_so_a_chunk_knows_its_own_path(self):
        rows = [row(DocItemLabel.SECTION_HEADER, 0, level=1, text="Methods")]

        assert elements_from_items(rows)[0].headings == ("Methods",)


class TestMarkdownRendering:
    @pytest.mark.parametrize(
        "label, level, text, expected",
        [
            (DocItemLabel.TITLE, None, "A Paper", "# A Paper"),
            (DocItemLabel.SECTION_HEADER, 3, "Deep", "### Deep"),
            (DocItemLabel.SECTION_HEADER, None, "Unlevelled", "# Unlevelled"),
            (DocItemLabel.LIST_ITEM, None, "first", "- first"),
            (DocItemLabel.TEXT, None, "Prose.", "Prose."),
        ],
    )
    def test_rows_render_as_the_markdown_the_chunker_rules_expect(self, label, level, text, expected):
        elements = elements_from_items([row(label, 0, level=level, text=text)])

        assert elements[0].type == MARKDOWN
        assert elements[0].content == expected

    def test_heading_level_is_clamped_to_six(self):
        elements = elements_from_items([row(DocItemLabel.SECTION_HEADER, 0, level=99, text="Deep")])

        assert elements[0].content == "###### Deep"


class TestCaptions:
    def test_a_caption_is_absorbed_by_its_figure_rather_than_left_as_prose(self):
        rows = [
            row(DocItemLabel.PICTURE, 0),
            row(DocItemLabel.CAPTION, 1, text="Figure 1. A red square."),
        ]

        elements = elements_from_items(rows)

        assert [(e.type, e.content) for e in elements] == [(FIGURE, "Figure 1. A red square.")]

    def test_a_caption_preceding_its_table_is_absorbed_and_kept(self):
        rows = [
            row(DocItemLabel.CAPTION, 0, text="Table 1. Counts."),
            row(DocItemLabel.TABLE, 1, html="<table><tbody><tr><td>x</td></tr></tbody></table>"),
        ]

        elements = elements_from_items(rows)

        assert [e.type for e in elements] == [TABLE]
        # Consumed from the markdown stream, so the table has to carry it or it is lost.
        assert elements[0].content == (
            "<table><caption>Table 1. Counts.</caption><tbody><tr><td>x</td></tr></tbody></table>"
        )

    def test_a_table_caption_lands_where_html_allows_a_caption(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html="<table><thead><tr><th>N</th></tr></thead></table>"),
            row(DocItemLabel.CAPTION, 1, text="Table 2. Sizes."),
        ]

        content = elements_from_items(rows)[0].content

        # <caption> is only valid as the first child of <table>.
        assert content.startswith("<table><caption>Table 2. Sizes.</caption><thead>")

    def test_a_table_caption_is_escaped(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html="<table><tbody><tr><td>x</td></tr></tbody></table>"),
            row(DocItemLabel.CAPTION, 1, text="Risk & spread <n=42>"),
        ]

        content = elements_from_items(rows)[0].content

        assert "<caption>Risk &amp; spread &lt;n=42&gt;</caption>" in content

    def test_a_caption_survives_a_table_that_produced_no_markup(self):
        rows = [
            row(DocItemLabel.TABLE, 0, html=None),
            row(DocItemLabel.CAPTION, 1, text="Table 3. Unparsed."),
        ]

        elements = elements_from_items(rows)

        assert [(e.type, e.content) for e in elements] == [(TABLE, "Table 3. Unparsed.")]

    def test_a_caption_on_a_page_with_no_figure_survives_as_prose(self):
        rows = [
            row(DocItemLabel.PICTURE, 0, page_no=2),
            row(DocItemLabel.CAPTION, 1, page_no=1, text="Orphaned."),
        ]

        elements = elements_from_items(rows)

        assert [(e.type, e.content) for e in elements] == [(MARKDOWN, "Orphaned.")]

    def test_an_uncaptioned_figure_yields_nothing_retrievable(self):
        assert elements_from_items([row(DocItemLabel.PICTURE, 0)]) == []


class TestProvenance:
    def test_running_headers_and_footers_are_dropped(self):
        rows = [
            row(DocItemLabel.PAGE_HEADER, 0, text="Journal of Things"),
            row(DocItemLabel.TEXT, 1, text="Real body."),
            row(DocItemLabel.PAGE_FOOTER, 2, text="7"),
        ]

        assert [e.content for e in elements_from_items(rows)] == ["Real body."]

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

        elements = elements_from_items(spanning)

        assert [(e.page_no, e.content) for e in elements] == [(1, "first half"), (2, "second half")]

    def test_elements_come_back_in_reading_order_whatever_the_row_order(self):
        rows = [row(DocItemLabel.TEXT, 2, text="third"), row(DocItemLabel.TEXT, 0, text="first")]

        assert [e.content for e in elements_from_items(rows)] == ["first", "third"]

    def test_bbox_and_item_ref_survive_the_round_trip(self):
        elements = elements_from_items([row(DocItemLabel.TEXT, 0, text="x", bbox=[1.0, 2.0, 3.0, 4.0])])

        assert elements[0].bbox == (1.0, 2.0, 3.0, 4.0)
        assert elements[0].item_ref == "#/texts/0"


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

        elements = elements_from_items(item_rows(document, DOCUMENT_ID))

        assert [e.type for e in elements] == [MARKDOWN, MARKDOWN, TABLE]
        assert all(e.headings == ("Methods",) for e in elements)
        assert "<thead>" in elements[-1].content
