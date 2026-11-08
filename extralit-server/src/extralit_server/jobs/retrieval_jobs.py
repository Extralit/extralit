"""Chunking and embedding jobs over the stored `DoclingDocument`."""

import logging
from typing import Any, Optional
from uuid import UUID

import pyarrow as pa
from anyio import to_thread
from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.contexts import files
from extralit_server.contexts.ocr import storage as layout_storage
from extralit_server.contexts.retrieval.arrow import vector_column, vector_field
from extralit_server.contexts.retrieval.chunking import chunk_document
from extralit_server.contexts.retrieval.embedding import embed_documents, get_embedder
from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore
from extralit_server.contexts.workflows import writer_skip_reason
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import EMBED_QUEUE, OCR_QUEUE, REDIS_CONNECTION
from extralit_server.models.database import Document

_LOGGER = logging.getLogger(__name__)


@job(
    queue=OCR_QUEUE,
    connection=REDIS_CONNECTION,
    timeout=1800,
    result_ttl=3600,
    retry=Retry(max=2, interval=[30, 60]),
)
async def async_document_chunk_job(document_id: UUID, workspace_name: str) -> dict[str, Any]:
    """Chunk the stored `{document_id}.docling.json` and replace the document's chunks."""
    document_id = UUID(str(document_id))
    current_job = get_current_job()
    workflow_id = (current_job.meta or {}).get("workflow_id") if current_job is not None else None

    storage = await files.get_storage()
    doc = await layout_storage.load_layout(storage, workspace_name, document_id)

    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
    reference = document.reference if document is not None else None

    table = chunk_document(doc, str(document_id), reference)

    store = ChunkStore.for_workspace(workspace_name)
    async with store.layout.locked():
        async with AsyncSessionLocal() as db:
            skip = await writer_skip_reason(db, document_id, workflow_id)
        if skip is not None:
            _LOGGER.info(f"Chunks for document {document_id} were not stored: {skip}")
            return {"document_id": str(document_id), "skipped": skip}
        await to_thread.run_sync(store.replace_chunks, document_id, table)

    embed_job_id = None
    if RetrievalSettings().embedding_model:
        embed_job_id = async_embed_chunks_job.delay(workspace_name, str(document_id)).id

    return {"document_id": str(document_id), "num_chunks": table.num_rows, "embed_job_id": embed_job_id}


@job(
    queue=EMBED_QUEUE,
    connection=REDIS_CONNECTION,
    timeout=1800,
    result_ttl=3600,
    retry=Retry(max=2, interval=[30, 60]),
)
async def async_embed_chunks_job(workspace_name: str, document_id: Optional[str] = None) -> dict[str, Any]:
    """Embed chunks whose vector for the configured model is still NULL, one batch per commit."""
    settings = RetrievalSettings()
    embedder = get_embedder(settings)
    if embedder is None:
        return {"embedded": 0, "skipped": "no embedding model configured"}

    store = ChunkStore.for_workspace(workspace_name)
    pending = await to_thread.run_sync(store.unembedded, settings.embedding_model, document_id)
    column = vector_column(settings.embedding_model)
    embedded = 0

    for start in range(0, pending.num_rows, settings.embedding_batch_size):
        batch = pending.slice(start, settings.embedding_batch_size)
        # The provider call stays outside the layout lock, which writers wait on for at most 300 s.
        vectors = await embed_documents(embedder, batch.column("embed_text").to_pylist(), settings.embedding_batch_size)
        dimensions = len(vectors[0])
        payload = pa.Table.from_arrays(
            [
                batch.column("chunk_id"),
                pa.FixedSizeListArray.from_arrays(pa.array([x for v in vectors for x in v], pa.float32()), dimensions),
            ],
            schema=pa.schema([("chunk_id", pa.string()), vector_field(settings.embedding_model, dimensions)]),
        )
        async with store.layout.locked():
            await to_thread.run_sync(store.upsert_vectors, settings.embedding_model, payload)
        embedded += batch.num_rows

    current_job = get_current_job()
    if current_job is not None:
        current_job.meta.update({"workspace_name": workspace_name, "workflow_step": "embed_chunks"})
        current_job.save_meta()
    _LOGGER.info(f"Embedded {embedded} chunks of workspace {workspace_name} into {column}")
    return {"embedded": embedded, "column": column}
