"""`retrieval backfill` enqueues chunk jobs only for unchunked or stale documents."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts.retrieval import backfill as module
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.settings import settings as server_settings
from tests.unit.contexts.retrieval.test_store import chunks

pytestmark = pytest.mark.asyncio


class FakeSession:
    def __init__(self, workspaces, documents):
        self.results = [workspaces, *documents]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, _query):
        result = MagicMock()
        result.all.return_value = self.results.pop(0)
        return result


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(server_settings, "storage_url", tmp_path.as_uri())
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", "test:model")
    workspace_id, fresh, stale, unchunked, unparsed = (uuid4() for _ in range(5))
    layout = {"layout_metadata": {"layout_url": "layout/x.docling.json"}}
    store = ChunkStore.for_workspace("ws")
    store.replace_chunks(
        str(fresh), chunks(str(fresh), ["a"]).set_column(11, "chunker_fingerprint", [[module.CHUNKER_FINGERPRINT]])
    )
    store.replace_chunks(str(stale), chunks(str(stale), ["b"]))
    session = FakeSession(
        [(workspace_id, "ws")],
        [[(fresh, layout), (stale, layout), (unchunked, layout), (unparsed, {})]],
    )
    with (
        patch.object(module, "AsyncSessionLocal", lambda: session),
        patch("extralit_server.jobs.retrieval_jobs.async_document_chunk_job.delay") as chunk,
        patch("extralit_server.jobs.retrieval_jobs.async_embed_chunks_job.delay") as embed,
    ):
        yield {
            "chunk": chunk,
            "embed": embed,
            "stale": stale,
            "unchunked": unchunked,
            "session": session,
            "fresh": fresh,
        }


async def test_only_stale_and_unchunked_documents_are_enqueued(world):
    reports = await module.backfill()

    queued = {call.args[0] for call in world["chunk"].call_args_list}
    assert queued == {world["stale"], world["unchunked"]}
    world["embed"].assert_called_once_with("ws")
    assert reports[0].chunk_jobs == 2
    assert reports[0].unembedded == 2


async def test_second_run_enqueues_no_chunk_jobs(world):
    from extralit_server.jobs.retrieval_jobs import async_document_chunk_job  # noqa: F401

    first = await module.backfill()
    assert first[0].chunk_jobs == 2
    for document_id in (world["stale"], world["unchunked"]):
        store = ChunkStore.for_workspace("ws")
        store.replace_chunks(
            str(document_id),
            chunks(str(document_id), ["z"]).set_column(11, "chunker_fingerprint", [[module.CHUNKER_FINGERPRINT]]),
        )
    world["session"].results = [
        [(uuid4(), "ws")],
        [
            (document_id, {"layout_metadata": {"layout_url": "x"}})
            for document_id in (world["fresh"], world["stale"], world["unchunked"])
        ],
    ]
    world["chunk"].reset_mock()

    second = await module.backfill()

    world["chunk"].assert_not_called()
    assert second[0].chunk_jobs == 0
