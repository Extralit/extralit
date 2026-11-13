"""Chunking a builder-made DoclingDocument."""

from __future__ import annotations

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size

from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, append_blocks, new_document
from extralit_server.contexts.ocr.tables import make_cell
from extralit_server.contexts.retrieval.chunking import chunk_document

DOC_ID = "6f0c1d2e-0000-4000-8000-000000000001"


def box(top: float, bottom: float) -> BoundingBox:
    return BoundingBox(l=10, t=top, r=200, b=bottom, coord_origin=CoordOrigin.TOPLEFT)


def block(label: DocItemLabel, text: str, top: float, **kwargs) -> LayoutBlock:
    return LayoutBlock(label=label, bbox=box(top, top + 10), text=text, **kwargs)


def table_block(top: float) -> LayoutBlock:
    cells = [
        make_cell("Group", 0, 0, column_header=True),
        make_cell("Mean_val", 0, 1, column_header=True),
        make_cell("control", 1, 0),
        make_cell("1.5", 1, 1),
    ]
    return LayoutBlock(label=DocItemLabel.TABLE, bbox=box(top, top + 40), cells=cells)


def picture_block(top: float) -> LayoutBlock:
    return LayoutBlock(label=DocItemLabel.PICTURE, bbox=box(top, top + 40))


def build(*pages: list[LayoutBlock]):
    doc = new_document("sample")
    for number, blocks in enumerate(pages, start=1):
        append_blocks(doc, PageContext(page_no=number, size=Size(width=612, height=792)), blocks)
    return doc


def rows(doc, document_id=DOC_ID):
    return chunk_document(doc, document_id, "Smith2020").to_pylist()


@pytest.fixture
def paper():
    return build(
        [
            block(DocItemLabel.SECTION_HEADER, "Methods", 10, level=1),
            block(DocItemLabel.PARAGRAPH, "We sampled mice.", 30),
            block(DocItemLabel.SECTION_HEADER, "Design", 50, level=2),
            block(DocItemLabel.LIST_ITEM, "group A", 70),
            block(DocItemLabel.FORMULA, "x=1", 90),
            block(DocItemLabel.CAPTION, "Table 1. Results", 110),
            table_block(130),
            picture_block(200),
            block(DocItemLabel.PAGE_FOOTER, "Page 1 of 9", 780),
        ]
    )


def test_a_page_spanning_item_reports_both_pages():
    doc = build([block(DocItemLabel.PARAGRAPH, "spans", 700)])
    item = doc.texts[0]
    from docling_core.types.doc import ProvenanceItem

    item.prov.append(ProvenanceItem(page_no=2, bbox=box(10, 20), charspan=(0, 5)))

    [chunk] = rows(doc)

    assert (chunk["page_start"], chunk["page_end"]) == (1, 2)


def test_table_and_linked_caption_share_one_chunk(paper):
    [table] = [r for r in rows(paper) if r["kind"] == "table"]

    assert table["item_refs"] == ["#/tables/0", "#/texts/5"]
    assert not [r for r in rows(paper) if r["kind"] == "text" and "Table 1." in r["text"]]


def test_uncaptioned_picture_yields_no_chunk(paper):
    assert not [r for r in rows(paper) if r["kind"] == "figure"]


def test_captioned_picture_is_a_figure_chunk():
    doc = build([picture_block(10), block(DocItemLabel.CAPTION, "Figure 1. A mouse", 60)])

    [chunk] = rows(doc)

    assert chunk["kind"] == "figure"
    assert chunk["text"] == "Figure 1. A mouse"


def test_page_footer_never_becomes_a_chunk(paper):
    assert not [r for r in rows(paper) if "Page 1 of 9" in r["text"]]


def test_unlinked_caption_is_a_text_chunk():
    doc = build([block(DocItemLabel.CAPTION, "Table 2. Orphan", 10)])

    [chunk] = rows(doc)

    assert (chunk["kind"], chunk["text"]) == ("text", "Table 2. Orphan")


def test_rechunking_is_stable(paper):
    assert [r["chunk_id"] for r in rows(paper)] == [r["chunk_id"] for r in rows(paper)]


def test_removing_an_early_item_leaves_other_ids_unchanged():
    full = build([block(DocItemLabel.PARAGRAPH, t, 10 + 20 * i) for i, t in enumerate(["one", "two", "three"])])
    shorter = build([block(DocItemLabel.PARAGRAPH, t, 10 + 20 * i) for i, t in enumerate(["two", "three"])])

    ids = {r["text"]: r["chunk_id"] for r in rows(full)}

    assert {r["text"]: r["chunk_id"] for r in rows(shorter)} == {"two": ids["two"], "three": ids["three"]}


def test_identical_paragraphs_get_distinct_ids():
    doc = build([block(DocItemLabel.PARAGRAPH, "same", 10), block(DocItemLabel.PARAGRAPH, "same", 40)])

    first, second = rows(doc)

    assert first["chunk_id"] != second["chunk_id"]


def test_chunk_ids_depend_on_the_document():
    doc = build([block(DocItemLabel.PARAGRAPH, "same", 10)])

    assert rows(doc)[0]["chunk_id"] != rows(doc, "6f0c1d2e-0000-4000-8000-000000000002")[0]["chunk_id"]


def test_chunk_count_is_body_items_minus_captions_and_uncaptioned_pictures(paper):
    # 7 body items before the footer: paragraph, 2 headings, list item, formula, caption, table, picture.
    body = [item for item, _ in paper.iterate_items(with_groups=False)]
    headings = [i for i in body if i.label == DocItemLabel.SECTION_HEADER]
    linked_captions = 1
    uncaptioned_pictures = 1

    assert len(rows(paper)) == len(body) - len(headings) - linked_captions - uncaptioned_pictures
    assert len(rows(paper)) == 4


def test_table_text_is_a_markdown_table_prefixed_by_its_caption(paper):
    [table] = [r for r in rows(paper) if r["kind"] == "table"]

    lines = table["text"].splitlines()
    assert lines[0] == "Table 1. Results"
    assert lines[2].startswith("| Group")
    assert set(lines[3]) <= set("|- ")
    assert "Mean_val" in table["text"]


def test_embed_text_starts_with_the_breadcrumb(paper):
    by_text = {r["text"]: r for r in rows(paper)}

    assert by_text["We sampled mice."]["headings"] == ["Methods"]
    assert by_text["We sampled mice."]["embed_text"] == "Methods\n\nWe sampled mice."
    assert by_text["- group A"]["headings"] == ["Methods", "Design"]
    assert by_text["- group A"]["embed_text"].startswith("Methods > Design\n\n")


def test_a_sibling_heading_replaces_the_previous_one():
    doc = build(
        [
            block(DocItemLabel.SECTION_HEADER, "A", 10, level=1),
            block(DocItemLabel.SECTION_HEADER, "A1", 30, level=2),
            block(DocItemLabel.SECTION_HEADER, "B", 50, level=1),
            block(DocItemLabel.PARAGRAPH, "body", 70),
        ]
    )

    assert rows(doc)[0]["headings"] == ["B"]


def test_ordinal_follows_reading_order_and_reference_is_denormalised(paper):
    result = rows(paper)

    assert [r["ordinal"] for r in result] == list(range(len(result)))
    assert {r["reference"] for r in result} == {"Smith2020"}
