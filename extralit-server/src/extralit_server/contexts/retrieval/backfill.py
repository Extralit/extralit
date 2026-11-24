"""Re-chunk documents whose chunks do not match their `docling.json` or chunker version, then embed what is missing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from anyio import to_thread
from sqlalchemy import select

from extralit_server.contexts import files
from extralit_server.contexts.ocr import storage as layout_storage
from extralit_server.contexts.retrieval.chunking import CHUNKER_FINGERPRINT
from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.database import AsyncSessionLocal
from extralit_server.models.database import Document, Workspace

_LOGGER = logging.getLogger(__name__)


@dataclass
class WorkspaceBackfill:
    workspace: str
    chunk_jobs: int
    embed_job: bool
    unembedded: Optional[int]
    pruned: int = 0


async def backfill(workspace: Optional[str] = None) -> list[WorkspaceBackfill]:
    from extralit_server.jobs.retrieval_jobs import async_document_chunk_job, async_embed_chunks_job

    settings = RetrievalSettings()
    async with AsyncSessionLocal() as db:
        query = select(Workspace.id, Workspace.name).order_by(Workspace.name)
        if workspace:
            query = query.where(Workspace.name == workspace)
        workspaces = (await db.execute(query)).all()
        existing = {
            workspace_id: {
                str(d) for d in (await db.scalars(select(Document.id).where(Document.workspace_id == workspace_id)))
            }
            for workspace_id, _ in workspaces
        }
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

    storage = await files.get_storage()
    reports = []
    for workspace_id, name in workspaces:
        store = ChunkStore.for_workspace(name)
        stamps = _chunk_stamps(store)
        orphans = [d for d in stamps if d not in existing[workspace_id]]
        if orphans:
            async with store.layout.locked():
                for document_id in orphans:
                    await to_thread.run_sync(store.layout.delete_document, document_id)
            _LOGGER.info(f"Pruned rows of {len(orphans)} deleted documents from workspace {name}")
        stale = []
        for document_id in documents[workspace_id]:
            try:
                raw = await files.read_object(storage, name, layout_storage.layout_object_path(document_id))
                source_hash = layout_storage.layout_hash(raw)
            except Exception as error:
                _LOGGER.warning(f"Skipping document {document_id}: docling.json unreadable: {error}")
                continue
            if stamps.get(str(document_id)) != {(source_hash, CHUNKER_FINGERPRINT)}:
                stale.append(document_id)
        for document_id in stale:
            async_document_chunk_job.delay(document_id, name)

        pending = store.count_unembedded(settings.embedding_model) if settings.embedding_model else None
        embed = bool(pending)
        if embed:
            async_embed_chunks_job.delay(name)
        reports.append(WorkspaceBackfill(name, len(stale), embed, pending, len(orphans)))
    return reports


def _chunk_stamps(store: ChunkStore) -> dict[str, set[tuple[Optional[str], Optional[str]]]]:
    """Document id -> the `(source_hash, chunker_fingerprint)` pairs its chunks carry."""
    dataset = store.open()
    stamps: dict[str, set[tuple[Optional[str], Optional[str]]]] = {}
    if dataset is None:
        return stamps
    columns = [c for c in ("document_id", "source_hash", "chunker_fingerprint") if c in dataset.schema.names]
    table = dataset.to_table(columns=columns).to_pydict()
    for index, document_id in enumerate(table["document_id"]):
        pair = (table["source_hash"][index] if "source_hash" in table else None, table["chunker_fingerprint"][index])
        stamps.setdefault(document_id, set()).add(pair)
    return stamps
