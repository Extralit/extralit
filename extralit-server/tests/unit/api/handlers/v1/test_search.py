"""Tests for `POST /workspaces/{name}/search`."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from pydantic_ai import Embedder

from extralit_server.api.handlers.v1 import search as search_handler
from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.contexts.retrieval.search import hybrid_search
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.settings import settings
from tests.factories import AnnotatorFactory, DocumentFactory, WorkspaceFactory
from tests.hashing_embedder import HashingEmbeddingModel
from tests.integration.retrieval.test_search import DIM, MODEL, chunk_rows, embed


@pytest.fixture
async def workspace_with_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_url", tmp_path.as_uri())
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", MODEL)
    workspace = await WorkspaceFactory.create(name=f"ws-{uuid4().hex[:8]}")
    store = ChunkStore.for_workspace(workspace.name)
    document_id = str((await DocumentFactory.create(workspace=workspace)).id)
    table = chunk_rows(
        document_id, "Ref-A", ["quokka habitat survey results"] + [f"filler {i} words" for i in range(10)]
    )
    store.replace_chunks(document_id, table)
    embedder = Embedder(HashingEmbeddingModel(dimensions=DIM))
    await embed(embedder, store, table)
    monkeypatch.setattr("extralit_server.api.handlers.v1.search.get_embedder", lambda _settings: embedder)
    return workspace, document_id


@pytest.mark.asyncio
class TestSearchWorkspace:
    async def test_chunks_of_a_deleted_document_are_not_returned(
        self, async_client: AsyncClient, owner_auth_header, workspace_with_chunks
    ):
        workspace, document_id = workspace_with_chunks
        orphan = str(uuid4())
        ChunkStore.for_workspace(workspace.name).replace_chunks(orphan, chunk_rows(orphan, "Ref-A", ["quokka orphan"]))

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace.name}/search", headers=owner_auth_header, json={"query": "quokka"}
        )

        assert {hit["document_id"] for hit in response.json()["hits"]} == {document_id}

    async def test_an_orphan_ranked_first_does_not_hide_a_live_hit_under_limit_one(
        self, async_client: AsyncClient, owner_auth_header, workspace_with_chunks
    ):
        workspace, document_id = workspace_with_chunks
        store = ChunkStore.for_workspace(workspace.name)
        embedder = search_handler.get_embedder(None)
        for _ in range(3):
            orphan = str(uuid4())
            table = chunk_rows(orphan, "Ref-A", ["quokka"])
            store.replace_chunks(orphan, table)
            await embed(embedder, store, table)
        top = await hybrid_search([store], "quokka", embedder=embedder, limit=1)
        assert top[0].document_id != document_id

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace.name}/search",
            headers=owner_auth_header,
            json={"query": "quokka", "limit": 1},
        )

        assert [hit["document_id"] for hit in response.json()["hits"]] == [document_id]

    async def test_returns_hits_with_item_refs_and_scores(
        self, async_client: AsyncClient, owner_auth_header, workspace_with_chunks
    ):
        workspace, document_id = workspace_with_chunks

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace.name}/search",
            headers=owner_auth_header,
            json={"query": "quokka habitat survey results", "limit": 3},
        )

        assert response.status_code == 200
        hit = response.json()["hits"][0]
        assert hit["document_id"] == document_id
        assert hit["item_refs"] == ["#/texts/0"]
        assert hit["type"] == "table"
        assert hit["scores"]["bm25"] is not None and hit["scores"]["vector"] is not None and hit["scores"]["rrf"] > 0

    async def test_reference_filter(self, async_client: AsyncClient, owner_auth_header, workspace_with_chunks):
        workspace, _ = workspace_with_chunks

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace.name}/search",
            headers=owner_auth_header,
            json={"query": "words", "references": ["Other"]},
        )

        assert response.json() == {"hits": []}

    async def test_unknown_workspace_is_404(self, async_client: AsyncClient, owner_auth_header):
        response = await async_client.post(
            "/api/v1/workspaces/nope/search", headers=owner_auth_header, json={"query": "x"}
        )

        assert response.status_code == 404

    async def test_non_member_is_forbidden(self, async_client: AsyncClient, workspace_with_chunks):
        workspace, _ = workspace_with_chunks
        outsider = await AnnotatorFactory.create()

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace.name}/search",
            headers={API_KEY_HEADER_NAME: outsider.api_key},
            json={"query": "quokka"},
        )

        assert response.status_code == 403

    async def test_invalid_type_is_422(self, async_client: AsyncClient, owner_auth_header, workspace_with_chunks):
        workspace, _ = workspace_with_chunks

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace.name}/search",
            headers=owner_auth_header,
            json={"query": "x", "types": ["bogus"]},
        )

        assert response.status_code == 422
