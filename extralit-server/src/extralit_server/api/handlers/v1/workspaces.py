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
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import WorkspacePolicy, WorkspaceUserPolicy, authorize
from extralit_server.api.schemas.v1.users import User as UserSchema
from extralit_server.api.schemas.v1.users import Users
from extralit_server.api.schemas.v1.workspaces import (
    Workspace as WorkspaceSchema,
)
from extralit_server.api.schemas.v1.workspaces import (
    WorkspaceCreate,
    WorkspaceDoctorCheckResult,
    WorkspaceDoctorResponse,
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
    s3_client=Depends(files.get_s3_client),
):
    await authorize(current_user, WorkspacePolicy.create)

    try:
        await files.create_bucket(s3_client, workspace_create.name)
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
    s3_client=Depends(files.get_s3_client),
):
    await authorize(current_user, WorkspacePolicy.delete)

    try:
        workspace = await Workspace.get_or_raise(db, workspace_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        await files.delete_bucket(s3_client, workspace.name)
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


@router.post("/workspaces/{workspace_id}/doctor", response_model=WorkspaceDoctorResponse)
async def workspace_doctor(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
    s3_client=Depends(files.get_s3_client),
    autofix: bool = True,
):
    """
    Run diagnostics on a workspace and optionally auto-fix issues.
    
    Checks:
    - S3 bucket exists (can auto-fix)
    - Bucket has proper versioning policy (informational)
    - RQ worker pool connectivity (informational)
    """
    await authorize(current_user, WorkspacePolicy.get(workspace_id))

    workspace = await Workspace.get_or_raise(db, workspace_id)
    checks = []
    
    # Check 1: S3 bucket exists
    bucket_exists = await files.bucket_exists(s3_client, workspace.name)
    if bucket_exists:
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="s3_bucket",
                status="ok",
                message=f"S3 bucket '{workspace.name}' exists",
                fixed=False,
            )
        )
    else:
        if autofix:
            try:
                await files.create_bucket(s3_client, workspace.name)
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="s3_bucket",
                        status="ok",
                        message=f"S3 bucket '{workspace.name}' was missing and has been created",
                        fixed=True,
                    )
                )
            except Exception as e:
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="s3_bucket",
                        status="error",
                        message=f"S3 bucket '{workspace.name}' does not exist and failed to create: {e!s}",
                        fixed=False,
                    )
                )
        else:
            checks.append(
                WorkspaceDoctorCheckResult(
                    check_name="s3_bucket",
                    status="error",
                    message=f"S3 bucket '{workspace.name}' does not exist (autofix disabled)",
                    fixed=False,
                )
            )
    
    # Check 2: Bucket versioning policy
    if bucket_exists or any(check.check_name == "s3_bucket" and check.fixed for check in checks):
        versioning = await files.get_bucket_versioning(s3_client, workspace.name)
        if versioning:
            if versioning["status"] == "Enabled":
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="bucket_versioning",
                        status="ok",
                        message=f"Bucket versioning is enabled (Status: {versioning['status']})",
                        fixed=False,
                    )
                )
            else:
                checks.append(
                    WorkspaceDoctorCheckResult(
                        check_name="bucket_versioning",
                        status="warning",
                        message=f"Bucket versioning is not enabled (Status: {versioning['status']})",
                        fixed=False,
                    )
                )
        else:
            checks.append(
                WorkspaceDoctorCheckResult(
                    check_name="bucket_versioning",
                    status="warning",
                    message="Could not retrieve bucket versioning configuration",
                    fixed=False,
                )
            )
    
    # Check 3: RQ worker pool connectivity
    try:
        from extralit_server.jobs.queues import DEFAULT_QUEUE
        
        # Try to ping Redis through the queue connection
        connection = DEFAULT_QUEUE.connection
        connection.ping()
        
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="rq_worker_pool",
                status="ok",
                message="Redis Queue worker pool is reachable",
                fixed=False,
            )
        )
    except Exception as e:
        checks.append(
            WorkspaceDoctorCheckResult(
                check_name="rq_worker_pool",
                status="warning",
                message=f"Could not connect to RQ worker pool: {e!s}",
                fixed=False,
            )
        )
    
    # Determine overall status
    has_errors = any(check.status == "error" for check in checks)
    has_fixed = any(check.fixed for check in checks)
    has_warnings = any(check.status == "warning" for check in checks)
    
    if has_errors:
        overall_status = "issues_found"
    elif has_fixed:
        overall_status = "issues_fixed"
    elif has_warnings:
        overall_status = "issues_found"
    else:
        overall_status = "healthy"
    
    return WorkspaceDoctorResponse(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        checks=checks,
        overall_status=overall_status,
    )
