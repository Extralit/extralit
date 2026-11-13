"""Chunks + hashing-embedder vectors (`TestEmbeddingModel` is constant, so it cannot rank) searched through the DuckDB `lance` extension."""

from __future__ import annotations

from uuid import uuid4

import pyarrow as pa
import pytest
from pydantic_ai import Embedder

from extralit_server.contexts.retrieval.arrow import CHUNK_SCHEMA, vector_column, vector_field
from extralit_server.contexts.retrieval.search import SearchFilters, hybrid_search
from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.settings import settings as server_settings
from tests.hashing_embedder import HashingEmbeddingModel

MODEL = "test:embed"
DIM = 16
pytestmark = pytest.mark.asyncio


def chunk_rows(document_id: str, reference: str, texts: list[str]) -> pa.Table:
    return pa.Table.from_pylist(
        [
            {
                "chunk_id": f"{document_id}-{i}",
                "document_id": document_id,
                "reference": reference,
                "ordinal": i,
                "kind": "table" if i == 0 else "text",
                "text": text,
                "embed_text": text,
                "headings": ["Methods"],
                "item_refs": [f"#/texts/{i}"],
                "page_start": 1 + i % 3,
                "page_end": 1 + i % 3,
                "chunker_fingerprint": "t",
            }
            for i, text in enumerate(texts)
        ],
        schema=CHUNK_SCHEMA,
    )


async def embed(embedder: Embedder, store: ChunkStore, table: pa.Table) -> None:
    vectors = (await embedder.embed_documents(table.column("embed_text").to_pylist())).embeddings
    flat = pa.FixedSizeListArray.from_arrays(pa.array([x for v in vectors for x in v], pa.float32()), DIM)
    store.upsert_vectors(
        MODEL,
        pa.Table.from_arrays(
            [table.column("chunk_id"), flat], schema=pa.schema([("chunk_id", pa.string()), vector_field(MODEL, DIM)])
        ),
    )


@pytest.fixture
def embedder():
    return Embedder(HashingEmbeddingModel(dimensions=DIM))


@pytest.fixture
def config():
    return RetrievalSettings(embedding_model=MODEL, candidate_k=20)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(server_settings, "storage_url", tmp_path.as_uri())
    return ChunkStore.for_workspace("ws-search")


@pytest.fixture
async def corpus(store, embedder):
    doc_a, doc_b = str(uuid4()), str(uuid4())
    table_a = chunk_rows(
        doc_a, "Ref-A", ["quokka habitat survey results"] + [f"filler a{i} common words" for i in range(40)]
    )
    table_b = chunk_rows(doc_b, "Ref-B", [f"filler b{i} common words" for i in range(40)])
    for doc, table in ((doc_a, table_a), (doc_b, table_b)):
        store.replace_chunks(doc, table)
    await embed(embedder, store, table_a)
    await embed(embedder, store, table_b)
    return doc_a, doc_b, table_a


async def test_fts_only_finds_the_chunk(store, corpus, config):
    _, _, table = corpus
    hits = await hybrid_search([store], "quokka", embedder=None, limit=3, settings=config)

    assert hits[0].chunk_id == table.column("chunk_id")[0].as_py()
    assert hits[0].bm25 is not None and hits[0].vector is None


async def test_hybrid_scores_both_legs(store, corpus, embedder, config):
    _, _, table = corpus
    hits = await hybrid_search([store], "quokka habitat survey results", embedder=embedder, limit=3, settings=config)

    assert hits[0].chunk_id == table.column("chunk_id")[0].as_py()
    assert hits[0].bm25 is not None and hits[0].vector is not None and hits[0].rrf > 0


async def test_reference_filter_still_returns_limit_hits(store, corpus, embedder, config):
    hits = await hybrid_search(
        [store],
        "common words",
        embedder=embedder,
        filters=SearchFilters(references=["Ref-B"]),
        limit=10,
        settings=config,
    )

    assert len(hits) == 10
    assert {h.reference for h in hits} == {"Ref-B"}


async def test_filters_apply_before_top_k_on_a_rare_match(store, corpus, embedder, config):
    doc_a, _, _ = corpus
    hits = await hybrid_search(
        [store],
        "common words",
        embedder=embedder,
        filters=SearchFilters(document_ids=[doc_a], kinds=["table"], pages=[1]),
        limit=5,
        settings=config,
    )

    assert [h.kind for h in hits] == ["table"]


async def test_page_filter_matches_inside_a_chunks_span(store, embedder, config):
    doc = str(uuid4())
    table = chunk_rows(doc, "Ref-S", ["spanning table quokka"])
    table = table.set_column(9, "page_start", pa.array([1], pa.int32())).set_column(
        10, "page_end", pa.array([3], pa.int32())
    )
    store.replace_chunks(doc, table)

    hits = await hybrid_search([store], "quokka", embedder=None, filters=SearchFilters(pages=[2]), settings=config)

    assert [h.chunk_id for h in hits] == [f"{doc}-0"]


async def test_limit_above_candidate_k_is_honoured(store, corpus):
    hits = await hybrid_search(
        [store], "common words", embedder=None, limit=60, settings=RetrievalSettings(candidate_k=20)
    )

    assert len(hits) == 60


async def test_stored_chunk_own_vector_is_first(store, corpus, embedder, config):
    _, doc_b, _ = corpus
    target = store.open().to_table(filter=f"document_id = '{doc_b}' AND ordinal = 7").to_pylist()[0]
    hits = await hybrid_search([store], target["embed_text"], embedder=embedder, limit=1, settings=config)

    assert hits[0].chunk_id == target["chunk_id"]


async def test_vector_leg_skipped_when_model_has_no_column(store, corpus, embedder):
    other = RetrievalSettings(embedding_model="test:other", candidate_k=20)
    hits = await hybrid_search([store], "quokka", embedder=embedder, limit=3, settings=other)

    assert hits and all(h.vector is None for h in hits)


async def test_second_embed_run_is_a_noop(store, corpus):
    assert store.unembedded(MODEL).num_rows == 0
    assert vector_column(MODEL) in store.open().schema.names


async def test_multi_store_union(tmp_path, monkeypatch, store, corpus, embedder, config):
    other_root = tmp_path / "other"
    monkeypatch.setattr(server_settings, "storage_url", other_root.as_uri())
    other = ChunkStore.for_workspace("ws-other")
    doc = str(uuid4())
    table = chunk_rows(doc, "Ref-C", ["quokka tail anatomy"])
    other.replace_chunks(doc, table)
    await embed(embedder, other, table)

    hits = await hybrid_search([store, other], "quokka", embedder=embedder, limit=10, settings=config)

    assert {"Ref-A", "Ref-C"} <= {h.reference for h in hits}
