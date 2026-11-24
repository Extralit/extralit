from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import DocumentPolicy, authorize
from extralit_server.api.schemas.v1.search import SearchHit, SearchRequest, SearchResponse, SearchScores
from extralit_server.contexts.retrieval.embedding import get_embedder
from extralit_server.contexts.retrieval.search import SearchFilters, embed_query, hybrid_search
from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.database import get_async_db
from extralit_server.models import User, Workspace
from extralit_server.models.database import Document
from extralit_server.security import auth

router = APIRouter(tags=["search"])

MAX_CANDIDATES = 1000


@router.post("/workspaces/{workspace_name}/search")
async def search_workspace(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_name: str,
    body: SearchRequest,
    current_user: Annotated[User, Security(auth.get_current_user)],
) -> SearchResponse:
    workspace = (await db.execute(select(Workspace).where(Workspace.name == workspace_name))).scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workspace `{workspace_name}` not found")
    await authorize(current_user, DocumentPolicy.get_by_workspace(workspace.id))

    settings = RetrievalSettings()
    store = ChunkStore.for_workspace(workspace.name)
    vector = await embed_query([store], body.query, get_embedder(settings), settings)
    filters = SearchFilters(
        document_ids=body.document_ids, references=body.references, pages=body.pages, types=body.types
    )
    # Chunks of deleted documents are dropped, then refilled by asking for more candidates (see retrieval.md).
    requested = body.limit
    while True:
        candidates = await hybrid_search(
            [store], body.query, vector=vector, filters=filters, limit=requested, settings=settings
        )
        live = set(
            (
                await db.execute(
                    select(Document.id).where(
                        Document.workspace_id == workspace.id,
                        Document.id.in_({UUID(h.document_id) for h in candidates}),
                    )
                )
            ).scalars()
        )
        hits = [h for h in candidates if UUID(h.document_id) in live]
        if len(hits) >= body.limit or len(candidates) < requested or requested >= MAX_CANDIDATES:
            break
        requested = min(requested * 4, MAX_CANDIDATES)
    hits = hits[: body.limit]
    return SearchResponse(
        hits=[
            SearchHit(
                **{k: getattr(h, k) for k in SearchHit.model_fields if k != "scores"},
                scores=SearchScores(bm25=h.bm25, vector=h.vector, rrf=h.rrf),
            )
            for h in hits
        ]
    )
