"""ChunkStore round-trips on a local `file://` root."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pyarrow as pa
import pytest

from extralit_server.contexts.ocr.arrow import ITEM_SCHEMA, PAGE_SCHEMA
from extralit_server.contexts.ocr.layout_store import LayoutStore
from extralit_server.contexts.ocr.storage import delete_layout
from extralit_server.contexts.retrieval.arrow import CHUNK_SCHEMA, vector_column, vector_field
from extralit_server.contexts.retrieval.store import ChunkStore, DimensionMismatchError
from extralit_server.settings import settings

MODEL_A = "test:model-a"
MODEL_B = "test:Model_B/v2"


def chunks(document_id: str, texts: list[str]) -> pa.Table:
    return pa.Table.from_pylist(
        [
            {
                "chunk_id": f"{document_id[:8]}-{text}",
                "document_id": document_id,
                "reference": "Ref",
                "ordinal": i,
                "kind": "text",
                "text": text,
                "embed_text": text,
                "headings": [],
                "item_refs": [f"#/texts/{i}"],
                "page_start": 1,
                "page_end": 1,
                "chunker_fingerprint": "t",
            }
            for i, text in enumerate(texts)
        ],
        schema=CHUNK_SCHEMA,
    )


def vectors(model: str, ids: list[str], dim: int, seed: int = 0) -> pa.Table:
    data = np.random.default_rng(seed).random((len(ids), dim), dtype=np.float32)
    flat = pa.FixedSizeListArray.from_arrays(pa.array(data.ravel()), dim)
    return pa.Table.from_arrays(
        [pa.array(ids), flat], schema=pa.schema([("chunk_id", pa.string()), vector_field(model, dim)])
    )


def indexes(store: ChunkStore) -> dict[str, str]:
    return {i["name"]: i["type"] for i in store.open().list_indices()}


def nearest(store: ChunkStore, model: str, row: pa.Table) -> str:
    column = vector_column(model)
    query = np.asarray(row.column(column).to_pylist()[0], dtype=np.float32)
    return (
        store.open().to_table(nearest={"column": column, "q": query, "k": 5}, columns=["chunk_id"]).column(0)[0].as_py()
    )


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_url", tmp_path.as_uri())
    return ChunkStore.for_workspace("ws-chunks")


@pytest.fixture
def doc():
    return str(uuid4())


class TestChunks:
    def test_first_write_creates_the_dataset_and_text_index(self, store, doc):
        store.replace_chunks(doc, chunks(doc, ["alpha beta", "gamma"]))

        assert store.open().count_rows() == 2
        assert indexes(store) == {"chunks_text_idx": "Inverted"}
        assert store.open().to_table(full_text_query="gamma").num_rows == 1

    def test_full_text_finds_rows_appended_after_indexing(self, store, doc):
        store.replace_chunks(doc, chunks(doc, ["alpha"]))
        other = str(uuid4())
        store.replace_chunks(other, chunks(other, ["omega"]))

        assert store.open().to_table(full_text_query="omega").num_rows == 1

    def test_rechunk_drops_removed_chunks_and_leaves_other_documents(self, store, doc):
        other = str(uuid4())
        store.replace_chunks(other, chunks(other, ["keep"]))
        store.replace_chunks(doc, chunks(doc, ["a", "b", "c"]))

        store.replace_chunks(doc, chunks(doc, ["a", "c"]))

        remaining = sorted(store.open().to_table(columns=["text"]).column(0).to_pylist())
        assert remaining == ["a", "c", "keep"]

    def test_rechunk_to_nothing_clears_the_document(self, store, doc):
        store.replace_chunks(doc, chunks(doc, ["a"]))

        store.replace_chunks(doc, chunks(doc, []))

        assert store.open().count_rows() == 0

    def test_delete_document_removes_chunks(self, store, doc):
        store.replace_chunks(doc, chunks(doc, ["a"]))

        store.layout.delete_document(doc)

        assert store.open().count_rows() == 0

    def test_source_is_an_empty_chunk_table_before_any_write(self, store):
        assert store.source().schema == CHUNK_SCHEMA


class TestVectors:
    def test_two_models_sit_side_by_side_each_indexed(self, store, doc):
        texts = ["a", "b", "c", "d"]
        table = chunks(doc, texts)
        ids = table.column("chunk_id").to_pylist()
        store.replace_chunks(doc, table)

        store.upsert_vectors(MODEL_A, vectors(MODEL_A, ids, 8))
        store.upsert_vectors(MODEL_B, vectors(MODEL_B, ids, 16, seed=1))

        assert store.vector_columns() == {MODEL_A: vector_column(MODEL_A), MODEL_B: vector_column(MODEL_B)}
        assert vector_column(MODEL_B) == "vector__test_model_b_v2"
        found = indexes(store)
        assert found[f"{vector_column(MODEL_A)}_idx"] == "IVF_HNSW_FLAT"
        assert found[f"{vector_column(MODEL_B)}_idx"] == "IVF_HNSW_FLAT"
        assert store.unembedded(MODEL_A).num_rows == 0

    def test_unembedded_lists_rows_without_a_vector(self, store, doc):
        table = chunks(doc, ["a", "b", "c"])
        ids = table.column("chunk_id").to_pylist()
        store.replace_chunks(doc, table)
        assert store.unembedded(MODEL_A).num_rows == 3

        store.upsert_vectors(MODEL_A, vectors(MODEL_A, ids[:1], 4))

        pending = store.unembedded(MODEL_A, doc)
        assert sorted(pending.column("chunk_id").to_pylist()) == sorted(ids[1:])
        assert store.unembedded(MODEL_A, str(uuid4())).num_rows == 0

    def test_rows_appended_after_the_index_are_still_searched(self, store, doc):
        first = chunks(doc, ["a", "b", "c"])
        store.replace_chunks(doc, first)
        store.upsert_vectors(MODEL_A, vectors(MODEL_A, first.column("chunk_id").to_pylist(), 8))

        late = chunks(doc, ["a", "b", "c", "late"])
        store.replace_chunks(doc, late)
        late_vectors = vectors(MODEL_A, [late.column("chunk_id")[3].as_py()], 8, seed=9)
        store.upsert_vectors(MODEL_A, late_vectors)

        assert nearest(store, MODEL_A, late_vectors) == late.column("chunk_id")[3].as_py()

    def test_rechunk_keeps_vectors_of_unchanged_chunks_and_drops_removed(self, store, doc):
        table = chunks(doc, ["a", "b", "c"])
        ids = table.column("chunk_id").to_pylist()
        store.replace_chunks(doc, table)
        embedded = vectors(MODEL_A, ids, 8)
        store.upsert_vectors(MODEL_A, embedded)

        store.replace_chunks(doc, chunks(doc, ["a", "c", "new"]))

        rows = {
            r["text"]: r[vector_column(MODEL_A)]
            for r in store.open().to_table(columns=["text", vector_column(MODEL_A)]).to_pylist()
        }
        assert set(rows) == {"a", "c", "new"}
        assert rows["new"] is None
        expected = dict(zip(ids, embedded.column(vector_column(MODEL_A)).to_pylist(), strict=True))
        assert rows["a"] == expected[ids[0]]
        assert rows["c"] == expected[ids[2]]
        assert store.unembedded(MODEL_A).column("embed_text").to_pylist() == ["new"]

    def test_other_dimensions_are_rejected_and_the_column_is_untouched(self, store, doc):
        table = chunks(doc, ["a"])
        ids = table.column("chunk_id").to_pylist()
        store.replace_chunks(doc, table)
        original = vectors(MODEL_A, ids, 8)
        store.upsert_vectors(MODEL_A, original)

        with pytest.raises(DimensionMismatchError):
            store.upsert_vectors(MODEL_A, vectors(MODEL_A, ids, 4))

        stored = store.open().to_table(columns=[vector_column(MODEL_A)]).column(0).to_pylist()
        assert stored == original.column(vector_column(MODEL_A)).to_pylist()

    def test_a_different_model_with_the_same_slug_is_rejected(self, store, doc):
        table = chunks(doc, ["a"])
        ids = table.column("chunk_id").to_pylist()
        store.replace_chunks(doc, table)
        store.upsert_vectors("x:m-1", vectors("x:m-1", ids, 4))

        with pytest.raises(DimensionMismatchError):
            store.upsert_vectors("x:m_1", vectors("x:m_1", ids, 4))

    def test_dropping_a_model_removes_its_column_and_index(self, store, doc):
        table = chunks(doc, ["a"])
        store.replace_chunks(doc, table)
        store.upsert_vectors(MODEL_A, vectors(MODEL_A, table.column("chunk_id").to_pylist(), 4))

        store.drop_vector_column(MODEL_A)

        assert store.vector_columns() == {}
        assert list(indexes(store)) == ["chunks_text_idx"]

    def test_vectors_for_deleted_chunks_are_not_resurrected(self, store, doc):
        store.replace_chunks(doc, chunks(doc, ["a"]))

        store.upsert_vectors(MODEL_A, vectors(MODEL_A, ["gone"], 4))

        assert store.open().count_rows() == 1
        assert store.unembedded(MODEL_A).num_rows == 1


def test_layout_store_replace_accepts_registered_extra_datasets(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_url", tmp_path.as_uri())
    layout = LayoutStore.for_workspace("ws-extra")
    ChunkStore(layout)
    doc = str(uuid4())

    versions = layout.replace_document(
        doc,
        pa.Table.from_pylist([], schema=ITEM_SCHEMA),
        pa.Table.from_pylist([], schema=PAGE_SCHEMA),
        extra={"chunks": chunks(doc, ["a"])},
    )

    assert versions["chunks_version"] >= 1
    with pytest.raises(KeyError):
        layout.replace_document(
            doc,
            pa.Table.from_pylist([], schema=ITEM_SCHEMA),
            pa.Table.from_pylist([], schema=PAGE_SCHEMA),
            extra={"unknown": pa.table({})},
        )


def test_replace_document_keeps_vectors_of_unchanged_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_url", tmp_path.as_uri())
    layout = LayoutStore.for_workspace("ws-keep")
    store = ChunkStore(layout)
    doc = str(uuid4())
    table = chunks(doc, ["a", "b"])
    store.replace_chunks(doc, table)
    store.upsert_vectors(MODEL_A, vectors(MODEL_A, table.column("chunk_id").to_pylist(), 4))

    layout.replace_document(
        doc,
        pa.Table.from_pylist([], schema=ITEM_SCHEMA),
        pa.Table.from_pylist([], schema=PAGE_SCHEMA),
        extra={"chunks": chunks(doc, ["a", "c"])},
    )

    assert store.unembedded(MODEL_A).column("embed_text").to_pylist() == ["c"]


def test_dropping_a_colliding_model_leaves_the_stored_one(store, doc):
    table = chunks(doc, ["a"])
    store.replace_chunks(doc, table)
    store.upsert_vectors("x:m-1", vectors("x:m-1", table.column("chunk_id").to_pylist(), 4))

    store.drop_vector_column("x:m_1")

    assert store.vector_columns() == {"x:m-1": vector_column("x:m-1")}


class TestDeleteLayoutDropsChunks:
    @pytest.mark.asyncio
    async def test_delete_layout_removes_the_documents_chunks(self, store, doc):
        other = str(uuid4())
        store.replace_chunks(doc, chunks(doc, ["a", "b"]))
        store.replace_chunks(other, chunks(other, ["keep"]))
        with patch("extralit_server.contexts.ocr.storage.files.delete_object", AsyncMock()):
            await delete_layout(AsyncMock(), "ws-chunks", doc, store=store.layout)

        assert store.open().to_table(columns=["text"]).column(0).to_pylist() == ["keep"]
