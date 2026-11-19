"""Object-storage layout for extracted document layout.

Canonical JSON (`documents/{id}/docling.json`) is the source of truth, page sizes included; the
item rows live in the workspace's Lance datasets (see `layout_store`) so a corpus-wide question is
one scan. Both live in S3 rather than `documents.metadata_`, which every document listing returns.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional
from uuid import UUID

from anyio import to_thread
from docling_core.types.doc import DoclingDocument

from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage
from extralit_server.contexts.ocr.arrow import items_table
from extralit_server.contexts.ocr.layout_store import LayoutStore

_LOGGER = logging.getLogger("extralit_server.contexts.ocr.storage")


def layout_hash(raw: bytes) -> str:
    """Stamp carried by every item and chunk row built from this exact `docling.json`."""
    return hashlib.sha256(raw).hexdigest()


def layout_object_path(document_id: UUID | str) -> str:
    """Key of the document's canonical `DoclingDocument` JSON."""
    return files.get_docling_json_s3_object_path(document_id)


async def store_layout(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID | str,
    doc: DoclingDocument,
    store: Optional[LayoutStore] = None,
) -> dict[str, Any]:
    """Write the canonical JSON, then replace this document's rows in the workspace datasets.

    `store` lets a caller that already holds the workspace lock pass its own handle through; the
    lock is reentrant per store instance, so the replace still runs serialized either way.
    """
    document_id = str(document_id)
    layout_url = layout_object_path(document_id)
    store = store or LayoutStore.for_workspace(workspace_name)

    raw = json.dumps(doc.export_to_dict(), ensure_ascii=False).encode("utf-8")
    source_hash = layout_hash(raw)
    await files.put_object(
        storage,
        workspace_name,
        layout_url,
        raw,
        content_type="application/json",
        metadata={"docling_version": doc.version, "document_id": document_id},
    )

    items = items_table(doc, document_id, source_hash)
    async with store.locked():
        versions = await to_thread.run_sync(store.replace_document, document_id, items)
        await to_thread.run_sync(store.maybe_compact)

    return {
        "layout_url": layout_url,
        "items_uri": store.items_uri(),
        "source_hash": source_hash,
        **versions,
    }


async def delete_layout(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID | str,
    store: Optional[LayoutStore] = None,
) -> None:
    """Drop the JSON and the rows. Best effort: orphaned rows are superseded on the next parse."""
    try:
        await files.delete_object(storage, workspace_name, layout_object_path(document_id))
    except Exception as error:
        _LOGGER.warning(f"Could not delete layout JSON for document {document_id}: {error}")

    try:
        store = store or LayoutStore.for_workspace(workspace_name)
        async with store.locked():
            await to_thread.run_sync(store.delete_document, document_id)
    except Exception as error:
        _LOGGER.warning(f"Could not delete layout rows for document {document_id}: {error}")


async def load_layout(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID | str,
    object_path: Optional[str] = None,
) -> DoclingDocument:
    """Read the canonical JSON back into a `DoclingDocument`.

    A document written by a newer docling-core fails validation outright — the version validator
    demands an equal major and a minor no higher than the SDK's.
    """
    doc, _ = await read_layout(storage, workspace_name, document_id, object_path)
    return doc


async def read_layout(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID | str,
    object_path: Optional[str] = None,
) -> tuple[DoclingDocument, str]:
    """`load_layout` plus the hash of the bytes it parsed."""
    key = object_path or layout_object_path(document_id)
    file = await files.get_object(storage, workspace_name, key)
    raw = bytes(await file.response.bytes_async())
    return DoclingDocument.model_validate(json.loads(raw)), layout_hash(raw)
