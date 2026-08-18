"""Serialized writes of `documents.metadata_`.

Several jobs own different slices of the same JSON column, so a read-modify-write that is not
serialized silently drops whatever another job committed in between. Every writer takes the same
row lock through here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata
from extralit_server.models.database import Document


async def update_processing_metadata(
    db: AsyncSession,
    document_id: UUID,
    mutate: Callable[[DocumentProcessingMetadata], None],
) -> Optional[DocumentProcessingMetadata]:
    """Apply `mutate` to the document's processing metadata under a row lock, and commit.

    Returns None when the document is gone, which is how a job learns its work was deleted.
    """
    await db.execute(select(Document.id).where(Document.id == document_id).with_for_update())

    # populate_existing: the lock is worthless if the session hands back its own stale copy.
    document = await db.get(Document, document_id, populate_existing=True)
    if document is None:
        return None

    metadata = DocumentProcessingMetadata(**(document.metadata_ or {}))
    mutate(metadata)
    document.metadata_ = metadata.model_dump()
    await db.commit()
    return metadata
