"""Tests for the document chunking job: what it reads, writes, and refuses to write."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument

from extralit_server.api.schemas.v1.document.metadata import (
    ChunkingMetadata,
    ChunkMetadata,
    DocumentProcessingMetadata,
)

MODULE = "extralit_server.jobs.document_jobs"

pytestmark = pytest.mark.asyncio


def layout() -> DoclingDocument:
    doc = DoclingDocument(name="doc")
    doc.add_heading("Introduction", level=1)
    doc.add_text(label=DocItemLabel.TEXT, text="Mosquito longevity was measured across cohorts. " * 80)
    return doc


@pytest.fixture
def job_context():
    calls = []
    stored = {}
    applied = DocumentProcessingMetadata()

    async def store_chunks(storage, workspace_name, document_id, markdown, chunks):
        calls.append("store_chunks")
        stored.update(markdown=markdown, chunks=chunks)
        return f"chunks/{document_id}.json"

    async def update_metadata(db, document_id, mutate):
        calls.append("update_metadata")
        mutate(applied)
        return applied

    session = MagicMock()
    session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    session.return_value.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(f"{MODULE}.files.get_storage", AsyncMock(return_value=AsyncMock())),
        patch(f"{MODULE}.layout_storage.load_layout", AsyncMock(return_value=layout())) as load,
        patch(f"{MODULE}.chunk_storage.store_chunks", store_chunks),
        patch(f"{MODULE}.chunk_storage.delete_chunks", AsyncMock()) as delete,
        patch(f"{MODULE}.update_processing_metadata", update_metadata) as update,
        patch(f"{MODULE}.get_current_job", return_value=MagicMock(meta={"workflow_id": "wf-1"})),
        patch(f"{MODULE}.writer_skip_reason", AsyncMock(return_value=None)) as skip,
        patch(f"{MODULE}.AsyncSessionLocal", session),
    ):
        yield {
            "calls": calls,
            "stored": stored,
            "metadata": applied,
            "load": load,
            "skip": skip,
            "delete": delete,
            "update": update,
        }


async def run_job(document_id=None):
    from extralit_server.jobs.document_jobs import document_chunking_job

    return await document_chunking_job(document_id or uuid4(), "ws")


class TestChunkingJob:
    async def test_chunks_the_stored_layout(self, job_context):
        document_id = uuid4()

        await run_job(document_id)

        load = job_context["load"].await_args.args
        assert load[1:] == ("ws", document_id)

    async def test_chunks_go_to_storage_and_only_a_pointer_to_metadata(self, job_context):
        document_id = uuid4()

        result = await run_job(document_id)

        stored = job_context["stored"]
        assert len(stored["chunks"]) > 1
        assert all(ChunkMetadata(**c) for c in stored["chunks"])
        assert all(stored["markdown"][c["start_index"] : c["end_index"]] == c["text"] for c in stored["chunks"])

        chunking = job_context["metadata"].chunking_metadata
        assert isinstance(chunking, ChunkingMetadata)
        assert chunking.chunks_url == f"chunks/{document_id}.json"
        assert chunking.num_chunks == len(stored["chunks"])
        assert chunking.markdown_length == len(stored["markdown"])
        assert result["num_chunks"] == chunking.num_chunks
        # Nothing chunk-sized lands in the JSON column every document listing returns.
        assert "chunks" not in job_context["metadata"].model_dump()["chunking_metadata"]

    async def test_storage_is_written_before_metadata(self, job_context):
        await run_job()

        assert job_context["calls"] == ["store_chunks", "update_metadata"]

    @pytest.mark.parametrize("reason", ["document deleted", "workflow superseded"])
    async def test_a_stale_run_writes_nothing(self, job_context, reason):
        job_context["skip"].return_value = reason

        result = await run_job()

        assert result["skipped"] == reason
        assert job_context["skip"].await_args.args[2] == "wf-1"
        assert job_context["calls"] == []

    async def test_a_document_deleted_before_the_metadata_write_drops_its_chunks(self, job_context):
        async def gone(db, document_id, mutate):
            return None

        with patch(f"{MODULE}.update_processing_metadata", gone):
            result = await run_job()

        assert result["skipped"] == "document deleted"
        job_context["delete"].assert_awaited_once()

    async def test_a_missing_layout_fails_the_job(self, job_context):
        job_context["load"].side_effect = FileNotFoundError("layout/x.docling.json")

        with pytest.raises(FileNotFoundError):
            await run_job()

        assert job_context["calls"] == []
