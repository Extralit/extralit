"""Versioned, object-store-backed Pandera schema bodies for a dataset.

A dataset's record shape is declared by a Pandera schema whose body lives in the
workspace bucket. Publishing a version uploads the body, registers a `SchemaVersion`
pointer, and projects every declared column into a `Field` row -- so the `fields`
table is the queryable column manifest and there is no cached copy of it.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pandera.pandas as pa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.contexts import files as files_ctx
from extralit_server.enums import DatasetStatus, FieldType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.database import Dataset, Field, SchemaVersion
from extralit_server.search_engine import SearchEngine

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client


def object_key_for(dataset_id: UUID, version: int) -> str:
    return f"schemas/{dataset_id}/v{version}.json"


def derive_column_fields(
    body_json: str, review_widgets: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Project a Pandera body into `Field` row payloads, one per declared column.

    `review_widgets` is the out-of-band per-column widget overlay: Pandera's `to_json`
    drops `Column.metadata`, so widget config cannot ride inside the body itself.
    """
    review_widgets = review_widgets or {}
    try:
        schema = pa.DataFrameSchema.from_json(body_json)
    except Exception as ex:
        raise UnprocessableEntityError(f"schema body is not a valid Pandera DataFrameSchema: {ex}") from ex

    return [
        {
            "name": name,
            "title": name,
            # A column is an ingestion input, never annotator-required.
            "required": False,
            "settings": {
                "type": FieldType.column,
                "dtype": str(column.dtype),
                "nullable": bool(column.nullable),
                "review": review_widgets.get(name),
            },
        }
        for name, column in schema.columns.items()
    ]


async def _next_version_number(db: AsyncSession, dataset_id: UUID) -> int:
    stmt = select(SchemaVersion.version).where(SchemaVersion.dataset_id == dataset_id)
    return max((await db.execute(stmt)).scalars().all(), default=0) + 1


async def publish_version(
    db: AsyncSession,
    search_engine: SearchEngine,
    s3_client: "S3Client",
    dataset: Dataset,
    *,
    body: str,
    bucket: str,
    review_widgets: dict[str, dict[str, Any]] | None = None,
    created_by: UUID | None = None,
) -> SchemaVersion:
    """Upload a body, register the version, materialize its column fields, publish the dataset."""
    # Parse before any write so an invalid body leaves no version row and no S3 object.
    field_payloads = derive_column_fields(body, review_widgets)

    next_version = await _next_version_number(db, dataset.id)
    key = object_key_for(dataset.id, next_version)
    metadata = await files_ctx.put_object(s3_client, bucket, key, body, content_type="application/json")

    parent_id = dataset.current_schema_version_id

    version = await SchemaVersion.create(
        db,
        dataset_id=dataset.id,
        version=next_version,
        object_key=key,
        object_version_id=getattr(metadata, "version_id", None),
        etag=metadata.etag,
        checksum=files_ctx.compute_hash(body.encode("utf-8")),
        parent_version_id=parent_id,
        created_by=created_by,
        autocommit=False,
    )
    # Flush so `version.id` (a flush-time default) exists before `datasets` points at it.
    # Doing both in one flush would form a datasets<->schema_versions FK cycle.
    await db.flush()

    if field_payloads:
        # `Field.upsert_many` raises on an empty `objects` list (models/mixins.py); a
        # column-less Pandera body is a legal, if degenerate, schema, so skip rather
        # than reject -- a business rule shouldn't hinge on a persistence-layer guard.
        await Field.upsert_many(
            db,
            objects=[{**payload, "dataset_id": dataset.id} for payload in field_payloads],
            constraints=[Field.name, Field.dataset_id],
            autocommit=False,
        )

    await dataset.update(db, current_schema_version_id=version.id, status=DatasetStatus.ready, autocommit=False)
    await db.commit()

    # Post-commit, outside the transaction -- the repo-wide convention for index side effects.
    await search_engine.create_index(dataset)

    return version


async def list_versions(db: AsyncSession, dataset: Dataset) -> list[SchemaVersion]:
    stmt = select(SchemaVersion).where(SchemaVersion.dataset_id == dataset.id).order_by(SchemaVersion.version)
    return list((await db.execute(stmt)).scalars().all())


async def get_version_by_number(db: AsyncSession, dataset_id: UUID, version: int) -> SchemaVersion | None:
    stmt = select(SchemaVersion).where(SchemaVersion.dataset_id == dataset_id, SchemaVersion.version == version)
    return (await db.execute(stmt)).scalar_one_or_none()
