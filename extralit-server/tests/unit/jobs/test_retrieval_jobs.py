"""Chunk and embed jobs against a local store; Redis (`EXTRALIT_REDIS_URL`) backs the layout lock."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size
from pydantic_ai import Embedder
from pydantic_ai.embeddings import TestEmbeddingModel

from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, append_blocks, new_document
from extralit_server.contexts.retrieval.arrow import vector_column
from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.settings import settings as server_settings

MODULE = "extralit_server.jobs.retrieval_jobs"
MODEL = "test:model"
pytestmark = pytest.mark.asyncio


def document():
    doc = new_document("sample")
    blocks = [
        LayoutBlock(
            label=DocItemLabel.PARAGRAPH,
            bbox=BoundingBox(l=10, t=30 + 20 * i, r=200, b=40 + 20 * i, coord_origin=CoordOrigin.TOPLEFT),
            text=f"paragraph number {i}",
        )
        for i in range(5)
    ]
    append_blocks(doc, PageContext(page_no=1, size=Size(width=612, height=792)), blocks)
    return doc


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(server_settings, "storage_url", tmp_path.as_uri())
    return ChunkStore.for_workspace("ws-jobs")


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", MODEL)
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_BATCH_SIZE", "2")


class LockProbe(TestEmbeddingModel):
    """Records whether the layout lock was held during each provider call."""

    def __init__(self, store, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.depths = []

    async def embed(self, inputs, *, input_type, settings=None):
        self.depths.append(self.store.layout._lock_depth)
        return await super().embed(inputs, input_type=input_type, settings=settings)


@pytest.fixture
def chunk_env(store):
    session = MagicMock()
    session.return_value.__aenter__ = AsyncMock(
        return_value=MagicMock(get=AsyncMock(return_value=MagicMock(reference="Ref")))
    )
    session.return_value.__aexit__ = AsyncMock(return_value=False)
    with (
        patch(f"{MODULE}.files.get_storage", AsyncMock()),
        patch(f"{MODULE}.layout_storage.load_layout", AsyncMock(return_value=document())),
        patch(f"{MODULE}.ChunkStore.for_workspace", return_value=store),
        patch(f"{MODULE}.AsyncSessionLocal", session),
        patch(f"{MODULE}.writer_skip_reason", AsyncMock(return_value=None)) as skip,
        patch(f"{MODULE}.async_embed_chunks_job.delay") as delay,
    ):
        yield {"skip": skip, "delay": delay}


class TestChunkJob:
    async def test_stores_chunks_and_enqueues_embedding_when_a_model_is_set(self, store, chunk_env, config):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job

        doc_id = uuid4()
        result = await async_document_chunk_job(doc_id, "ws-jobs")

        rows = store.open().to_table().to_pylist()
        assert result["num_chunks"] == len(rows) == 5
        assert {r["reference"] for r in rows} == {"Ref"}
        chunk_env["delay"].assert_called_once_with("ws-jobs", str(doc_id))

    async def test_no_embed_job_without_a_model(self, store, chunk_env, monkeypatch):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job

        monkeypatch.delenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", raising=False)
        await async_document_chunk_job(uuid4(), "ws-jobs")

        chunk_env["delay"].assert_not_called()

    async def test_workflow_id_from_the_layout_job_reaches_the_writer_guard(self, store, chunk_env, config):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job

        doc_id = uuid4()
        chunk_env["skip"].return_value = "workflow superseded"
        result = await async_document_chunk_job(doc_id, "ws-jobs", "wf-old")

        assert chunk_env["skip"].call_args.args[1:] == (doc_id, "wf-old")
        assert result["skipped"] == "workflow superseded"
        assert store.open() is None

    async def test_deleted_document_writes_nothing(self, store, chunk_env, config):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job

        chunk_env["skip"].return_value = "document deleted"
        result = await async_document_chunk_job(uuid4(), "ws-jobs")

        assert result["skipped"] == "document deleted"
        assert store.open() is None
        chunk_env["delay"].assert_not_called()


class TestEmbedJob:
    async def test_embeds_outside_the_lock_then_a_second_run_is_a_noop(self, store, chunk_env, config):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job, async_embed_chunks_job

        await async_document_chunk_job(uuid4(), "ws-jobs")
        probe = LockProbe(store, dimensions=8)
        with (
            patch(f"{MODULE}.ChunkStore.for_workspace", return_value=store),
            patch(f"{MODULE}.get_embedder", return_value=Embedder(probe)),
        ):
            first = await async_embed_chunks_job("ws-jobs")
            second = await async_embed_chunks_job("ws-jobs")

        assert first["embedded"] == 5
        assert probe.depths == [0, 0, 0]
        assert second["embedded"] == 0
        assert store.unembedded(MODEL).num_rows == 0
        assert vector_column(MODEL) in store.open().schema.names

    async def test_empty_model_does_nothing(self, store, monkeypatch):
        from extralit_server.jobs.retrieval_jobs import async_embed_chunks_job

        monkeypatch.delenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", raising=False)
        assert RetrievalSettings().embedding_model == ""
        assert (await async_embed_chunks_job("ws-jobs"))["embedded"] == 0
