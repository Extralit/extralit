"""Tests for the pymupdf layout parser. Opt-in — pymupdf4llm is an AGPL extra."""

from pathlib import Path

import pytest
from docling_core.types.doc import CoordOrigin, DocItemLabel

pytest.importorskip("pymupdf4llm")

from extralit_server.contexts.ocr.parsers.pymupdf import parse
from extralit_server.contexts.ocr.parsers.registry import get_parser, list_parsers

FIXTURES = Path(__file__).parents[3] / "fixtures" / "pdf"
PAGE_WIDTH, PAGE_HEIGHT = 612.0, 792.0


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return (FIXTURES / "sample.pdf").read_bytes()


@pytest.fixture(scope="module")
def doc(pdf_bytes):
    return parse(pdf_bytes, name="sample")


class TestRegistry:
    def test_pymupdf_is_registered_when_the_extra_is_installed(self):
        assert "pymupdf" in list_parsers()

    def test_get_parser_resolves_it(self, pdf_bytes):
        assert get_parser("pymupdf")(pdf_bytes, name="sample").name == "sample"


class TestGeometry:
    def test_page_size_comes_from_the_page_rect(self, doc):
        assert doc.pages[1].size.width == pytest.approx(PAGE_WIDTH)
        assert doc.pages[1].size.height == pytest.approx(PAGE_HEIGHT)

    def test_coordinates_are_top_left_with_no_flip(self, doc):
        title = next(t for t in doc.texts if "Study of Layout" in t.text)

        assert title.prov[0].bbox.coord_origin == CoordOrigin.TOPLEFT
        # pymupdf is natively top-left, so the title keeps its ~52.7pt top directly.
        assert title.prov[0].bbox.t == pytest.approx(52.7, abs=1.0)

    def test_page_numbers_are_one_indexed(self, doc):
        assert {p.page_no for t in doc.texts for p in t.prov} == {1}

    def test_every_bbox_stays_inside_the_page(self, doc):
        for item, _ in doc.iterate_items(with_groups=False):
            for prov in item.prov:
                assert 0 <= prov.bbox.l <= prov.bbox.r <= PAGE_WIDTH
                assert 0 <= prov.bbox.t <= prov.bbox.b <= PAGE_HEIGHT

    def test_reading_order_runs_down_the_page(self, doc):
        tops = [i.prov[0].bbox.t for i, _ in doc.iterate_items(with_groups=False)]

        assert tops == sorted(tops)


class TestHeadings:
    def test_font_size_ranking_yields_heading_levels(self, doc):
        title = next(t for t in doc.texts if "Study of Layout" in t.text)
        methods = next(t for t in doc.texts if t.text == "Methods")

        assert title.label == DocItemLabel.SECTION_HEADER
        assert (title.level, methods.level) == (1, 2)

    def test_body_text_is_not_promoted(self, doc):
        body = next(t for t in doc.texts if "two parsers" in t.text)

        assert body.label == DocItemLabel.TEXT
        # Plain text items carry no level at all — only headings do.
        assert not hasattr(body, "level")


class TestTables:
    def test_a_table_is_detected(self, doc):
        assert len(doc.tables) == 1

    def test_cell_offsets_are_exclusive_and_span_the_grid(self, doc):
        data = doc.tables[0].data

        assert (data.num_rows, data.num_cols) == (2, 2)
        for cell in data.table_cells:
            assert cell.end_row_offset_idx == cell.start_row_offset_idx + cell.row_span
            assert cell.end_col_offset_idx == cell.start_col_offset_idx + cell.col_span

    def test_cell_text_is_recovered(self, doc):
        assert {c.text for c in doc.tables[0].data.table_cells} == {"Group", "N", "control", "42"}

    def test_header_row_is_flagged(self, doc):
        header = [c for c in doc.tables[0].data.table_cells if c.start_row_offset_idx == 0]

        assert all(c.column_header for c in header)

    def test_every_cell_carries_its_own_bbox(self, doc):
        # Per-cell geometry is the reason pymupdf is the higher-fidelity parser.
        for cell in doc.tables[0].data.table_cells:
            assert cell.bbox is not None
            assert cell.bbox.coord_origin == CoordOrigin.TOPLEFT
            assert cell.bbox.r > cell.bbox.l

    def test_cell_bboxes_sit_inside_the_table_bbox(self, doc):
        table_bbox = doc.tables[0].prov[0].bbox

        for cell in doc.tables[0].data.table_cells:
            assert cell.bbox.intersection_over_self(table_bbox) == pytest.approx(1.0, abs=0.01)

    def test_table_html_round_trips(self, doc):
        html = doc.tables[0].export_to_html(doc=doc)

        assert "<th>Group</th>" in html
        assert "<td>42</td>" in html

    def test_table_text_is_not_duplicated_as_body_text(self, doc):
        assert not any(t.text in {"Group", "N", "control", "42", "Group N", "control 42"} for t in doc.texts)


class TestPictures:
    def test_image_blocks_become_pictures(self, doc):
        assert len(doc.pictures) == 1

    def test_picture_bbox_matches_the_drawn_rect(self, doc):
        bbox = doc.pictures[0].prov[0].bbox

        assert (bbox.l, bbox.t, bbox.r, bbox.b) == pytest.approx((72.0, 322.0, 192.0, 412.0), abs=1.0)


class TestPageSelection:
    def test_pages_filter_restricts_output(self, pdf_bytes):
        doc = parse(pdf_bytes, name="sample", pages=[2])

        assert doc.texts == []
        assert 1 not in doc.pages


class TestParserAgreement:
    def test_both_parsers_agree_on_page_geometry(self, pdf_bytes):
        from extralit_server.contexts.ocr.parsers.pdf_inspector import parse as parse_pi

        other = parse_pi(pdf_bytes, name="sample")
        mine = parse(pdf_bytes, name="sample")

        assert set(mine.pages) == set(other.pages)
        for page_no, page in mine.pages.items():
            assert page.size.width == pytest.approx(other.pages[page_no].size.width)
            assert page.size.height == pytest.approx(other.pages[page_no].size.height)

    def test_both_parsers_place_the_title_in_the_same_region(self, pdf_bytes):
        from extralit_server.contexts.ocr.parsers.pdf_inspector import parse as parse_pi

        mine = next(t for t in parse(pdf_bytes, name="s").texts if "Study of Layout" in t.text)
        other = next(t for t in parse_pi(pdf_bytes, name="s").texts if "Study of Layout" in t.text)

        assert mine.prov[0].bbox.intersection_over_self(other.prov[0].bbox) > 0.6
