"""Chunk documents that predate the chunk job or its chunker version, then embed what is missing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select

from extralit_server.contexts.retrieval.chunking import CHUNKER_FINGERPRINT
from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.database import AsyncSessionLocal
from extralit_server.models.database import Document, Workspace


@dataclass
class WorkspaceBackfill:
    workspace: str
    chunk_jobs: int
    embed_job: bool
    unembedded: Optional[int]


async def backfill(workspace: Optional[str] = None) -> list[WorkspaceBackfill]:
    from extralit_server.jobs.retrieval_jobs import async_document_chunk_job, async_embed_chunks_job

    settings = RetrievalSettings()
    async with AsyncSessionLocal() as db:
        query = select(Workspace.id, Workspace.name).order_by(Workspace.name)
        if workspace:
            query = query.where(Workspace.name == workspace)
        workspaces = (await db.execute(query)).all()
        documents = {
            workspace_id: [
                document_id
                for document_id, metadata in (
                    await db.execute(
                        select(Document.id, Document.metadata_).where(Document.workspace_id == workspace_id)
                    )
                ).all()
                if ((metadata or {}).get("layout_metadata") or {}).get("layout_url")
            ]
            for workspace_id, _ in workspaces
        }

    reports = []
    for workspace_id, name in workspaces:
        store = ChunkStore.for_workspace(name)
        fingerprints: dict[str, set[str]] = {}
        dataset = store.open()
        if dataset is not None:
            table = dataset.to_table(columns=["document_id", "chunker_fingerprint"])
            for document_id, fingerprint in zip(
                table.column("document_id").to_pylist(), table.column("chunker_fingerprint").to_pylist(), strict=True
            ):
                fingerprints.setdefault(document_id, set()).add(fingerprint)

        stale = [d for d in documents[workspace_id] if fingerprints.get(str(d)) != {CHUNKER_FINGERPRINT}]
        for document_id in stale:
            async_document_chunk_job.delay(document_id, name)

        embed = bool(settings.embedding_model)
        if embed:
            async_embed_chunks_job.delay(name)
        pending = store.unembedded(settings.embedding_model).num_rows if embed else None
        reports.append(WorkspaceBackfill(name, len(stale), embed, pending))
    return reports
