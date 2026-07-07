from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import SchemaPolicy, authorize
from extralit_server.api.schemas.v2.records import (
    DELETE_RECORDS_LIMIT,
    LIST_RECORDS_LIMIT_DEFAULT,
    LIST_RECORDS_LIMIT_LE,
    RecordRead,
    Records,
    RecordsBulkUpsert,
    ReferenceGroup,
    ReferenceView,
)
from extralit_server.api.schemas.v2.search import RecordSearchQuery
from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2 import index_sync
from extralit_server.contexts.v2 import records as records_ctx
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.database import get_async_db
from extralit_server.enums import V2RecordStatus
from extralit_server.errors.future import NotFoundError, UnprocessableEntityError
from extralit_server.index import get_index_engine
from extralit_server.index.base import IndexEngine, IndexFilter
from extralit_server.models import User, Workspace
from extralit_server.models.v2 import Schema, V2Record
from extralit_server.security import auth
from extralit_server.utils import parse_uuids

router = APIRouter(tags=["v2: records"])


async def _get_schema_or_404(db: AsyncSession, schema_id: UUID) -> Schema:
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return schema


# AIP-136-style custom method (spec §7); Starlette treats the `:` as a literal character.
@router.post("/schemas/{schema_id}/records:bulk-upsert", response_model=Records)
async def bulk_upsert_schema_records(
    *,
    schema_id: UUID,
    payload: RecordsBulkUpsert,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    s3_client=Depends(files_ctx.get_s3_client),
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.upsert_records(schema))
    workspace = await Workspace.get_or_raise(db, schema.workspace_id)
    records = await records_ctx.bulk_upsert_records(db, s3_client, schema, items=payload.items, bucket=workspace.name)
    await index_sync.sync_upserted_records(index_engine, db, schema, records)
    return Records(items=records, total=len(records))


@router.post("/schemas/{schema_id}/records:search", response_model=Records)
async def search_schema_records(
    *,
    schema_id: UUID,
    payload: RecordSearchQuery,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Full-text (BM25) + scalar-filter search over a schema's records.

    Lance supplies matching record ids and scores; payloads are hydrated from Postgres
    (the source of truth) and returned in the engine's hit order. `total` is the engine's
    total match count, which may exceed the returned page.
    """
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.list_records(schema))

    filters = [IndexFilter(column=f.column, op=f.op, value=f.value) for f in payload.filters]
    result = await index_engine.search(
        schema.id, text=payload.text, filters=filters, offset=payload.offset, limit=payload.limit
    )
    if not result.hits:
        return Records(items=[], total=result.total)

    hit_ids = [hit.record_id for hit in result.hits]
    rows = (
        (await db.execute(select(V2Record).where(V2Record.id.in_(hit_ids), V2Record.schema_id == schema.id)))
        .scalars()
        .all()
    )
    by_id = {row.id: row for row in rows}
    ordered = [by_id[rid] for rid in hit_ids if rid in by_id]  # preserve Lance order; skip PG-missing (stale index)
    return Records(items=[RecordRead.model_validate(r) for r in ordered], total=result.total)


@router.get("/schemas/{schema_id}/records", response_model=Records)
async def list_schema_records(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=LIST_RECORDS_LIMIT_LE)] = LIST_RECORDS_LIMIT_DEFAULT,
    status_filter: Annotated[V2RecordStatus | None, Query(alias="status")] = None,
    reference: Annotated[str | None, Query()] = None,
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.list_records(schema))
    records, total = await records_ctx.list_records(
        db, schema, offset=offset, limit=limit, status=status_filter, reference=reference
    )
    return Records(items=records, total=total)


@router.delete("/schemas/{schema_id}/records", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schema_records(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    ids: Annotated[str, Query(description="Comma-separated record ids to delete")],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.delete_records(schema))
    # Reject an empty param up front: parse_uuids("") would 422 with a generic
    # "Invalid UUID format" before a post-parse length check could run.
    if not ids.strip():
        raise UnprocessableEntityError("No record IDs provided")
    record_ids = parse_uuids(ids)
    if len(record_ids) > DELETE_RECORDS_LIMIT:
        raise UnprocessableEntityError(f"Cannot delete more than {DELETE_RECORDS_LIMIT} records at once")
    await records_ctx.delete_records(db, schema, record_ids)
    await index_sync.sync_deleted_records(index_engine, schema, record_ids)


# `:path` converter: references are free-form join keys and DOIs contain slashes
# (e.g. 10.1000/j.foo.2020.01); the default converter would 404 on them.
@router.get("/references/{reference:path}", response_model=ReferenceView)
async def get_reference_view(
    *,
    reference: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID, Query(description="Workspace to scope the cross-schema view (required)")],
):
    """The document's project-level extraction view: all v2 records across every schema in
    the workspace that share this `reference` (spec §6), grouped per schema.

    An unknown reference returns an empty view (200): the reference is a free-form join
    key, not an entity, so "no extractions yet" is not an error.
    """
    # workspace_id is required so the view is scoped + authorized (mirrors GET /schemas).
    await authorize(current_user, SchemaPolicy.list(workspace_id))
    records = await records_ctx.list_records_by_reference(db, workspace_id=workspace_id, reference=reference)

    schema_ids = {r.schema_id for r in records}
    schemas_by_id = {
        s.id: s for s in await schemas_ctx.list_schemas(db, workspace_id=workspace_id) if s.id in schema_ids
    }

    groups = [
        ReferenceGroup(
            schema_id=schema_id,
            schema_name=schemas_by_id[schema_id].name,
            records=[RecordRead.model_validate(r) for r in records if r.schema_id == schema_id],
        )
        for schema_id in sorted(schema_ids, key=lambda schema_id: schemas_by_id[schema_id].name)
    ]
    return ReferenceView(reference=reference, groups=groups, total_records=len(records))
