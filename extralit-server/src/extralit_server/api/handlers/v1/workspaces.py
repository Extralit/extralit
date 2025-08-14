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

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security, status
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import WorkspacePolicy, WorkspaceUserPolicy, authorize
from extralit_server.api.schemas.v1.users import User as UserSchema
from extralit_server.api.schemas.v1.users import Users
from extralit_server.api.schemas.v1.workspaces import (
    Workspace as WorkspaceSchema,
)
from extralit_server.api.schemas.v1.workspaces import (
    WorkspaceCreate,
    Workspaces,
    WorkspaceUserCreate,
)
from extralit_server.contexts import accounts, files
from extralit_server.database import get_async_db
from extralit_server.errors import GenericServerError
from extralit_server.errors.future import NotFoundError, NotUniqueError, UnprocessableEntityError
from extralit_server.models import User, Workspace, WorkspaceUser
from extralit_server.security import auth

router = APIRouter(tags=["workspaces"])


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceSchema)
async def get_workspace(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    return await Workspace.get_or_raise(db, workspace_id)


@router.post("/workspaces", status_code=status.HTTP_201_CREATED, response_model=WorkspaceSchema)
async def create_workspace(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_create: WorkspaceCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
    minio_client: Annotated[Minio | files.LocalFileStorage, Depends(files.get_minio_client)],
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
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
    minio_client: Annotated[Minio | files.LocalFileStorage, Depends(files.get_minio_client)],
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
        print(f"Error deleting bucket for workspace {workspace.name}: {e!s}")

    try:
        return await accounts.delete_workspace(db, workspace)
    except NotUniqueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Error deleting workspace {workspace.id}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting workspace: {e!s}"
        )


@router.get("/me/workspaces")
async def list_workspaces_me(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
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
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WorkspaceUserPolicy.list(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)

    await workspace.awaitable_attrs.users

    return Users(items=workspace.users)


@router.post("/workspaces/{workspace_id}/users", status_code=status.HTTP_201_CREATED, response_model=UserSchema)
async def create_workspace_user(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    workspace_user_create: WorkspaceUserCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
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
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    user_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    workspace_user = await WorkspaceUser.get_by_or_raise(db, workspace_id=workspace_id, user_id=user_id)

    await authorize(current_user, WorkspaceUserPolicy.delete(workspace_user))

    await accounts.delete_workspace_user(db, workspace_user)

    return await workspace_user.awaitable_attrs.user
