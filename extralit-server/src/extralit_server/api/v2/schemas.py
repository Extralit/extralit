from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import SchemaPolicy, authorize
from extralit_server.api.schemas.v2.schemas import (
    SchemaCreate,
    SchemaRead,
    Schemas,
    SchemaUpdate,
    SchemaVersionCreate,
    SchemaVersionRead,
)
from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError
from extralit_server.models import User, Workspace
from extralit_server.models.v2 import Schema, SchemaVersion
from extralit_server.security import auth

router = APIRouter(tags=["v2: schemas"])


async def _get_schema_or_404(db: AsyncSession, schema_id: UUID) -> Schema:
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return schema


@router.post("/schemas", response_model=SchemaRead, status_code=status.HTTP_201_CREATED)
async def create_schema(
    *,
    payload: SchemaCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, SchemaPolicy.create(payload.workspace_id))
    return await schemas_ctx.create_schema(
        db,
        name=payload.name,
        kind=payload.kind,
        workspace_id=payload.workspace_id,
        settings=payload.settings,
    )


@router.get("/schemas", response_model=Schemas)
async def list_schemas(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID, Query(description="Workspace to list schemas for (required)")],
):
    # workspace_id is required so every list is scoped + authorized (no cross-workspace listing).
    await authorize(current_user, SchemaPolicy.list(workspace_id))
    items = await schemas_ctx.list_schemas(db, workspace_id=workspace_id)
    return Schemas(items=items)


@router.get("/schemas/{schema_id}", response_model=SchemaRead)
async def get_schema(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.get(schema))
    return schema


@router.put("/schemas/{schema_id}", response_model=SchemaRead)
async def update_schema(
    *,
    schema_id: UUID,
    payload: SchemaUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.update(schema))
    return await schemas_ctx.update_schema(db, schema, name=payload.name, settings=payload.settings)


@router.delete("/schemas/{schema_id}", response_model=SchemaRead)
async def delete_schema(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.delete(schema))
    return await schemas_ctx.delete_schema(db, schema)


@router.post(
    "/schemas/{schema_id}/versions",
    response_model=SchemaVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_schema_version(
    *,
    schema_id: UUID,
    payload: SchemaVersionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    s3_client=Depends(files_ctx.get_s3_client),
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.publish(schema))
    workspace = await Workspace.get_or_raise(db, schema.workspace_id)
    return await schemas_ctx.publish_version(
        db,
        s3_client,
        schema,
        body=payload.body,
        bucket=workspace.name,
        review_widgets=payload.review_widgets,
        created_by=current_user.id,
    )


@router.get("/schemas/{schema_id}/versions", response_model=list[SchemaVersionRead])
async def list_schema_versions(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.get(schema))
    return sorted(await schema.awaitable_attrs.versions, key=lambda v: v.version)


@router.get("/schemas/{schema_id}/columns", response_model=list[dict])
async def get_schema_columns(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.get(schema))
    if schema.current_version_id is None:
        return []
    version = await SchemaVersion.get(db, schema.current_version_id)
    return version.columns_cache if version else []
