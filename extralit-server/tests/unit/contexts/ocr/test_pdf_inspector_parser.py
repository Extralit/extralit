"""Tests for the pdf-inspector layout parser. Always runs — pdf-inspector is a required dep."""

from pathlib import Path

import pytest
from docling_core.types.doc import CoordOrigin, DocItemLabel

from extralit_server.contexts.ocr.parsers import get_parser, list_parsers
from extralit_server.contexts.ocr.parsers.pdf_inspector import (
    classify,
    page_sizes,
    parse,
    role_to_label,
)

FIXTURES = Path(__file__).parents[3] / "fixtures" / "pdf"
PAGE_WIDTH, PAGE_HEIGHT = 612.0, 792.0


@pytest.fixture(scope="module")
def untagged_bytes() -> bytes:
    return (FIXTURES / "sample.pdf").read_bytes()


@pytest.fixture(scope="module")
def tagged_bytes() -> bytes:
    return (FIXTURES / "sample_tagged.pdf").read_bytes()


@pytest.fixture(scope="module")
def untagged(untagged_bytes):
    return parse(untagged_bytes, name="sample")


@pytest.fixture(scope="module")
def tagged(tagged_bytes):
    return parse(tagged_bytes, name="sample_tagged")


class TestRegistry:
    def test_pdf_inspector_is_always_registered(self):
        assert "pdf_inspector" in list_parsers()

    def test_get_parser_returns_a_callable(self, untagged_bytes):
        doc = get_parser("pdf_inspector")(untagged_bytes, name="sample")

        assert doc.name == "sample"

    def test_unknown_parser_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            get_parser("nope")


class TestPageSizes:
    def test_reads_mediabox_keyed_by_one_indexed_page_no(self, untagged_bytes):
        sizes = page_sizes(untagged_bytes)

        assert set(sizes) == {1}
        assert sizes[1].width == pytest.approx(PAGE_WIDTH)
        assert sizes[1].height == pytest.approx(PAGE_HEIGHT)

    def test_page_item_size_lands_on_the_document(self, untagged):
        assert untagged.pages[1].size.height == pytest.approx(PAGE_HEIGHT)


class TestCoordinateFlip:
    def test_all_bboxes_are_top_left_origin(self, untagged):
        for item, _ in untagged.iterate_items(with_groups=False):
            for prov in item.prov:
                assert prov.bbox.coord_origin == CoordOrigin.TOPLEFT

    def test_title_sits_near_the_top_of_the_page(self, untagged):
        title = next(t for t in untagged.texts if "Study of Layout" in t.text)

        # Drawn at PDF y=720 on a 792pt page -> ~54..72pt from the top edge.
        assert title.prov[0].bbox.t == pytest.approx(PAGE_HEIGHT - 738, abs=1.0)
        assert title.prov[0].bbox.b == pytest.approx(PAGE_HEIGHT - 720, abs=1.0)

    def test_reading_order_runs_down_the_page(self, untagged):
        tops = [t.prov[0].bbox.t for t in untagged.texts]

        assert tops == sorted(tops)

    def test_every_bbox_stays_inside_the_page(self, untagged):
        for item, _ in untagged.iterate_items(with_groups=False):
            for prov in item.prov:
                assert 0 <= prov.bbox.l <= prov.bbox.r <= PAGE_WIDTH
                assert 0 <= prov.bbox.t <= prov.bbox.b <= PAGE_HEIGHT


class TestTextExtraction:
    def test_body_text_is_captured(self, untagged):
        assert any("two parsers" in t.text for t in untagged.texts)

    def test_page_number_is_one_indexed(self, untagged):
        assert {p.page_no for t in untagged.texts for p in t.prov} == {1}

    def test_images_become_pictures_not_text(self, untagged):
        assert len(untagged.pictures) == 1
        assert not any("[Image:" in t.text for t in untagged.texts)

    def test_provenance_charspan_matches_the_item_text(self, untagged):
        for text_item in untagged.texts:
            assert text_item.prov[0].charspan == (0, len(text_item.text))


class TestRoleMapping:
    @pytest.mark.parametrize(
        ("role", "label", "level"),
        [
            ("H1", DocItemLabel.SECTION_HEADER, 1),
            ("H3", DocItemLabel.SECTION_HEADER, 3),
            ("H6", DocItemLabel.SECTION_HEADER, 6),
            ("P", DocItemLabel.TEXT, None),
            ("Table", DocItemLabel.TABLE, None),
            ("Figure", DocItemLabel.PICTURE, None),
            ("Caption", DocItemLabel.CAPTION, None),
            ("LI", DocItemLabel.LIST_ITEM, None),
            ("Title", DocItemLabel.TITLE, None),
        ],
    )
    def test_known_roles_map_to_labels(self, role, label, level):
        assert role_to_label(role) == (label, level)

    def test_unknown_roles_fall_back_to_plain_text(self):
        assert role_to_label("Sect") == (DocItemLabel.TEXT, None)


class TestTaggedPdf:
    def test_structure_roles_produce_real_heading_levels(self, tagged):
        headings = {t.text: t.level for t in tagged.texts if t.label == DocItemLabel.SECTION_HEADER}

        assert headings["A Study of Layout Extraction"] == 1
        assert headings["Methods"] == 2

    def test_paragraph_role_stays_plain_text(self, tagged):
        body = next(t for t in tagged.texts if "two parsers" in t.text)

        assert body.label == DocItemLabel.TEXT

    def test_table_role_produces_a_table_item(self, tagged):
        assert len(tagged.tables) == 1

    def test_table_cells_are_recovered_geometrically(self, tagged):
        cells = tagged.tables[0].data

        assert cells.num_rows == 2
        assert cells.num_cols == 2
        assert {c.text for c in cells.table_cells} == {"Group", "N", "control", "42"}

    def test_first_table_row_is_marked_as_header(self, tagged):
        header = [c for c in tagged.tables[0].data.table_cells if c.start_row_offset_idx == 0]

        assert all(c.column_header for c in header)
        assert {c.text for c in header} == {"Group", "N"}

    def test_table_text_is_not_duplicated_as_body_text(self, tagged):
        assert not any(t.text in {"Group", "N", "control", "42"} for t in tagged.texts)

    def test_caption_role_survives_containment_dedup(self, tagged):
        assert any(t.label == DocItemLabel.CAPTION and "Figure 1" in t.text for t in tagged.texts)

    def test_figure_role_produces_a_picture(self, tagged):
        assert len(tagged.pictures) == 1


class TestUntaggedHeuristics:
    def test_larger_font_sizes_are_promoted_to_headings(self, untagged):
        title = next(t for t in untagged.texts if "Study of Layout" in t.text)
        body = next(t for t in untagged.texts if "two parsers" in t.text)

        assert title.label == DocItemLabel.SECTION_HEADER
        assert body.label == DocItemLabel.TEXT

    def test_heading_levels_rank_by_descending_font_size(self, untagged):
        title = next(t for t in untagged.texts if "Study of Layout" in t.text)
        methods = next(t for t in untagged.texts if t.text == "Methods")

        assert title.level < methods.level


class TestClassify:
    def test_reports_page_count_and_normalized_ocr_pages(self, untagged_bytes):
        result = classify(untagged_bytes)

        assert result["page_count"] == 1
        # classify_pdf reports 0-indexed pages; we normalize to docling's 1-indexed page_no.
        # `sample.pdf` is a known false positive: any image-bearing page under ~1400 characters
        # is flagged, which is why nothing is skipped on the strength of this list.
        assert result["pages_needing_ocr"] == [1]

    def test_reports_a_pdf_type(self, untagged_bytes):
        assert isinstance(classify(untagged_bytes)["pdf_type"], str)


class TestPageSelection:
    def test_pages_filter_restricts_output(self, untagged_bytes):
        doc = parse(untagged_bytes, name="sample", pages=[2])

        assert doc.texts == []
        assert 1 not in doc.pages
