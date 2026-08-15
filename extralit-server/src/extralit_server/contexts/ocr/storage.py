"""Object-storage layout for extracted document layout.

Canonical JSON is the source of truth; the Parquet sidecars are a columnar projection for
analytics and cross-document provenance search. Both live in S3 rather than `documents.metadata_`,
which is returned in full by every document listing.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, Optional
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from docling_core.types.doc import DoclingDocument

from extralit_server.contexts import files
from extralit_server.contexts.ocr.arrow import items_table, pages_table

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client

LAYOUT_PREFIX = "layout"


def layout_object_path(document_id: UUID | str) -> str:
    return f"{LAYOUT_PREFIX}/{document_id}.docling.json"


def items_object_path(document_id: UUID | str) -> str:
    return f"{LAYOUT_PREFIX}/{document_id}.items.parquet"


def pages_object_path(document_id: UUID | str) -> str:
    return f"{LAYOUT_PREFIX}/{document_id}.pages.parquet"


def _to_parquet(table: pa.Table) -> bytes:
    buffer = io.BytesIO()
    pq.write_table(table, buffer, compression="zstd")
    return buffer.getvalue()


async def store_layout(
    s3_client: S3Client,
    workspace_name: str,
    document_id: UUID | str,
    doc: DoclingDocument,
) -> dict[str, str]:
    """Write the canonical JSON and both Parquet sidecars. Returns their object paths."""
    document_id = str(document_id)
    paths = {
        "layout_url": layout_object_path(document_id),
        "items_parquet_url": items_object_path(document_id),
        "pages_parquet_url": pages_object_path(document_id),
    }

    await files.put_object(
        s3_client,
        workspace_name,
        paths["layout_url"],
        json.dumps(doc.export_to_dict(), ensure_ascii=False),
        content_type="application/json",
        metadata={"docling_version": doc.version, "document_id": document_id},
    )
    await files.put_object(
        s3_client,
        workspace_name,
        paths["items_parquet_url"],
        _to_parquet(items_table(doc, document_id)),
        content_type="application/vnd.apache.parquet",
        metadata={"document_id": document_id},
    )
    await files.put_object(
        s3_client,
        workspace_name,
        paths["pages_parquet_url"],
        _to_parquet(pages_table(doc, document_id)),
        content_type="application/vnd.apache.parquet",
        metadata={"document_id": document_id},
    )

    return paths


async def load_layout(
    s3_client: S3Client,
    workspace_name: str,
    document_id: UUID | str,
    object_path: Optional[str] = None,
) -> DoclingDocument:
    """Read the canonical JSON back into a `DoclingDocument`.

    A document written by a newer docling-core fails validation outright — the version validator
    demands an equal major and a minor no higher than the SDK's.
    """
    key = object_path or layout_object_path(document_id)
    response = await s3_client.get_object(Bucket=workspace_name, Key=key)
    raw = await response["Body"].read()
    return DoclingDocument.model_validate(json.loads(raw))
