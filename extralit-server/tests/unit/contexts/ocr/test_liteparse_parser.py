"""Tests for the liteparse page parser. Always runs — liteparse is a required dep."""

from pathlib import Path

import liteparse
import pytest
from docling_core.types.doc import CoordOrigin, DocItemLabel, Size

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata
from extralit_server.contexts.ocr.parsers.liteparse import LiteParseParser, restore_stripped_header, to_layout_block
from extralit_server.contexts.ocr.parsers.service import ParserService, build_document

FIXTURES = Path(__file__).parents[3] / "fixtures" / "pdf"
RECT = liteparse.AnnotationRect(x=72.0, y=100.0, width=200.0, height=20.0)
PAGE = Size(width=612.0, height=792.0)


def _cell(text: str, bbox=RECT) -> liteparse.LayoutCell:
    return liteparse.LayoutCell(text=text, bbox=bbox)


@pytest.fixture(scope="module")
def two_page_bytes() -> bytes:
    return (FIXTURES / "two_page.pdf").read_bytes()


@pytest.fixture(scope="module")
def sample_bytes() -> bytes:
    return (FIXTURES / "sample.pdf").read_bytes()


@pytest.fixture(scope="module")
def two_page(two_page_bytes):
    return LiteParseParser().parse_pages(two_page_bytes, [1, 2], ocr=False)


class TestToLayoutBlock:
    @pytest.mark.parametrize(
        ("kind", "label"),
        [
            ("heading", DocItemLabel.SECTION_HEADER),
            ("paragraph", DocItemLabel.TEXT),
            ("list_item", DocItemLabel.LIST_ITEM),
            ("table", DocItemLabel.TABLE),
            ("figure", DocItemLabel.PICTURE),
        ],
    )
    def test_kind_maps_to_label(self, kind, label):
        assert to_layout_block(liteparse.LayoutBlock(kind=kind, text="x", bbox=RECT)).label == label

    def test_rect_becomes_top_left_bbox(self):
        bbox = to_layout_block(liteparse.LayoutBlock(kind="paragraph", text="x", bbox=RECT)).bbox
        assert (bbox.l, bbox.t, bbox.r, bbox.b) == (72.0, 100.0, 272.0, 120.0)
        assert bbox.coord_origin == CoordOrigin.TOPLEFT

    def test_heading_keeps_its_level(self):
        assert to_layout_block(liteparse.LayoutBlock(kind="heading", text="x", level=2, bbox=RECT)).level == 2

    def test_list_depth_is_not_a_heading_level(self):
        block = to_layout_block(liteparse.LayoutBlock(kind="list_item", text="x", level=2, bbox=RECT))
        assert block.label == DocItemLabel.LIST_ITEM
        assert block.level is None

    @pytest.mark.parametrize(("kind", "label"), [("code", DocItemLabel.CODE), ("grid_fallback", DocItemLabel.TEXT)])
    def test_line_based_kinds_keep_their_lines(self, kind, label):
        block = to_layout_block(liteparse.LayoutBlock(kind=kind, lines=["a = 1", "b = 2"], bbox=RECT))
        assert block.label == label
        assert block.text == "a = 1\nb = 2"

    @pytest.mark.parametrize(
        "block",
        [
            liteparse.LayoutBlock(kind="rule", bbox=RECT),
            liteparse.LayoutBlock(kind="paragraph", text="x", bbox=None),
            liteparse.LayoutBlock(kind="new_kind", text="x", bbox=RECT),
        ],
    )
    def test_unplaceable_blocks_are_dropped(self, block):
        assert to_layout_block(block) is None

    def test_heading_text_is_raw(self):
        block = liteparse.LayoutBlock(kind="heading", text="Adageba1,2*, Kanmiki", level=1, bbox=RECT)
        assert to_layout_block(block).text == "Adageba1,2*, Kanmiki"

    def test_code_lines_are_verbatim(self):
        block = liteparse.LayoutBlock(kind="code", lines=["a = b ** 2"], bbox=RECT)
        assert to_layout_block(block).text == "a = b ** 2"

    def test_table_cell_text_is_raw(self):
        block = liteparse.LayoutBlock(kind="table", rows=[[_cell("0.39*")]], bbox=RECT)
        assert to_layout_block(block).cells[0].text == "0.39*"

    @pytest.mark.parametrize(("marker", "ordered"), [("1.", True), ("-", None)])
    def test_list_marker_is_carried(self, marker, ordered):
        block = liteparse.LayoutBlock(kind="list_item", text="x", marker=marker, ordered=ordered, bbox=RECT)
        mapped = to_layout_block(block)
        assert mapped.marker == marker
        assert mapped.enumerated is bool(ordered)

    def test_header_row_comes_first_and_is_marked(self):
        block = liteparse.LayoutBlock(
            kind="table", header=[_cell("Group"), _cell("N")], rows=[[_cell("control"), _cell("42")]], bbox=RECT
        )
        cells = to_layout_block(block).cells
        assert [(c.text, c.start_row_offset_idx, c.start_col_offset_idx, c.column_header) for c in cells] == [
            ("Group", 0, 0, True),
            ("N", 0, 1, True),
            ("control", 1, 0, False),
            ("42", 1, 1, False),
        ]

    def test_table_without_header_has_no_header_cells(self):
        block = liteparse.LayoutBlock(kind="table", rows=[[_cell("control")]], bbox=RECT)
        assert not to_layout_block(block).cells[0].column_header

    def test_padding_cell_has_no_bbox(self):
        block = liteparse.LayoutBlock(kind="table", rows=[[_cell("a"), _cell("", bbox=None)]], bbox=RECT)
        cells = to_layout_block(block).cells
        assert cells[0].bbox is not None
        assert cells[1].bbox is None


class TestParsePages:
    def test_blocks_are_keyed_by_page(self, two_page):
        assert sorted(two_page) == [1, 2]

    def test_first_page_kinds(self, two_page):
        assert [block.label for block in two_page[1]] == [
            DocItemLabel.SECTION_HEADER,
            DocItemLabel.TEXT,
            *[DocItemLabel.LIST_ITEM] * 4,
        ]
        assert two_page[1][0].text == "Results of the Survey"
        assert two_page[1][0].level == 1

    def test_second_page_kinds(self, two_page):
        assert [block.label for block in two_page[2]] == [
            DocItemLabel.TABLE,
            DocItemLabel.PICTURE,
            DocItemLabel.TEXT,
        ]

    def test_bboxes_are_top_left(self, two_page):
        heading = two_page[1][0].bbox
        assert heading.coord_origin == CoordOrigin.TOPLEFT
        assert heading.t < heading.b < 100

    def test_table_cells(self, two_page):
        table = two_page[2][0]
        assert table.cells[0].text == "Species"
        assert [c.text for c in table.cells if c.column_header] == ["Species", "Count", "Mean"]
        assert (table.cells[-1].text, table.cells[-1].start_row_offset_idx) == ("1.9", 3)
        assert all(c.bbox is not None for c in table.cells)

    def test_page_subset_keeps_absolute_page_numbers(self, two_page_bytes):
        assert list(LiteParseParser().parse_pages(two_page_bytes, [2], ocr=False)) == [2]

    def test_no_pages_skips_parsing(self, two_page_bytes):
        assert LiteParseParser().parse_pages(two_page_bytes, [], ocr=False) == {}

    @pytest.mark.parametrize("ocr", [True, False])
    def test_arguments_reach_liteparse(self, monkeypatch, ocr):
        calls = []

        class FakeEngine:
            def __init__(self, **kwargs):
                calls.append(kwargs)

            def parse(self, data):
                return liteparse.ParseResult(pages=[], text="")

        monkeypatch.setattr(liteparse, "LiteParse", FakeEngine)
        LiteParseParser(num_workers=2).parse_pages(b"%PDF", [1, 3], ocr=ocr)

        assert len(calls) == 1
        assert calls[0]["ocr_enabled"] is ocr
        assert calls[0]["extract_blocks"] is True
        assert calls[0]["target_pages"] == "1,3"
        assert calls[0]["num_workers"] == 2
        assert calls[0]["keep_headers_footers"] is False


@pytest.fixture(scope="module")
def service() -> ParserService:
    # Real triage calls sample.pdf scanned, and OCR needs tessdata, which CI does not install.
    return ParserService(
        parsers={"liteparse": LiteParseParser()},
        triage=lambda _: TriageMetadata(pdf_type="text_based", page_count=1),
    )


@pytest.fixture(scope="module")
def document(service, sample_bytes):
    return service.parse(sample_bytes, service.plan(sample_bytes), name="sample", filename="sample.pdf")


def _word(text: str, x: float, y: float = 82.0, width: float = 30.0) -> liteparse.TextItem:
    return liteparse.TextItem(text=text, x=x, y=y, width=width, height=12.0)


def _body(y: float = 99.0) -> liteparse.LayoutBlock:
    rects = [liteparse.AnnotationRect(x=x, y=y, width=20.0, height=12.0) for x in (72.0, 220.0)]
    row = [liteparse.LayoutCell(text="12", bbox=rect) for rect in rects]
    bbox = liteparse.AnnotationRect(x=72.0, y=y, width=168.0, height=12.0)
    return liteparse.LayoutBlock(kind="table", rows=[row], bbox=bbox)


def _table(rows: list[list[str]], header: list[str] | None = None) -> liteparse.LayoutBlock:
    return liteparse.LayoutBlock(
        kind="table",
        header=[_cell(text) for text in header] if header else None,
        rows=[[_cell(text) for text in row] for row in rows],
        bbox=RECT,
    )


class TestRestoreStrippedHeader:
    def test_words_above_the_body_become_the_header(self):
        block = _body()
        restored = restore_stripped_header(block, [block], [_word("Species", 72.0), _word("Count", 220.0)])
        assert [cell.text for cell in restored.header] == ["Species", "Count"]
        assert restored.bbox.y == 82.0
        assert restored.bbox.height == 29.0

    def test_two_words_in_one_column_join(self):
        block = _body()
        words = [_word("Mean", 104.0, width=20.0), _word("Species", 72.0), _word("Count", 220.0)]
        assert [c.text for c in restore_stripped_header(block, [block], words).header] == ["Species Mean", "Count"]

    def test_single_column_line_such_as_a_caption_is_ignored(self):
        block = _body()
        assert restore_stripped_header(block, [block], [_word("Table 1. A caption", 72.0)]) is block

    def test_words_further_up_the_page_are_ignored(self):
        block = _body()
        words = [_word("Journal", 72.0, y=33.0), _word("Volume", 220.0, y=33.0)]
        assert restore_stripped_header(block, [block], words) is block

    def test_words_outside_the_table_width_are_ignored(self):
        block = _body()
        words = [_word("Fig", 400.0), _word("Species", 72.0)]
        assert restore_stripped_header(block, [block], words) is block

    def test_words_placed_in_another_block_are_ignored(self):
        block = _body()
        rect = liteparse.AnnotationRect(x=60.0, y=80.0, width=300.0, height=16.0)
        paragraph = liteparse.LayoutBlock(kind="paragraph", text="Species Count", bbox=rect)
        words = [_word("Species", 72.0), _word("Count", 220.0)]
        assert restore_stripped_header(block, [paragraph, block], words) is block

    def test_blank_row_left_by_stripping_is_replaced(self):
        block = _body()
        blank = [liteparse.LayoutCell(text="", bbox=cell.bbox) for cell in block.rows[0]]
        ruled = liteparse.LayoutBlock(kind="table", rows=[blank, *_body(y=99.0).rows], bbox=block.bbox)
        restored = restore_stripped_header(ruled, [ruled], [_word("Species", 72.0), _word("Count", 220.0)])
        assert len(restored.rows) == 1
        assert [cell.text for cell in restored.header] == ["Species", "Count"]

    def test_detected_header_is_kept(self):
        block = _table([["a", "b"]], header=["Group", "N"])
        assert restore_stripped_header(block, [block], [_word("x", 72.0), _word("y", 220.0)]) is block

    def test_non_table_is_unchanged(self):
        block = liteparse.LayoutBlock(kind="paragraph", text="x", bbox=RECT)
        assert restore_stripped_header(block, [block], [_word("x", 72.0), _word("y", 220.0)]) is block


class TestRepeatedHeader:
    @pytest.fixture(scope="class")
    def pages(self):
        pdf_bytes = (FIXTURES / "repeated_header.pdf").read_bytes()
        return LiteParseParser().parse_pages(pdf_bytes, [1, 2, 3], ocr=False)

    @pytest.mark.parametrize("page", [1, 2, 3])
    def test_every_page_keeps_its_column_labels(self, pages, page):
        (table,) = [block for block in pages[page] if block.label == DocItemLabel.TABLE]
        assert [c.text for c in table.cells if c.column_header] == ["Species", "Count", "Mean"]

    def test_body_rows_are_not_duplicated(self, pages):
        (table,) = [block for block in pages[2] if block.label == DocItemLabel.TABLE]
        assert max(c.start_row_offset_idx for c in table.cells) == 6

    def test_running_title_stays_stripped(self, pages):
        assert not [block for found in pages.values() for block in found if "Journal of Layout" in block.text]


class TestListItems:
    @pytest.fixture(scope="class")
    def document(self, two_page):
        return build_document(two_page, page_sizes={1: PAGE, 2: PAGE}, name="two_page")

    def test_markers_reach_the_document(self, document):
        items = [(item.marker, item.enumerated) for item in document.texts if item.label == DocItemLabel.LIST_ITEM]
        assert items == [("1.", True), ("2.", True), ("-", False), ("-", False)]

    def test_numbers_survive_markdown_export(self, document):
        markdown = document.export_to_markdown()
        assert "1. first site" in markdown
        assert "2. second site" in markdown


class TestParserService:
    def test_plan_falls_back_to_liteparse_without_ocr(self, service, sample_bytes):
        plan = service.plan(sample_bytes)
        assert plan.pages_by_parser == {"liteparse": [1]}
        assert plan.ocr_pages == []

    def test_every_item_has_provenance(self, document):
        items = [item for item, _ in document.iterate_items()]
        assert items
        assert all(item.prov and item.prov[0].page_no == 1 for item in items)

    def test_table_and_figure_survive(self, document):
        assert len(document.tables) == 1
        assert document.tables[0].data.num_rows == 2
        assert len(document.pictures) == 1

    def test_known_gap_structure_is_flat_on_sample(self, document):
        # ENG-84: sample.pdf's title, heading and caption all come back as paragraphs.
        assert {item.label for item in document.texts} == {DocItemLabel.TEXT}
