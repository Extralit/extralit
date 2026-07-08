"""Business logic for v2 Schemas and their object-store-backed versions."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2.schema_bodies import derive_columns_cache
from extralit_server.enums import SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client


def object_key_for(schema_id: UUID, version: int) -> str:
    return f"schemas/{schema_id}/v{version}.json"


async def create_schema(
    db: AsyncSession,
    *,
    name: str,
    workspace_id: UUID,
    settings: dict[str, Any] | None = None,
) -> Schema:
    return await Schema.create(
        db,
        name=name,
        workspace_id=workspace_id,
        settings=settings or {},
        status=SchemaStatus.draft,
    )


async def get_schema(db: AsyncSession, schema_id: UUID) -> Schema | None:
    return await Schema.get(db, schema_id)


async def list_schemas(db: AsyncSession, *, workspace_id: UUID | None = None) -> list[Schema]:
    stmt = select(Schema)
    if workspace_id is not None:
        stmt = stmt.filter_by(workspace_id=workspace_id)
    stmt = stmt.order_by(Schema.inserted_at)
    return (await db.execute(stmt)).scalars().all()


async def update_schema(
    db: AsyncSession,
    schema: Schema,
    *,
    name: str | None = None,
    settings: dict[str, Any] | None = None,
) -> Schema:
    values: dict[str, Any] = {}
    if name is not None:
        values["name"] = name
    if settings is not None:
        values["settings"] = settings
    if not values:
        return schema
    # replace_dict=True gives PUT semantics: a provided `settings` payload replaces the
    # stored dict wholesale. CRUDMixin.fill() otherwise merges dicts, which would make
    # removing a settings key impossible.
    return await schema.update(db, replace_dict=True, **values)


async def delete_schema(db: AsyncSession, schema: Schema) -> Schema:
    return await schema.delete(db)


async def _next_version_number(db: AsyncSession, schema_id: UUID) -> int:
    versions = (await db.execute(select(SchemaVersion).filter_by(schema_id=schema_id))).scalars().all()
    return (max((v.version for v in versions), default=0)) + 1


async def publish_version(
    db: AsyncSession,
    s3_client: "S3Client",
    schema: Schema,
    *,
    body: str,
    bucket: str,
    review_widgets: dict[str, dict[str, Any]] | None = None,
    created_by: UUID | None = None,
) -> SchemaVersion:
    """Upload a Pandera body to the object store and register a new SchemaVersion.

    `review_widgets` is the out-of-band per-column widget overlay (spec §13); it is
    persisted on the version and merged into the derived `columns_cache`.
    """
    review_widgets = review_widgets or {}
    next_version = await _next_version_number(db, schema.id)
    key = object_key_for(schema.id, next_version)

    metadata = await files_ctx.put_object(s3_client, bucket, key, body, content_type="application/json")

    parent = await db.get(SchemaVersion, schema.current_version_id) if schema.current_version_id else None

    version = await SchemaVersion.create(
        db,
        schema_id=schema.id,
        version=next_version,
        object_key=key,
        object_version_id=getattr(metadata, "version_id", None),
        etag=metadata.etag,
        checksum=files_ctx.compute_hash(body.encode("utf-8")),
        parent_version_id=parent.id if parent else None,
        columns_cache=derive_columns_cache(body, review_widgets),
        review_widgets=review_widgets,
        created_by=created_by,
        autocommit=False,
    )
    # Flush so the version row (and its uuid `id`, a flush-time default) is persisted before we
    # point `schema.current_version_id` at it. Doing both in one flush would form a schemas<->
    # schema_versions FK cycle and leave version.id unset.
    await db.flush()
    await schema.update(db, current_version_id=version.id, status=SchemaStatus.published, autocommit=False)
    await db.commit()
    return version
