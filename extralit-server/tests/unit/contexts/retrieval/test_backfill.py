"""`retrieval backfill` enqueues chunk jobs for documents whose chunks do not match their docling.json."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts.retrieval import backfill as module
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.settings import settings as server_settings
from tests.unit.contexts.retrieval.test_store import chunks, vectors

HASH = "sha-new"


def stamped(document_id: str, texts: list[str], source_hash: str, fingerprint: str):
    table = chunks(document_id, texts)
    table = table.set_column(
        table.schema.get_field_index("chunker_fingerprint"), "chunker_fingerprint", [[fingerprint] * len(texts)]
    )
    return table.set_column(table.schema.get_field_index("source_hash"), "source_hash", [[source_hash] * len(texts)])


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
    workspace_id, fresh, edited, outdated, unchunked, unparsed = (uuid4() for _ in range(6))
    layout = {"layout_metadata": {"layout_url": "documents/x/docling.json"}}
    store = ChunkStore.for_workspace("ws")
    store.replace_chunks(str(fresh), stamped(str(fresh), ["a"], HASH, module.CHUNKER_FINGERPRINT))
    # `edited`: docling.json was rewritten after its chunks were built.
    store.replace_chunks(str(edited), stamped(str(edited), ["b"], "sha-old", module.CHUNKER_FINGERPRINT))
    store.replace_chunks(str(outdated), stamped(str(outdated), ["c"], HASH, "old-chunker"))
    session = FakeSession(
        [(workspace_id, "ws")],
        [
            [
                (fresh, layout),
                (edited, layout),
                (outdated, layout),
                (unchunked, layout),
                (unparsed, {}),
                (uuid4(), {"layout_metadata": None}),
            ]
        ],
    )
    with (
        patch.object(module, "AsyncSessionLocal", lambda: session),
        patch.object(module.files, "get_storage", AsyncMock()),
        patch.object(module.layout_storage, "read_layout", AsyncMock(return_value=(None, HASH))),
        patch("extralit_server.jobs.retrieval_jobs.async_document_chunk_job.delay") as chunk,
        patch("extralit_server.jobs.retrieval_jobs.async_embed_chunks_job.delay") as embed,
    ):
        yield {
            "chunk": chunk,
            "embed": embed,
            "stale": {edited, outdated, unchunked},
            "session": session,
            "ids": (fresh, edited, outdated, unchunked),
        }


async def test_only_documents_that_do_not_match_their_docling_json_are_enqueued(world):
    reports = await module.backfill()

    queued = {call.args[0] for call in world["chunk"].call_args_list}
    assert queued == world["stale"]
    assert reports[0].chunk_jobs == 3


async def test_second_run_enqueues_nothing(world):
    first = await module.backfill()
    assert first[0].chunk_jobs == 3
    store = ChunkStore.for_workspace("ws")
    for document_id in world["stale"]:
        store.replace_chunks(str(document_id), stamped(str(document_id), ["z"], HASH, module.CHUNKER_FINGERPRINT))
        store.upsert_vectors("test:model", vectors("test:model", [f"{str(document_id)[:8]}-z"], 4))
    store.upsert_vectors("test:model", vectors("test:model", [f"{str(world['ids'][0])[:8]}-a"], 4))
    world["session"].results = [
        [(uuid4(), "ws")],
        [(document_id, {"layout_metadata": {"layout_url": "x"}}) for document_id in world["ids"]],
    ]
    world["chunk"].reset_mock()
    world["embed"].reset_mock()

    second = await module.backfill()

    world["chunk"].assert_not_called()
    world["embed"].assert_not_called()
    assert second[0].chunk_jobs == 0
