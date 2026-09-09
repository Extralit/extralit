"""Tests for the DoclingDocument builder seam shared by every layout parser."""

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size, TableCell

from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    flip_to_top_left,
    is_contained,
    make_prov,
    new_document,
    register_page,
)

PAGE_HEIGHT = 792.0
PAGE_WIDTH = 612.0


@pytest.fixture
def doc():
    return new_document("sample")


@pytest.fixture
def ctx():
    return PageContext(page_no=1, size=Size(width=PAGE_WIDTH, height=PAGE_HEIGHT))


def bbox(t: float, b: float, left: float = 10.0, right: float = 100.0) -> BoundingBox:
    return BoundingBox(l=left, t=t, r=right, b=b, coord_origin=CoordOrigin.TOPLEFT)


class TestNewDocument:
    def test_sets_name_and_current_version(self, doc):
        from docling_core.types.doc.document import CURRENT_VERSION

        assert doc.name == "sample"
        assert doc.version == CURRENT_VERSION

    def test_origin_is_recorded_when_given(self):
        doc = new_document("sample", filename="paper.pdf", binary_hash=1234)

        assert doc.origin is not None
        assert doc.origin.filename == "paper.pdf"
        assert doc.origin.mimetype == "application/pdf"


class TestRegisterPage:
    def test_registers_size_under_one_indexed_page_no(self, doc, ctx):
        register_page(doc, ctx)

        assert doc.pages[1].size.width == PAGE_WIDTH
        assert doc.pages[1].size.height == PAGE_HEIGHT

    def test_is_idempotent(self, doc, ctx):
        register_page(doc, ctx)
        register_page(doc, ctx)

        assert len(doc.pages) == 1


class TestFlipToTopLeft:
    def test_bottom_left_origin_is_flipped(self):
        # A box 100pt tall sitting 100pt above the page bottom.
        bl = BoundingBox(l=10, b=100, r=50, t=200, coord_origin=CoordOrigin.BOTTOMLEFT)

        flipped = flip_to_top_left(bl, PAGE_HEIGHT)

        assert flipped.coord_origin == CoordOrigin.TOPLEFT
        assert flipped.t == pytest.approx(PAGE_HEIGHT - 200)
        assert flipped.b == pytest.approx(PAGE_HEIGHT - 100)
        assert (flipped.l, flipped.r) == (10, 50)

    def test_top_left_origin_is_left_alone(self):
        tl = bbox(t=10, b=30)

        assert flip_to_top_left(tl, PAGE_HEIGHT) == tl

    def test_flipped_box_keeps_its_height(self):
        bl = BoundingBox(l=0, b=100, r=10, t=200, coord_origin=CoordOrigin.BOTTOMLEFT)

        flipped = flip_to_top_left(bl, PAGE_HEIGHT)

        assert flipped.height == pytest.approx(bl.height)


class TestMakeProv:
    def test_charspan_covers_the_whole_text(self, ctx):
        prov = make_prov(ctx, bbox(t=10, b=30), text="hello world")

        assert prov.page_no == 1
        assert prov.charspan == (0, len("hello world"))

    def test_charspan_is_zero_for_non_text_items(self, ctx):
        prov = make_prov(ctx, bbox(t=10, b=30), text=None)

        assert prov.charspan == (0, 0)

    def test_bbox_is_clamped_into_the_page(self, ctx):
        prov = make_prov(ctx, bbox(t=10, b=30, left=-50, right=PAGE_WIDTH + 50), text="x")

        assert prov.bbox.l == 0.0
        assert prov.bbox.r == PAGE_WIDTH


class TestIsContained:
    def test_text_inside_an_existing_table_is_contained(self, doc, ctx):
        register_page(doc, ctx)
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=300, left=0, right=500))])

        assert is_contained(doc, bbox(t=150, b=170, left=10, right=200), page_no=1)

    def test_text_outside_every_table_is_not_contained(self, doc, ctx):
        register_page(doc, ctx)
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=300, left=0, right=500))])

        assert not is_contained(doc, bbox(t=400, b=420, left=10, right=200), page_no=1)

    def test_overlap_below_threshold_is_not_contained(self, doc, ctx):
        register_page(doc, ctx)
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=200, left=0, right=100))])

        # Half of this box lies inside the table -> IoSelf 0.5, under the 0.6 default.
        assert not is_contained(doc, bbox(t=150, b=250, left=0, right=100), page_no=1)

    def test_overlap_above_threshold_is_contained(self, doc, ctx):
        register_page(doc, ctx)
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=200, left=0, right=100))])

        # 70% of this box lies inside the table.
        assert is_contained(doc, bbox(t=130, b=230, left=0, right=100), page_no=1)

    def test_containment_is_scoped_to_the_page(self, doc, ctx):
        register_page(doc, ctx)
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=300, left=0, right=500))])

        assert not is_contained(doc, bbox(t=150, b=170, left=10, right=200), page_no=2)

    def test_pictures_also_absorb_text(self, doc, ctx):
        register_page(doc, ctx)
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=300, left=0, right=500))])

        assert is_contained(doc, bbox(t=150, b=170, left=10, right=200), page_no=1)


class TestAppendBlocks:
    def test_tables_and_pictures_are_added_before_text(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="intro"),
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=400, b=500)),
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=600, b=700)),
        ]

        append_blocks(doc, ctx, blocks)

        assert len(doc.tables) == 1
        assert len(doc.pictures) == 1
        assert [t.text for t in doc.texts] == ["intro"]

    def test_reading_order_interleaves_text_tables_and_pictures(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="intro"),
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=200)),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=250, b=270), text="middle"),
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=300, b=400)),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=450, b=470), text="outro"),
        ]

        append_blocks(doc, ctx, blocks)

        refs = [item.self_ref for item, _ in doc.iterate_items(with_groups=False)]
        assert refs == ["#/texts/0", "#/tables/0", "#/texts/1", "#/pictures/0", "#/texts/2"]

    def test_reading_order_is_by_page_then_position(self, doc, ctx):
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=700, b=750))])
        ctx2 = PageContext(page_no=2, size=Size(width=PAGE_WIDTH, height=PAGE_HEIGHT))
        append_blocks(doc, ctx2, [LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="page two top")])

        order = [(i.prov[0].page_no, i.prov[0].bbox.t) for i, _ in doc.iterate_items(with_groups=False)]
        assert order == sorted(order)

    def test_reading_order_of_text_is_preserved(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="first"),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=40, b=60), text="second"),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=70, b=90), text="third"),
        ]

        append_blocks(doc, ctx, blocks)

        assert [t.text for t in doc.texts] == ["first", "second", "third"]

    def test_text_inside_a_table_is_dropped(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=300, left=0, right=500)),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=150, b=170, left=10, right=200), text="cell text"),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=400, b=420), text="body text"),
        ]

        append_blocks(doc, ctx, blocks)

        assert [t.text for t in doc.texts] == ["body text"]

    def test_captions_are_kept_even_when_they_touch_a_figure(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=300, left=0, right=500)),
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=150, b=170, left=10, right=200), text="Figure 1."),
        ]

        append_blocks(doc, ctx, blocks)

        assert [t.text for t in doc.texts] == ["Figure 1."]

    def test_a_caption_is_linked_to_the_figure_it_touches(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=300, left=0, right=500)),
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=310, b=320), text="Figure 1."),
        ]

        append_blocks(doc, ctx, blocks)

        assert doc.pictures[0].caption_text(doc) == "Figure 1."

    def test_a_caption_above_its_table_binds_to_it(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=90, b=99), text="Table 1."),
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=300)),
        ]

        append_blocks(doc, ctx, blocks)

        assert doc.tables[0].caption_text(doc) == "Table 1."

    def test_the_nearer_neighbour_wins_when_a_caption_sits_between_two_figures(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=200)),
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=210, b=220), text="Belongs to the first."),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=230, b=240), text="Prose."),
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=300, b=400)),
        ]

        append_blocks(doc, ctx, blocks)

        assert doc.pictures[0].caption_text(doc) == "Belongs to the first."
        assert doc.pictures[1].captions == []

    def test_a_caption_reaches_past_one_line_of_prose(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=200)),
            LayoutBlock(label=DocItemLabel.FOOTNOTE, bbox=bbox(t=205, b=208), text="a"),
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=210, b=220), text="Figure 1."),
        ]

        append_blocks(doc, ctx, blocks)

        assert doc.pictures[0].caption_text(doc) == "Figure 1."

    def test_two_captions_on_one_figure_are_both_linked(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=90, b=99), text="Figure 1."),
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=200)),
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=210, b=220), text="A red square."),
        ]

        append_blocks(doc, ctx, blocks)

        assert [ref.resolve(doc).text for ref in doc.pictures[0].captions] == ["Figure 1.", "A red square."]

    def test_a_caption_never_binds_across_a_page(self, doc, ctx):
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=700, b=780))])
        page_two = PageContext(page_no=2, size=ctx.size)

        append_blocks(doc, page_two, [LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=10, b=20), text="Orphan.")])

        assert doc.pictures[0].captions == []

    def test_a_second_pass_over_a_page_links_nothing_twice(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=100, b=200)),
            LayoutBlock(label=DocItemLabel.CAPTION, bbox=bbox(t=210, b=220), text="Figure 1."),
        ]
        append_blocks(doc, ctx, blocks)

        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=400, b=420), text="More.")])

        assert len(doc.pictures[0].captions) == 1

    def test_every_item_carries_a_full_provenance_triple(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="hello"),
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=400, b=500)),
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=600, b=700)),
        ]

        append_blocks(doc, ctx, blocks)

        for item, _ in doc.iterate_items(with_groups=False):
            assert len(item.prov) == 1
            prov = item.prov[0]
            assert prov.page_no == 1
            assert prov.bbox.coord_origin == CoordOrigin.TOPLEFT
            assert prov.charspan is not None

    def test_headings_keep_their_level(self, doc, ctx):
        blocks = [LayoutBlock(label=DocItemLabel.SECTION_HEADER, bbox=bbox(t=10, b=30), text="Methods", level=3)]

        append_blocks(doc, ctx, blocks)

        assert doc.texts[0].label == DocItemLabel.SECTION_HEADER
        assert doc.texts[0].level == 3

    def test_titles_become_title_items(self, doc, ctx):
        blocks = [LayoutBlock(label=DocItemLabel.TITLE, bbox=bbox(t=10, b=30), text="A Paper")]

        append_blocks(doc, ctx, blocks)

        assert doc.texts[0].label == DocItemLabel.TITLE

    def test_empty_text_blocks_are_skipped(self, doc, ctx):
        blocks = [
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="   "),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=40, b=60), text="real"),
        ]

        append_blocks(doc, ctx, blocks)

        assert [t.text for t in doc.texts] == ["real"]

    def test_table_cells_are_carried_through(self, doc, ctx):
        cells = [
            TableCell(
                text="h1",
                start_row_offset_idx=0,
                end_row_offset_idx=1,
                start_col_offset_idx=0,
                end_col_offset_idx=1,
                column_header=True,
            ),
            TableCell(
                text="v1",
                start_row_offset_idx=1,
                end_row_offset_idx=2,
                start_col_offset_idx=0,
                end_col_offset_idx=1,
            ),
        ]
        blocks = [LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=100, b=300), cells=cells)]

        append_blocks(doc, ctx, blocks)

        table = doc.tables[0]
        assert table.data.num_rows == 2
        assert table.data.num_cols == 1
        assert table.data.table_cells[0].column_header is True

    def test_appending_a_second_page_extends_the_same_document(self, doc, ctx):
        append_blocks(doc, ctx, [LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="page one")])
        ctx2 = PageContext(page_no=2, size=Size(width=PAGE_WIDTH, height=PAGE_HEIGHT))
        append_blocks(doc, ctx2, [LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="page two")])

        assert [t.prov[0].page_no for t in doc.texts] == [1, 2]
        assert set(doc.pages) == {1, 2}

    def test_document_round_trips_through_json(self, doc, ctx):
        from docling_core.types.doc import DoclingDocument

        append_blocks(
            doc,
            ctx,
            [
                LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="hello"),
                LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=400, b=500)),
            ],
        )

        restored = DoclingDocument.model_validate(doc.model_dump(mode="json"))

        assert restored.texts[0].text == "hello"
        assert restored.tables[0].prov[0].page_no == 1
