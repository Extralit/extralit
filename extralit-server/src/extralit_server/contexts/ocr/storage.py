"""Object-storage layout for extracted document layout.

Canonical JSON is the source of truth; the columnar rows live in the workspace's Lance datasets
(see `layout_store`) so a corpus-wide question is one scan. Both live in S3 rather than
`documents.metadata_`, which is returned in full by every document listing.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional
from uuid import UUID

from anyio import to_thread
from docling_core.types.doc import DoclingDocument

from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage
from extralit_server.contexts.ocr.arrow import items_table, pages_table
from extralit_server.contexts.ocr.layout_store import LAYOUT_PREFIX, LayoutStore

_LOGGER = logging.getLogger("extralit_server.contexts.ocr.storage")


def layout_object_path(document_id: UUID | str) -> str:
    return f"{LAYOUT_PREFIX}/{document_id}.docling.json"


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

    await files.put_object(
        storage,
        workspace_name,
        layout_url,
        json.dumps(doc.export_to_dict(), ensure_ascii=False),
        content_type="application/json",
        metadata={"docling_version": doc.version, "document_id": document_id},
    )

    items = items_table(doc, document_id)
    pages = pages_table(doc, document_id)
    async with store.locked():
        versions = await to_thread.run_sync(store.replace_document, document_id, items, pages)
        await to_thread.run_sync(store.maybe_compact)

    return {
        "layout_url": layout_url,
        "items_uri": store.items_uri(),
        "pages_uri": store.pages_uri(),
        **versions,
    }


async def delete_layout(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID | str,
    store: Optional[LayoutStore] = None,
) -> None:
    """Drop both artifacts. Orphaned rows would skew workspace aggregates, but a failure here is
    negligible: they are superseded on the next parse of that document."""
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
    key = object_path or layout_object_path(document_id)
    file = await files.get_object(storage, workspace_name, key)
    raw = bytes(await file.response.bytes_async())
    return DoclingDocument.model_validate(json.loads(raw))
