from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import SchemaPolicy, authorize
from extralit_server.api.schemas.v2.records import (
    DELETE_RECORDS_LIMIT,
    LIST_RECORDS_LIMIT_DEFAULT,
    LIST_RECORDS_LIMIT_LE,
    Records,
    RecordsBulkUpsert,
)
from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2 import records as records_ctx
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.database import get_async_db
from extralit_server.enums import V2RecordStatus
from extralit_server.errors.future import NotFoundError, UnprocessableEntityError
from extralit_server.models import User, Workspace
from extralit_server.models.v2 import Schema
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
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.upsert_records(schema))
    workspace = await Workspace.get_or_raise(db, schema.workspace_id)
    records = await records_ctx.bulk_upsert_records(db, s3_client, schema, items=payload.items, bucket=workspace.name)
    return Records(items=records, total=len(records))


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
    current_user: Annotated[User, Security(auth.get_current_user)],
    ids: Annotated[str, Query(description="Comma-separated record ids to delete")],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.delete_records(schema))
    record_ids = parse_uuids(ids)
    if len(record_ids) == 0:
        raise UnprocessableEntityError("No record IDs provided")
    if len(record_ids) > DELETE_RECORDS_LIMIT:
        raise UnprocessableEntityError(f"Cannot delete more than {DELETE_RECORDS_LIMIT} records at once")
    await records_ctx.delete_records(db, schema, record_ids)
