"""Object-storage home of a document's chunks.

Kept beside the layout JSON rather than in `documents.metadata_`, which is returned in full by
every document listing. The object holds the Markdown too, since chunk offsets index into it.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage

_LOGGER = logging.getLogger(__name__)

CHUNKS_PREFIX = "chunks"


def chunks_object_path(document_id: UUID | str) -> str:
    return f"{CHUNKS_PREFIX}/{document_id}.json"


async def store_chunks(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID | str,
    markdown: str,
    chunks: list[dict[str, Any]],
) -> str:
    """Write the Markdown and its chunks as one JSON object; returns its path."""
    path = chunks_object_path(document_id)
    await files.put_object(
        storage,
        workspace_name,
        path,
        json.dumps({"markdown": markdown, "chunks": chunks}, ensure_ascii=False),
        content_type="application/json",
        metadata={"document_id": str(document_id)},
    )
    return path


async def load_chunks(storage: ObjectStorage, workspace_name: str, document_id: UUID | str) -> dict[str, Any]:
    """Read back `{"markdown": str, "chunks": [...]}`."""
    file = await files.get_object(storage, workspace_name, chunks_object_path(document_id))
    return json.loads(bytes(await file.response.bytes_async()))


async def delete_chunks(storage: ObjectStorage, workspace_name: str, document_id: UUID | str) -> None:
    """Best effort, like layout deletion: a leaked object is unreachable and overwritten on re-chunk."""
    try:
        await files.delete_object(storage, workspace_name, chunks_object_path(document_id))
    except Exception as error:
        _LOGGER.warning(f"Could not delete chunks for document {document_id}: {error}")
