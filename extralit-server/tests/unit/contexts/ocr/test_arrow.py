"""Tests for the columnar projection of a `DoclingDocument`."""

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, ProvenanceItem, Size

from extralit_server.contexts.ocr.arrow import (
    ITEM_SCHEMA,
    PAGE_SCHEMA,
    items_table,
    pages_table,
)
from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    new_document,
)

DOCUMENT_ID = "11111111-2222-3333-4444-555555555555"


def bbox(t: float, b: float, left: float = 10.0, right: float = 100.0) -> BoundingBox:
    return BoundingBox(l=left, t=t, r=right, b=b, coord_origin=CoordOrigin.TOPLEFT)


def _cells():
    from extralit_server.contexts.ocr.tables import make_cell

    return [
        make_cell("Group", row=0, col=0, column_header=True),
        make_cell("N", row=0, col=1, column_header=True),
        make_cell("control", row=1, col=0),
        make_cell("42", row=1, col=1),
    ]


@pytest.fixture
def doc():
    document = new_document("sample")
    ctx = PageContext(page_no=1, size=Size(width=612, height=792))
    append_blocks(
        document,
        ctx,
        [
            LayoutBlock(label=DocItemLabel.TITLE, bbox=bbox(t=10, b=40), text="A Paper"),
            LayoutBlock(label=DocItemLabel.SECTION_HEADER, bbox=bbox(t=50, b=70), text="Methods", level=2),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=80, b=120), text="Body text here."),
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=200, b=400), cells=_cells()),
            LayoutBlock(label=DocItemLabel.PICTURE, bbox=bbox(t=450, b=600)),
        ],
    )
    ctx2 = PageContext(page_no=2, size=Size(width=612, height=1008))
    append_blocks(document, ctx2, [LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="Page two.")])
    return document


class TestItemsTable:
    def test_schema_matches_exactly(self, doc):
        assert items_table(doc, DOCUMENT_ID).schema.equals(ITEM_SCHEMA)

    def test_row_count_equals_total_provenance_entries(self, doc):
        expected = sum(len(item.prov) for item, _ in doc.iterate_items(with_groups=False))

        assert items_table(doc, DOCUMENT_ID).num_rows == expected

    def test_multi_prov_item_expands_to_multiple_rows(self, doc):
        # A table spanning a page break carries two provenance entries.
        doc.tables[0].prov.append(
            ProvenanceItem(page_no=2, bbox=bbox(t=10, b=90), charspan=(0, 0)),
        )

        table = items_table(doc, DOCUMENT_ID)
        rows = table.filter(pa.compute.equal(table["self_ref"], "#/tables/0")).to_pylist()

        assert [r["prov_index"] for r in rows] == [0, 1]
        assert [r["page_no"] for r in rows] == [1, 2]

    def test_an_item_without_provenance_still_yields_one_row(self):
        document = new_document("sample")
        document.add_text(label=DocItemLabel.TEXT, text="no prov")

        rows = items_table(document, DOCUMENT_ID).to_pylist()

        assert len(rows) == 1
        assert rows[0]["page_no"] is None
        assert rows[0]["bbox"] is None
        assert rows[0]["prov_index"] == 0

    def test_self_ref_is_the_citation_anchor(self, doc):
        refs = items_table(doc, DOCUMENT_ID).column("self_ref").to_pylist()

        assert "#/tables/0" in refs
        assert "#/pictures/0" in refs
        assert all(r.startswith("#/") for r in refs)

    def test_reading_order_is_dense_and_monotonic(self, doc):
        orders = items_table(doc, DOCUMENT_ID).column("reading_order").to_pylist()

        assert orders == sorted(orders)
        assert set(orders) == set(range(len(set(orders))))

    def test_bbox_is_a_fixed_four_float_list(self, doc):
        table = items_table(doc, DOCUMENT_ID)

        assert table.schema.field("bbox").type == pa.list_(pa.float32(), 4)
        first = table.column("bbox")[0].as_py()
        assert len(first) == 4

    def test_bbox_preserves_ltrb_order(self, doc):
        table = items_table(doc, DOCUMENT_ID)
        row = next(r for r in table.to_pylist() if r["self_ref"] == "#/tables/0")

        assert row["bbox"] == pytest.approx([10.0, 200.0, 100.0, 400.0])

    def test_charspan_is_item_local(self, doc):
        table = items_table(doc, DOCUMENT_ID)
        rows = {r["self_ref"]: r for r in table.to_pylist()}

        assert rows["#/texts/0"]["charspan_start"] == 0
        assert rows["#/texts/0"]["charspan_end"] == len("A Paper")
        assert rows["#/tables/0"]["charspan_end"] == 0

    def test_heading_level_is_carried(self, doc):
        rows = {r["self_ref"]: r for r in items_table(doc, DOCUMENT_ID).to_pylist()}

        assert rows["#/texts/1"]["label"] == DocItemLabel.SECTION_HEADER.value
        assert rows["#/texts/1"]["level"] == 2

    def test_non_heading_items_have_no_level(self, doc):
        rows = {r["self_ref"]: r for r in items_table(doc, DOCUMENT_ID).to_pylist()}

        assert rows["#/texts/2"]["level"] is None

    def test_table_html_is_populated(self, doc):
        rows = {r["self_ref"]: r for r in items_table(doc, DOCUMENT_ID).to_pylist()}

        assert rows["#/tables/0"]["html"] is not None
        assert rows["#/tables/0"]["html"].startswith("<table")

    def test_text_items_have_no_html(self, doc):
        rows = {r["self_ref"]: r for r in items_table(doc, DOCUMENT_ID).to_pylist()}

        assert rows["#/texts/2"]["html"] is None

    def test_parent_ref_is_recorded(self, doc):
        rows = {r["self_ref"]: r for r in items_table(doc, DOCUMENT_ID).to_pylist()}

        assert rows["#/texts/2"]["parent_ref"] == "#/body"

    def test_document_id_is_stamped_on_every_row(self, doc):
        ids = set(items_table(doc, DOCUMENT_ID).column("document_id").to_pylist())

        assert ids == {DOCUMENT_ID}

    def test_coord_origin_is_recorded(self, doc):
        origins = set(items_table(doc, DOCUMENT_ID).column("coord_origin").to_pylist())

        assert origins == {CoordOrigin.TOPLEFT.value}

    def test_empty_document_yields_an_empty_table_with_the_schema(self):
        table = items_table(new_document("empty"), DOCUMENT_ID)

        assert table.num_rows == 0
        assert table.schema.equals(ITEM_SCHEMA)


class TestPagesTable:
    def test_schema_matches_exactly(self, doc):
        assert pages_table(doc, DOCUMENT_ID).schema.equals(PAGE_SCHEMA)

    def test_one_row_per_page_with_its_size(self, doc):
        rows = sorted(pages_table(doc, DOCUMENT_ID).to_pylist(), key=lambda r: r["page_no"])

        assert [r["page_no"] for r in rows] == [1, 2]
        assert rows[0]["height"] == pytest.approx(792.0)
        assert rows[1]["height"] == pytest.approx(1008.0)

    def test_empty_document_yields_an_empty_table_with_the_schema(self):
        table = pages_table(new_document("empty"), DOCUMENT_ID)

        assert table.num_rows == 0
        assert table.schema.equals(PAGE_SCHEMA)


class TestParquetRoundTrip:
    def test_items_survive_a_parquet_round_trip(self, doc, tmp_path):
        original = items_table(doc, DOCUMENT_ID)
        path = tmp_path / "items.parquet"

        pq.write_table(original, path)
        restored = pq.read_table(path)

        assert restored.num_rows == original.num_rows
        assert restored.to_pylist() == original.to_pylist()

    def test_pages_survive_a_parquet_round_trip(self, doc, tmp_path):
        original = pages_table(doc, DOCUMENT_ID)
        path = tmp_path / "pages.parquet"

        pq.write_table(original, path)

        assert pq.read_table(path).to_pylist() == original.to_pylist()

    def test_dictionary_columns_stay_readable_after_round_trip(self, doc, tmp_path):
        path = tmp_path / "items.parquet"
        pq.write_table(items_table(doc, DOCUMENT_ID), path)

        labels = pq.read_table(path).column("label").to_pylist()

        assert DocItemLabel.TABLE.value in labels
