"""Tests for the columnar element view of `items` rows."""

import pyarrow as pa
import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size

from extralit_server.contexts.ocr.arrow import ITEM_SCHEMA, item_rows
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


def row(label, reading_order, text=None, markdown=None, **overrides):
    """An `items` row. `markdown` defaults to `text`, the way docling renders plain prose."""
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
        "text": text,
        "markdown": text if markdown is None else markdown,
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
        rows = [row(DocItemLabel.SECTION_HEADER, 0, level=1, text="Methods", markdown="## Methods")]

        assert elements(rows)[0]["headings"] == ["Methods"]

    def test_the_breadcrumb_is_the_raw_heading_text_not_its_markdown(self):
        rows = [
            row(DocItemLabel.SECTION_HEADER, 0, level=1, text="Methods", markdown="## Methods"),
            row(DocItemLabel.TEXT, 1, text="Body."),
        ]

        assert [e["headings"] for e in elements(rows)] == [["Methods"], ["Methods"]]

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
            row(DocItemLabel.SECTION_HEADER, 0, level=1, text="   ", markdown=""),
            row(DocItemLabel.TEXT, 1, text="Body."),
        ]

        assert [e["headings"] for e in elements(rows)] == [[]]

    def test_levels_past_h6_share_the_deepest_slot(self):
        rows = [
            row(DocItemLabel.SECTION_HEADER, 0, level=7, text="Seven"),
            row(DocItemLabel.SECTION_HEADER, 1, level=99, text="Ninety-nine"),
        ]

        assert [e["headings"] for e in elements(rows)] == [["Seven"], ["Ninety-nine"]]


class TestContent:
    def test_content_is_the_rendered_markdown_not_the_raw_text(self):
        rows = [row(DocItemLabel.SECTION_HEADER, 0, level=1, text="Methods", markdown="## Methods")]

        element = elements(rows)[0]

        assert element["type"] == MARKDOWN
        assert element["content"] == "## Methods"

    def test_surrounding_whitespace_is_stripped_including_newlines(self):
        assert elements([row(DocItemLabel.TEXT, 0, text=" \n\tProse.\n ")])[0]["content"] == "Prose."

    def test_a_row_rendered_blank_is_dropped(self):
        # A linked caption renders as '' on its own: docling folds it into the table or figure.
        assert elements([row(DocItemLabel.CAPTION, 0, text="Figure 1.", markdown="")]) == []

    def test_a_row_never_rendered_falls_back_to_its_text(self):
        # NULL is a row written before the column existed, or one the renderer could not handle.
        assert elements([row(DocItemLabel.TEXT, 0, text="Old prose.", markdown="")]) == []
        rows = [{**row(DocItemLabel.TEXT, 0, text="Old prose."), "markdown": None}]

        assert [e["content"] for e in elements(rows)] == ["Old prose."]

    def test_tables_and_figures_carry_their_rendering_whatever_their_text(self):
        rows = [
            row(DocItemLabel.TABLE, 0, markdown="Table 1.\n\n| N |\n|---|\n| 1 |"),
            row(DocItemLabel.PICTURE, 1, markdown="Figure 1."),
            row(DocItemLabel.PICTURE, 2, markdown=""),
        ]

        assert [(e["type"], e["content"]) for e in elements(rows)] == [
            (TABLE, "Table 1.\n\n| N |\n|---|\n| 1 |"),
            (FIGURE, "Figure 1."),
        ]


class TestProvenance:
    def test_running_headers_and_footers_are_dropped(self):
        rows = [
            row(DocItemLabel.PAGE_HEADER, 0, text="Journal of Things"),
            row(DocItemLabel.TEXT, 1, text="Real body."),
            row(DocItemLabel.PAGE_FOOTER, 2, text="7"),
        ]

        assert [e["content"] for e in elements(rows)] == ["Real body."]

    def test_one_element_per_provenance_row_when_an_item_spans_a_page_break(self):
        text = "first half second half"
        spanning = [
            row(DocItemLabel.TEXT, 0, page_no=1, text=text, charspan_start=0, charspan_end=11),
            row(DocItemLabel.TEXT, 0, page_no=2, prov_index=1, text=text, charspan_start=11, charspan_end=22),
        ]

        assert [(e["page_no"], e["content"]) for e in elements(spanning)] == [(1, "first half"), (2, "second half")]

    def test_a_page_spanning_heading_keeps_its_slice_and_loses_its_marker(self):
        # Markdown is rendered per item and cannot be sliced by charspan, so the raw slice wins.
        text = "Methods and Materials"
        spanning = [
            row(
                DocItemLabel.SECTION_HEADER,
                0,
                level=1,
                text=text,
                markdown=f"## {text}",
                charspan_start=0,
                charspan_end=7,
            ),
            row(
                DocItemLabel.SECTION_HEADER,
                0,
                level=1,
                page_no=2,
                prov_index=1,
                text=text,
                markdown=f"## {text}",
                charspan_start=7,
                charspan_end=21,
            ),
        ]

        assert [e["content"] for e in elements(spanning)] == ["Methods", "and Materials"]

    def test_a_page_spanning_table_repeats_its_rendering_on_both_pages(self):
        spanning = [
            row(DocItemLabel.TABLE, 0, page_no=1, markdown="| N |", charspan_start=0, charspan_end=0),
            row(DocItemLabel.TABLE, 0, page_no=2, prov_index=1, markdown="| N |", charspan_start=0, charspan_end=0),
        ]

        assert [(e["page_no"], e["content"]) for e in elements(spanning)] == [(1, "| N |"), (2, "| N |")]

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


class TestAgainstRealProjection:
    @pytest.fixture
    def found(self):
        document = new_document("sample")
        append_blocks(
            document,
            PageContext(page_no=1, size=Size(width=612, height=792)),
            [
                LayoutBlock(label=DocItemLabel.TITLE, bbox=bbox(t=1, b=5), text="A Paper"),
                LayoutBlock(label=DocItemLabel.SECTION_HEADER, bbox=bbox(t=10, b=40), text="Methods", level=1),
                LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=50, b=70), text="Body text."),
                LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=190, b=199), text="Table 1. Counts."),
                LayoutBlock(
                    label=DocItemLabel.TABLE,
                    bbox=bbox(t=200, b=400),
                    cells=[make_cell("N", row=0, col=0, column_header=True), make_cell("42", row=1, col=0)],
                ),
                LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=500, b=600)),
                LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=601, b=610), text="Figure 1. A red square."),
                LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=700, b=750)),
            ],
        )
        return elements(item_rows(document, DOCUMENT_ID))

    def test_captions_ride_inside_their_table_and_figure_not_the_prose(self, found):
        assert [e["type"] for e in found] == [MARKDOWN, MARKDOWN, MARKDOWN, TABLE, FIGURE]
        assert found[3]["content"].startswith("Table 1. Counts.\n\n|")
        assert "|-----|" in found[3]["content"] and "42" in found[3]["content"]
        assert found[4]["content"] == "Figure 1. A red square."

    def test_an_uncaptioned_figure_yields_nothing_retrievable(self, found):
        assert sum(e["type"] == FIGURE for e in found) == 1

    def test_docling_reserves_the_top_heading_for_the_title(self, found):
        assert [e["content"] for e in found[:2]] == ["# A Paper", "## Methods"]

    def test_the_breadcrumb_reaches_every_element(self, found):
        assert all(e["headings"] == ["A Paper", "Methods"] for e in found[1:])


class TestTableChunking:
    """chonkie owns the row-window split; pin the behaviour the element design leans on."""

    def test_a_table_split_into_row_windows_repeats_caption_and_header_on_every_chunk(self):
        from chonkie import TableChunker

        document = new_document("sample")
        append_blocks(
            document,
            PageContext(page_no=1, size=Size(width=612, height=792)),
            [
                LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=190, b=199), text="Table 1. Counts."),
                LayoutBlock(
                    label=DocItemLabel.TABLE,
                    bbox=bbox(t=200, b=400),
                    cells=[
                        make_cell("Group", row=0, col=0, column_header=True),
                        make_cell("N", row=0, col=1, column_header=True),
                        *[make_cell(f"g{i}", row=i, col=0) for i in range(1, 7)],
                        *[make_cell(str(i), row=i, col=1) for i in range(1, 7)],
                    ],
                ),
            ],
        )
        content = elements(item_rows(document, DOCUMENT_ID))[0]["content"]

        chunks = [chunk.text for chunk in TableChunker(chunk_size=2)(content)]

        assert len(chunks) > 1
        assert all("Table 1. Counts." in chunk and "| Group" in chunk for chunk in chunks)
        assert "| g6" in chunks[-1] and "| g6" not in chunks[0]
