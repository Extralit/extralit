"""docling.json -> items -> chunks sync: real RQ queue and worker on Redis, local `file://` storage, no database."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, RefItem, Size
from rq import SimpleWorker
from rq.job import Job

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata
from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage
from extralit_server.contexts.ocr.arrow import items_table
from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, append_blocks, new_document
from extralit_server.contexts.ocr.layout_store import ITEMS_DATASET
from extralit_server.contexts.ocr.parsers.service import ParserService
from extralit_server.contexts.ocr.storage import layout_hash, store_layout
from extralit_server.contexts.retrieval.chunking import chunk_document
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.jobs.queues import DEFAULT_QUEUE, EMBED_QUEUE, OCR_QUEUE, REDIS_CONNECTION
from extralit_server.settings import settings as server_settings
from extralit_server.workflows.documents import create_document_workflow

FIXTURES = Path(__file__).parents[2] / "fixtures" / "pdf"
WORKSPACE = "ws-sync"


class BlockParser:
    def parse_pages(self, pdf_bytes, pages, *, ocr):
        return {
            page: [
                LayoutBlock(
                    label=DocItemLabel.PARAGRAPH,
                    bbox=BoundingBox(l=10, t=30, r=200, b=40, coord_origin=CoordOrigin.TOPLEFT),
                    text=f"text of page {page}",
                )
            ]
            for page in pages
        }


def noop_analysis(*args, **kwargs):
    """Stands in for the analysis job: `ocr.pdf` is put in storage by the test."""
    return None


class FakeSession:
    def __init__(self):
        self.db = MagicMock()
        self.db.scalar = AsyncMock(return_value="paper.pdf")
        self.db.get = AsyncMock(return_value=MagicMock(reference="Ref2020"))
        self.db.commit = AsyncMock()
        self.db.refresh = AsyncMock()

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(server_settings, "storage_url", tmp_path.as_uri())
    monkeypatch.delenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", raising=False)
    session = FakeSession()
    patches = [
        patch("extralit_server.workflows.documents.AsyncSessionLocal", session),
        patch("extralit_server.workflows.documents.analysis_and_preprocess_job", noop_analysis),
        patch("extralit_server.jobs.ocr_jobs.AsyncSessionLocal", session),
        patch(
            "extralit_server.jobs.ocr_jobs.default_service",
            return_value=ParserService(
                {"pymupdf": BlockParser(), "liteparse": BlockParser()},
                triage=lambda _: TriageMetadata(pdf_type="text", page_count=2),
            ),
        ),
        patch("extralit_server.jobs.ocr_jobs.writer_skip_reason", AsyncMock(return_value=None)),
        patch("extralit_server.jobs.ocr_jobs.update_processing_metadata", AsyncMock()),
        patch("extralit_server.jobs.retrieval_jobs.AsyncSessionLocal", session),
        patch("extralit_server.jobs.retrieval_jobs.writer_skip_reason", AsyncMock(return_value=None)),
        patch("extralit_server.contexts.files.get_storage", AsyncMock(side_effect=lambda: ObjectStorage())),
    ]
    for p in patches:
        p.start()
    yield tmp_path
    for p in patches:
        p.stop()


def upload_ocr_pdf(document_id) -> None:
    storage = ObjectStorage()
    asyncio.run(
        files.put_object(
            storage,
            WORKSPACE,
            files.get_ocr_pdf_s3_object_path(document_id),
            (FIXTURES / "two_page.pdf").read_bytes(),
            content_type="application/pdf",
        )
    )


def start_workflow(document_id):
    return asyncio.run(
        create_document_workflow(
            document_id, f"/api/v1/file/{WORKSPACE}/documents/{document_id}/source.pdf", "Ref2020", WORKSPACE, uuid4()
        )
    )


def jobs_by_step(group) -> dict[str, Job]:
    return {job.meta["workflow_step"]: job for job in group.get_jobs()}


def run_workers() -> None:
    SimpleWorker([DEFAULT_QUEUE, OCR_QUEUE], connection=REDIS_CONNECTION).work(burst=True)


def docling_hash(document_id) -> str:
    raw = asyncio.run(files.read_object(ObjectStorage(), WORKSPACE, files.get_docling_json_s3_object_path(document_id)))
    return hashlib.sha256(raw).hexdigest()


class TestEnqueueChain:
    def test_layout_then_chunks_run_and_rows_carry_the_hash_of_docling_json(self, env):
        document_id = uuid4()
        upload_ocr_pdf(document_id)

        group = start_workflow(document_id)
        steps = jobs_by_step(group)
        assert steps["document_chunks"].dependency_ids == [steps["document_layout"].id]
        assert steps["document_chunks"].get_status(refresh=True) == "deferred"
        run_workers()

        assert steps["document_layout"].get_status(refresh=True) == "finished"
        assert steps["document_chunks"].get_status(refresh=True) == "finished"
        store = ChunkStore.for_workspace(WORKSPACE)
        expected = {docling_hash(document_id)}
        assert store.layout.source_hashes(ITEMS_DATASET)[str(document_id)] == expected
        assert store.layout.source_hashes("chunks")[str(document_id)] == expected
        assert store.open().count_rows() > 0
        raw = asyncio.run(
            files.read_object(ObjectStorage(), WORKSPACE, files.get_docling_json_s3_object_path(document_id))
        )
        assert json.loads(raw)["origin"]["filename"] == "paper.pdf"

    def test_chunk_job_enqueues_the_embed_job_when_a_model_is_set(self, env, monkeypatch):
        monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", "test:model")
        document_id = uuid4()
        upload_ocr_pdf(document_id)
        start_workflow(document_id)

        run_workers()

        assert EMBED_QUEUE.count == 1

    def test_a_failed_layout_leaves_the_chunk_job_deferred_not_running_on_stale_data(self, env):
        document_id = uuid4()
        group = start_workflow(document_id)  # no ocr.pdf: the layout job fails

        run_workers()

        steps = jobs_by_step(group)
        assert steps["document_layout"].get_status(refresh=True) != "finished"
        assert steps["document_chunks"].get_status(refresh=True) == "deferred"
        assert ChunkStore.for_workspace(WORKSPACE).open() is None


class TestFailuresAreNotSwallowed:
    def test_a_failed_embed_enqueue_fails_the_chunk_job_so_rq_retries_it(self, env, monkeypatch):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job

        monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", "test:model")
        document_id = uuid4()
        doc = rebuilt(["alpha", "beta"])
        asyncio.run(store_layout(ObjectStorage(), WORKSPACE, document_id, doc))

        with patch(
            "extralit_server.jobs.retrieval_jobs.async_embed_chunks_job.delay", side_effect=ConnectionError("redis")
        ):
            with pytest.raises(ConnectionError):
                asyncio.run(async_document_chunk_job(document_id, WORKSPACE))

        # The rerun is idempotent: same chunks, now enqueued.
        with patch("extralit_server.jobs.retrieval_jobs.async_embed_chunks_job.delay") as delay:
            asyncio.run(async_document_chunk_job(document_id, WORKSPACE))
        delay.assert_called_once()
        assert ChunkStore.for_workspace(WORKSPACE).open().count_rows() == 2

    def test_a_chunk_job_heals_items_that_lag_docling_json(self, env):
        from extralit_server.jobs.retrieval_jobs import async_document_chunk_job

        document_id = uuid4()
        asyncio.run(store_layout(ObjectStorage(), WORKSPACE, document_id, rebuilt(["alpha", "beta"])))
        store = ChunkStore.for_workspace(WORKSPACE)
        # Crash between the layout job's two writes: docling.json is newer than the rows.
        store.layout.replace_document(document_id, items_table(rebuilt(["old"]), str(document_id), "stale"))

        asyncio.run(async_document_chunk_job(document_id, WORKSPACE))

        expected = {docling_hash(document_id)}
        assert store.layout.source_hashes(ITEMS_DATASET)[str(document_id)] == expected
        assert store.layout.source_hashes("chunks")[str(document_id)] == expected


def rebuilt(texts: list[str], headings_first: bool = False):
    doc = new_document("sample")
    blocks = [
        LayoutBlock(
            label=DocItemLabel.PARAGRAPH,
            bbox=BoundingBox(l=10, t=30 + 20 * i, r=200, b=40 + 20 * i, coord_origin=CoordOrigin.TOPLEFT),
            text=text,
        )
        for i, text in enumerate(texts)
    ]
    append_blocks(doc, PageContext(page_no=1, size=Size(width=612, height=792)), blocks)
    return doc


class TestReparse:
    def test_item_refs_resolve_after_an_item_is_removed_and_unchanged_chunks_keep_vectors(self, env):
        from tests.unit.contexts.retrieval.test_store import vectors

        document_id = str(uuid4())
        store = ChunkStore.for_workspace(WORKSPACE)
        before = rebuilt(["alpha", "beta", "gamma", "delta"])
        after = rebuilt(["alpha", "gamma", "delta"])

        def write(doc, source_hash):
            store.layout.replace_document(
                document_id,
                items_table(doc, document_id, source_hash),
                {"chunks": chunk_document(doc, document_id, "Ref", source_hash)},
            )

        write(before, "h1")
        ids = store.open().to_table(columns=["chunk_id"]).column(0).to_pylist()
        store.upsert_vectors("test:model", vectors("test:model", ids, 4))
        vector_of = {
            row["chunk_id"]: row["vector__test_model"]
            for row in store.open().to_table(columns=["chunk_id", "vector__test_model"]).to_pylist()
        }
        assert before.texts[2].text == "gamma"

        write(after, "h2")

        rows = store.open().to_table().to_pylist()
        assert sorted(r["text"] for r in rows) == ["alpha", "delta", "gamma"]
        for row in rows:
            resolved = [RefItem(cref=ref).resolve(after).text for ref in row["item_refs"]]
            assert resolved == [row["text"]]
            assert row["source_hash"] == "h2"
            assert row["vector__test_model"] == vector_of[row["chunk_id"]]
        item_rows = store.layout.load_items(document_id).to_pylist()
        assert {r["source_hash"] for r in item_rows} == {"h2"}
        assert {r["self_ref"] for r in item_rows} == {f"#/texts/{i}" for i in range(3)}


class TestDelete:
    def test_deleting_a_document_removes_its_objects_items_and_chunks(self, env):
        keep, drop = str(uuid4()), str(uuid4())
        storage = ObjectStorage()
        store = ChunkStore.for_workspace(WORKSPACE)
        for document_id, texts in ((keep, ["keep"]), (drop, ["alpha", "beta"])):
            doc = rebuilt(texts)
            asyncio.run(store_layout(storage, WORKSPACE, document_id, doc))
            asyncio.run(
                files.put_object(storage, WORKSPACE, f"documents/{document_id}/source.pdf", b"%PDF", "application/pdf")
            )
            store.replace_chunks(document_id, chunk_document(doc, document_id, "Ref", layout_hash(b"x")))

        asyncio.run(files.delete_document_artifacts(storage, WORKSPACE, drop))

        listed = asyncio.run(files.list_objects(storage, WORKSPACE, prefix=f"documents/{drop}/"))
        assert not listed
        assert store.layout.load_items(drop).num_rows == 0
        assert store.open().to_table(filter=f"document_id = '{drop}'").num_rows == 0
        assert store.layout.load_items(keep).num_rows > 0
        assert store.open().to_table(filter=f"document_id = '{keep}'").num_rows == 1
