# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from uuid import UUID
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from minio import Minio

from argilla_server.api.policies.v1 import WorkspacePolicy, WorkspaceUserPolicy, authorize
from argilla_server.api.schemas.v1.users import User as UserSchema
from argilla_server.api.schemas.v1.users import Users
from argilla_server.api.schemas.v1.workspaces import (
    Workspace as WorkspaceSchema,
)
from argilla_server.api.schemas.v1.workspaces import (
    WorkspaceCreate,
    Workspaces,
    WorkspaceUserCreate,
    WorkspaceSchemaConfiguration,
    WorkspaceSchemaConfigurationUpdate,
    WorkspaceSchemaValidationResponse,
    SchemaValidationResult,
    SchemaSyncRequest,
    SchemaSyncResponse,
)
from argilla_server.contexts import accounts, files
from argilla_server.database import get_async_db
from argilla_server.errors import GenericServerError
from argilla_server.errors.future import NotFoundError, UnprocessableEntityError, NotUniqueError
from argilla_server.models import User, Workspace, WorkspaceUser
from argilla_server.security import auth
from argilla_server.contexts.schemas import SchemaService

router = APIRouter(tags=["workspaces"])


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceSchema)
async def get_workspace(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    return await Workspace.get_or_raise(db, workspace_id)


@router.post("/workspaces", status_code=status.HTTP_201_CREATED, response_model=WorkspaceSchema)
async def create_workspace(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_create: WorkspaceCreate,
    current_user: User = Security(auth.get_current_user),
    minio_client: Union[Minio, files.LocalFileStorage] = Depends(files.get_storage_client),
):
    await authorize(current_user, WorkspacePolicy.create)

    try:
        files.create_bucket(minio_client, workspace_create.name)
    except Exception as e:
        raise GenericServerError(e)

    try:
        workspace = await accounts.create_workspace(db, workspace_create.model_dump())
    except NotUniqueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return workspace


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceSchema)
async def delete_workspace(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    current_user: User = Security(auth.get_current_user),
    minio_client: Union[Minio, files.LocalFileStorage] = Depends(files.get_storage_client),
):
    await authorize(current_user, WorkspacePolicy.delete)

    try:
        workspace = await Workspace.get_or_raise(db, workspace_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        await files.delete_bucket(minio_client, workspace.name)
    except Exception as e:
        # Log the error but continue with workspace deletion
        print(f"Error deleting bucket for workspace {workspace.name}: {str(e)}")

    try:
        return await accounts.delete_workspace(db, workspace)
    except NotUniqueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Error deleting workspace {workspace.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting workspace: {str(e)}"
        )


@router.get("/me/workspaces", response_model=Workspaces)
async def list_workspaces_me(
    *,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
) -> Workspaces:
    await authorize(current_user, WorkspacePolicy.list_workspaces_me)

    if current_user.is_owner:
        workspaces = await accounts.list_workspaces(db)
    else:
        workspaces = await accounts.list_workspaces_by_user_id(db, current_user.id)

    return Workspaces(items=workspaces)


@router.get("/workspaces/{workspace_id}/users", response_model=Users)
async def list_workspace_users(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, WorkspaceUserPolicy.list(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)

    await workspace.awaitable_attrs.users

    return Users(items=workspace.users)


@router.post("/workspaces/{workspace_id}/users", status_code=status.HTTP_201_CREATED, response_model=UserSchema)
async def create_workspace_user(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    workspace_user_create: WorkspaceUserCreate,
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, WorkspaceUserPolicy.create)

    workspace = await Workspace.get_or_raise(db, workspace_id)

    try:
        user = await User.get_or_raise(db, workspace_user_create.user_id)
    except NotFoundError as e:
        raise UnprocessableEntityError(e.message)

    workspace_user = await accounts.create_workspace_user(db, {"workspace_id": workspace.id, "user_id": user.id})

    return workspace_user.user


@router.delete("/workspaces/{workspace_id}/users/{user_id}", response_model=UserSchema)
async def delete_workspace_user(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    user_id: UUID,
    current_user: User = Security(auth.get_current_user),
):
    workspace_user = await WorkspaceUser.get_by_or_raise(db, workspace_id=workspace_id, user_id=user_id)

    await authorize(current_user, WorkspaceUserPolicy.delete(workspace_user))

    await accounts.delete_workspace_user(db, workspace_user)

    return await workspace_user.awaitable_attrs.user


def _get_schema_service() -> SchemaService:
    """Get a SchemaService instance with the appropriate client."""
    minio_client = files.get_storage_client()
    if minio_client is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage client not available")
    return SchemaService(minio_client)


@router.get("/workspaces/{workspace_id}/schema-configuration", response_model=WorkspaceSchemaConfiguration)
async def get_workspace_schema_configuration(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    current_user: User = Security(auth.get_current_user),
):
    """Get the schema configuration for a workspace."""
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    schema_service = _get_schema_service()

    config = await schema_service.get_workspace_schema_configuration(workspace)
    return WorkspaceSchemaConfiguration(**config.get("schema_configuration", {"schemas": [], "last_sync": None}))


@router.put("/workspaces/{workspace_id}/schema-configuration", response_model=WorkspaceSchemaConfiguration)
async def update_workspace_schema_configuration(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    config_update: WorkspaceSchemaConfigurationUpdate,
    current_user: User = Security(auth.get_current_user),
):
    """Update the schema configuration for a workspace."""
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    schema_service = _get_schema_service()

    # Convert to dict for storage
    config_dict = config_update.schema_configuration.model_dump()

    await schema_service.update_workspace_schema_configuration(db, workspace, config_dict)

    return config_update.schema_configuration


@router.post("/workspaces/{workspace_id}/schemas/{schema_name}/sync", response_model=SchemaSyncResponse)
async def sync_workspace_schema(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    schema_name: str,
    sync_request: SchemaSyncRequest = SchemaSyncRequest(),
    current_user: User = Security(auth.get_current_user),
):
    """Sync a specific schema from S3 to workspace metadata."""
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    schema_service = _get_schema_service()

    try:
        updated_config = await schema_service.sync_s3_schema_to_metadata(
            db, workspace, schema_name, sync_request.prefix
        )

        return SchemaSyncResponse(
            schema_configuration=WorkspaceSchemaConfiguration(**updated_config),
            schemas_synced=1,
            message=f"Successfully synced schema '{schema_name}' from S3",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to sync schema '{schema_name}': {str(e)}"
        )


@router.post("/workspaces/{workspace_id}/schemas/sync-all", response_model=SchemaSyncResponse)
async def sync_all_workspace_schemas(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    sync_request: SchemaSyncRequest = SchemaSyncRequest(),
    current_user: User = Security(auth.get_current_user),
):
    """Sync all schemas from S3 to workspace metadata."""
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    schema_service = _get_schema_service()

    try:
        updated_config = await schema_service.sync_all_s3_schemas_to_metadata(db, workspace, sync_request.prefix)

        schemas_count = len(updated_config.get("schemas", []))

        return SchemaSyncResponse(
            schema_configuration=WorkspaceSchemaConfiguration(**updated_config),
            schemas_synced=schemas_count,
            message=f"Successfully synced {schemas_count} schemas from S3",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to sync schemas: {str(e)}"
        )


@router.get("/workspaces/{workspace_id}/schemas/validate", response_model=WorkspaceSchemaValidationResponse)
async def validate_workspace_schemas(
    *,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID,
    current_user: User = Security(auth.get_current_user),
):
    """Validate all schemas in a workspace."""
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    schema_service = _get_schema_service()

    try:
        validation_results = await schema_service.validate_all_schemas(workspace)

        results = []
        all_valid = True

        for schema_name, (is_valid, error_message) in validation_results.items():
            results.append(
                SchemaValidationResult(schema_name=schema_name, is_valid=is_valid, error_message=error_message)
            )
            if not is_valid:
                all_valid = False

        return WorkspaceSchemaValidationResponse(validation_results=results, all_valid=all_valid)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to validate schemas: {str(e)}"
        )
