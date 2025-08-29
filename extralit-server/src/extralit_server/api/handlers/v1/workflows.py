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

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import JobPolicy, authorize
from extralit_server.api.schemas.v1.workflows import (
    RestartWorkflowRequest,
    StartWorkflowRequest,
    StartWorkflowResponse,
    WorkflowStatusResponse,
)
from extralit_server.contexts.workflows import (
    get_workflow_status,
    get_workflow_statuses_by_reference,
    restart_failed_jobs_in_workflow,
)
from extralit_server.database import get_async_db
from extralit_server.models import User
from extralit_server.models.database import Document, DocumentWorkflow, Workspace
from extralit_server.security import auth
from extralit_server.workflows.documents import create_document_workflow

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["workflows"])


@router.post(
    "/workflows/start",
)
async def start_workflow(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    request: StartWorkflowRequest,
) -> StartWorkflowResponse:
    """Start PDF processing workflow for a document."""
    await authorize(current_user, JobPolicy.get)

    try:
        # Get document and validate it exists
        document = await db.get(Document, request.document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id `{request.document_id}` not found",
            )

        # Get workspace by name
        from sqlalchemy import select

        workspace_result = await db.execute(select(Workspace).where(Workspace.name == request.workspace_name))
        workspace = workspace_result.scalar_one_or_none()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace `{request.workspace_name}` not found",
            )

        # Check if workflow already exists
        existing_workflow = await DocumentWorkflow.get_by_document_id(db, request.document_id)
        if existing_workflow and not request.force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow already exists for document {request.document_id}. Use force=true to restart.",
            )

        # Generate reference if not provided
        reference = request.reference or f"doc_{str(request.document_id)[:8]}"

        # Get document S3 URL (assuming it's stored in document metadata or similar)
        # This is a placeholder - you'll need to implement the actual S3 URL retrieval
        s3_url = getattr(document, "s3_url", None) or f"s3://documents/{document.id}"

        # Start the workflow
        await create_document_workflow(
            document_id=request.document_id,
            s3_url=s3_url,
            reference=reference,
            workspace_name=request.workspace_name,
            workspace_id=workspace.id,
        )

        # Get the created workflow
        workflow = await DocumentWorkflow.get_by_document_id(db, request.document_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workflow record",
            )

        return StartWorkflowResponse(
            workflow_id=str(workflow.id),
            document_id=str(request.document_id),
            group_id=workflow.group_id,
            status=workflow.status,
            reference=reference,
        )

    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error starting workflow for document {request.document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {e!s}",
        )


@router.get("/workflows/status", response_model=list[WorkflowStatusResponse])
async def get_workflow_status_endpoint(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    document_id: Optional[UUID] = Query(None, description="Filter by document ID"),
    reference: Optional[str] = Query(None, description="Filter by document reference"),
    workspace_name: Optional[str] = Query(None, description="Filter by workspace name"),
) -> list[WorkflowStatusResponse] | None:
    """Get workflow status for documents."""
    await authorize(current_user, JobPolicy.get)

    try:
        if not document_id and not reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify either document_id or reference",
            )

        if document_id:
            # Get status for specific document
            workflow_status = await get_workflow_status(db, document_id)

            # Get workspace name if needed
            if workspace_name and workflow_status.get("workspace_id"):
                workspace = await db.get(Workspace, workflow_status["workspace_id"])
                if workspace and workspace.name != workspace_name:
                    return []  # Filter out if workspace doesn't match
                workflow_status["workspace_name"] = workspace.name if workspace else None

            return [_convert_to_workflow_status_response(workflow_status)]

        elif reference:
            # Get status for all documents with reference
            workflow_statuses = await get_workflow_statuses_by_reference(db, reference)

            results = []
            for workflow_status in workflow_statuses:
                # Get workspace name if needed
                if workspace_name and workflow_status.get("workspace_id"):
                    workspace = await db.get(Workspace, workflow_status["workspace_id"])
                    if workspace and workspace.name != workspace_name:
                        continue  # Skip if workspace doesn't match
                    workflow_status["workspace_name"] = workspace.name if workspace else None
                elif workflow_status.get("workspace_id"):
                    workspace = await db.get(Workspace, workflow_status["workspace_id"])
                    workflow_status["workspace_name"] = workspace.name if workspace else None

                results.append(_convert_to_workflow_status_response(workflow_status))

            return results

    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {e!s}",
        )


@router.post("/workflows/restart")
async def restart_workflow(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    request: RestartWorkflowRequest,
) -> StartWorkflowResponse:
    """Restart failed workflow jobs using RQ Groups."""
    await authorize(current_user, JobPolicy.get)

    try:
        # Get workflow
        workflow = await DocumentWorkflow.get_by_document_id(db, request.document_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow not found for document {request.document_id}",
            )

        # Check if workflow is resumable
        from extralit_server.contexts.workflows import is_workflow_resumable

        if not is_workflow_resumable(workflow.group_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow is not in a resumable state (no failed jobs found)",
            )

        # Restart failed jobs
        restart_result = await restart_failed_jobs_in_workflow(db, workflow)

        if not restart_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to restart workflow: {restart_result.get('error', 'Unknown error')}",
            )

        return StartWorkflowResponse(
            workflow_id=str(workflow.id),
            document_id=str(request.document_id),
            group_id=workflow.group_id,
            status="running",
            reference=workflow.reference,
            restarted_jobs=restart_result["restarted_jobs"],
        )

    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error restarting workflow for document {request.document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart workflow: {e!s}",
        )


@router.get(
    "/workflows/",
)
async def list_workflows(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_name: Optional[str] = Query(None, description="Filter by workspace name"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of workflows to return"),
) -> list[WorkflowStatusResponse]:
    """List workflows with optional filtering."""
    await authorize(current_user, JobPolicy.get)

    try:
        from sqlalchemy import select

        # Build query
        query = select(DocumentWorkflow).order_by(DocumentWorkflow.inserted_at.desc()).limit(limit)

        # Apply workspace filter
        if workspace_name:
            workspace_result = await db.execute(select(Workspace).where(Workspace.name == workspace_name))
            workspace = workspace_result.scalar_one_or_none()
            if not workspace:
                return []  # No workflows if workspace doesn't exist
            query = query.where(DocumentWorkflow.workspace_id == workspace.id)

        # Apply status filter
        if status_filter:
            query = query.where(DocumentWorkflow.status == status_filter)

        # Execute query
        result = await db.execute(query)
        workflows = result.scalars().all()

        # Convert to response format
        workflow_responses = []
        for workflow in workflows:
            try:
                # Get detailed workflow status
                workflow_status = await get_workflow_status(db, workflow.document_id)

                # Get workspace name
                workspace = await db.get(Workspace, workflow.workspace_id)
                workflow_status["workspace_name"] = workspace.name if workspace else None

                workflow_responses.append(_convert_to_workflow_status_response(workflow_status))

            except Exception as workflow_error:
                _LOGGER.warning(f"Error processing workflow {workflow.id}: {workflow_error}")
                # Add basic workflow info even if detailed status fails
                workflow_responses.append(
                    WorkflowStatusResponse(
                        workflow_id=str(workflow.id),
                        document_id=str(workflow.document_id),
                        group_id=workflow.group_id,
                        status="error",
                        progress=0.0,
                        reference=workflow.reference,
                        workspace_id=str(workflow.workspace_id),
                        workflow_type=workflow.workflow_type,
                        total_jobs=0,
                        completed_jobs=0,
                        failed_jobs=0,
                        running_jobs=0,
                        created_at=workflow.inserted_at,
                        updated_at=workflow.updated_at,
                        error=f"Error processing workflow: {workflow_error}",
                    )
                )

        return workflow_responses

    except Exception as e:
        _LOGGER.error(f"Error listing workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {e!s}",
        )


def _convert_to_workflow_status_response(workflow_status: dict) -> WorkflowStatusResponse:
    """Convert workflow status dictionary to response schema."""
    return WorkflowStatusResponse(
        workflow_id=str(workflow_status.get("workflow_id", "")),
        document_id=str(workflow_status.get("document_id", "")),
        group_id=workflow_status.get("group_id", ""),
        status=workflow_status.get("status", "unknown"),
        progress=workflow_status.get("progress", 0.0),
        reference=workflow_status.get("reference"),
        workspace_name=workflow_status.get("workspace_name"),
        workspace_id=str(workflow_status.get("workspace_id", "")),
        workflow_type=workflow_status.get("workflow_type", "unknown"),
        total_jobs=workflow_status.get("total_jobs", 0),
        completed_jobs=workflow_status.get("completed_jobs", 0),
        failed_jobs=workflow_status.get("failed_jobs", 0),
        running_jobs=workflow_status.get("running_jobs", 0),
        created_at=workflow_status.get("created_at"),
        updated_at=workflow_status.get("updated_at"),
        error=workflow_status.get("error"),
        jobs=workflow_status.get("jobs"),
    )
