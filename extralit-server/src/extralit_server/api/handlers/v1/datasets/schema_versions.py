from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import DatasetPolicy, authorize
from extralit_server.api.schemas.v1.schema_versions import SchemaVersionCreate, SchemaVersionRead
from extralit_server.contexts import files as files_ctx
from extralit_server.contexts import schema_versions
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError
from extralit_server.models import Dataset, User
from extralit_server.search_engine import SearchEngine, get_search_engine
from extralit_server.security import auth

router = APIRouter()


@router.post(
    "/datasets/{dataset_id}/schema-versions",
    status_code=status.HTTP_201_CREATED,
    response_model=SchemaVersionRead,
)
async def publish_schema_version(
    *,
    dataset_id: UUID,
    version_create: SchemaVersionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    s3_client=Depends(files_ctx.get_s3_client),
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id, options=[selectinload(Dataset.workspace)])
    await authorize(current_user, DatasetPolicy.publish(dataset))

    return await schema_versions.publish_version(
        db,
        search_engine,
        s3_client,
        dataset,
        body=version_create.body,
        # One bucket per workspace, named exactly Workspace.name — contexts/files.py:381.
        bucket=dataset.workspace.name,
        review_widgets=version_create.review_widgets,
        created_by=current_user.id,
    )


@router.get("/datasets/{dataset_id}/schema-versions", response_model=list[SchemaVersionRead])
async def list_schema_versions(
    *,
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)
    await authorize(current_user, DatasetPolicy.get(dataset))

    return await schema_versions.list_versions(db, dataset)


@router.get("/datasets/{dataset_id}/schema-versions/{version}", response_model=SchemaVersionRead)
async def get_schema_version(
    *,
    dataset_id: UUID,
    version: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)
    await authorize(current_user, DatasetPolicy.get(dataset))

    schema_version = await schema_versions.get_version_by_number(db, dataset.id, version)
    if schema_version is None:
        raise NotFoundError(f"SchemaVersion {version} not found for dataset {dataset_id}")

    return schema_version
