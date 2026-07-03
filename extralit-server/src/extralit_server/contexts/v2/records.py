"""Business logic for v2 Records: validated bulk-upsert, listing, deletion, reference view."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v2.records import RecordUpsert
from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2.schema_bodies import SchemaValidationError, validate_record_fields
from extralit_server.enums import V2RecordStatus
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.v2 import Schema, SchemaVersion, V2Record

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client


async def _fetch_body_json(s3_client: "S3Client", bucket: str, version: SchemaVersion) -> str:
    """Fetch a schema version's Pandera body from the object store, pinned to its S3 version."""
    obj = await files_ctx.get_object(s3_client, bucket, version.object_key, version_id=version.object_version_id)
    data = await obj.response.read()
    return data.decode("utf-8") if isinstance(data, bytes) else data


async def bulk_upsert_records(
    db: AsyncSession,
    s3_client: "S3Client",
    schema: Schema,
    *,
    items: list[RecordUpsert],
    bucket: str,
) -> list[V2Record]:
    """Validate every item against its (pinned or current) schema version, then upsert.

    All-or-nothing: every item is validated against the Pandera body before any row is
    written, so a single invalid item fails the whole request without partial writes.
    Identity for updates is (schema_id, external_id); items without an external_id always
    insert. Each distinct schema version's body is fetched from the object store once per
    request, never per record.

    Update semantics are patch-like for `metadata`/`status`: an omitted (None) value
    preserves the existing row's value rather than clearing it (see RecordUpsert docs);
    `fields`, `reference`, and the resolved schema_version_id are always overwritten.
    """
    default_version_id = schema.current_version_id
    if default_version_id is None:
        raise UnprocessableEntityError(
            f"Schema `{schema.id}` has no published version; publish a version before writing records"
        )

    provided = [item.external_id for item in items if item.external_id is not None]
    if len(provided) != len(set(provided)):
        raise UnprocessableEntityError("Duplicate `external_id` values in the same bulk-upsert payload")

    # Resolve distinct pinned versions; every pin must belong to this schema.
    version_ids = {item.schema_version_id or default_version_id for item in items}
    versions: dict[UUID, SchemaVersion] = {}
    for version_id in version_ids:
        version = await SchemaVersion.get(db, version_id)
        if version is None or version.schema_id != schema.id:
            raise UnprocessableEntityError(f"Schema version `{version_id}` does not belong to schema `{schema.id}`")
        versions[version_id] = version

    bodies: dict[UUID, str] = {}
    for version_id, version in versions.items():
        bodies[version_id] = await _fetch_body_json(s3_client, bucket, version)

    errors: list[str] = []
    validated_fields: list[dict] = []
    for idx, item in enumerate(items):
        version_id = item.schema_version_id or default_version_id
        try:
            validated_fields.append(validate_record_fields(bodies[version_id], item.fields))
        except SchemaValidationError as exc:
            validated_fields.append({})
            errors.extend(
                f"items[{idx}]: column={e['column']!r} check={e['check']!r} error={e['error']}" for e in exc.errors
            )
    if errors:
        raise UnprocessableEntityError("Record fields failed schema validation: " + "; ".join(errors))

    # v1-style merge (contexts/records_bulk.py): external_id is nullable, which rules out a
    # single ON CONFLICT statement, and we must return ORM rows in input order.
    existing: dict[str, V2Record] = {}
    if provided:
        stmt = select(V2Record).where(V2Record.schema_id == schema.id, V2Record.external_id.in_(provided))
        existing = {r.external_id: r for r in (await db.execute(stmt)).scalars().all()}

    result: list[V2Record] = []
    for item, fields in zip(items, validated_fields, strict=False):
        version_id = item.schema_version_id or default_version_id
        record = existing.get(item.external_id) if item.external_id is not None else None
        if record is None:
            record = V2Record(
                schema_id=schema.id,
                schema_version_id=version_id,
                reference=item.reference,
                external_id=item.external_id,
                fields=fields,
                metadata_=item.metadata,
                status=item.status or V2RecordStatus.pending,
            )
            db.add(record)
        else:
            record.schema_version_id = version_id
            record.reference = item.reference
            record.fields = fields
            if item.metadata is not None:
                record.metadata_ = item.metadata
            if item.status is not None:
                record.status = item.status
        result.append(record)

    await db.flush()
    await db.commit()
    return result


async def list_records(
    db: AsyncSession,
    schema: Schema,
    *,
    offset: int,
    limit: int,
    status: V2RecordStatus | None = None,
    reference: str | None = None,
) -> tuple[list[V2Record], int]:
    filters = [V2Record.schema_id == schema.id]
    if status is not None:
        filters.append(V2Record.status == status)
    if reference is not None:
        filters.append(V2Record.reference == reference)

    total = (await db.execute(select(func.count(V2Record.id)).where(*filters))).scalar_one()
    stmt = select(V2Record).where(*filters).order_by(V2Record.inserted_at.asc()).offset(offset).limit(limit)
    return (await db.execute(stmt)).scalars().all(), total


async def delete_records(db: AsyncSession, schema: Schema, record_ids: list[UUID]) -> int:
    result = await db.execute(sql_delete(V2Record).where(V2Record.id.in_(record_ids), V2Record.schema_id == schema.id))
    await db.commit()
    return result.rowcount


async def list_records_by_reference(db: AsyncSession, *, workspace_id: UUID, reference: str) -> list[V2Record]:
    stmt = (
        select(V2Record)
        .join(Schema, V2Record.schema_id == Schema.id)
        .where(Schema.workspace_id == workspace_id, V2Record.reference == reference)
        .order_by(V2Record.schema_id, V2Record.inserted_at.asc())
    )
    return (await db.execute(stmt)).scalars().all()
