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

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import JobPolicy, authorize
from extralit_server.api.schemas.v1.jobs import Job as JobSchema
from extralit_server.api.schemas.v1.jobs import WorkflowJobResult
from extralit_server.contexts.workflows import get_jobs_by_reference, get_jobs_for_document
from extralit_server.database import get_async_db
from extralit_server.jobs.queues import REDIS_CONNECTION
from extralit_server.models import User
from extralit_server.models.database import DocumentWorkflow
from extralit_server.security import auth

router = APIRouter(tags=["jobs"])


def _get_job(job_id: str) -> Job:
    try:
        return Job.fetch(job_id, connection=REDIS_CONNECTION)
    except NoSuchJobError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id `{job_id}` not found",
        )


@router.get("/jobs/{job_id}", response_model=JobSchema)
async def get_job(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    job_id: str,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    job = _get_job(job_id)

    await authorize(current_user, JobPolicy.get)

    return JobSchema(id=job.id, status=job.get_status(refresh=True))


@router.get("/jobs/", response_model=list[WorkflowJobResult])
async def get_jobs(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    document_id: Optional[UUID] = Query(None, description="Filter by document ID"),
    reference: Optional[str] = Query(None, description="Filter by document reference"),
    group_id: Optional[str] = Query(None, description="Filter by RQ Group ID"),
):
    """
    Get jobs using RQ Groups-based querying.

    Maps document IDs to RQ Groups for efficient job status retrieval.
    For reference-level queries, searches over documents linked to the reference.
    """
    await authorize(current_user, JobPolicy.get)

    try:
        if document_id:
            # Get jobs for specific document using RQ Groups
            jobs_raw = await get_jobs_for_document(db, document_id)
            return [_convert_job_data_to_result(job_data) for job_data in jobs_raw]

        elif reference:
            # Get jobs for all documents with reference using RQ Groups
            jobs_raw = await get_jobs_by_reference(db, reference)
            return [_convert_job_data_to_result(job_data) for job_data in jobs_raw]

        elif group_id:
            # Direct group querying - get workflow and jobs from RQ Group
            workflow = await DocumentWorkflow.get_by_group_id(db, group_id)
            if not workflow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow with group_id `{group_id}` not found",
                )

            from extralit_server.contexts.workflows import get_workflow_status_from_group

            group_status = get_workflow_status_from_group(group_id)

            # Convert group jobs to WorkflowJobResult format
            results = []
            for job_data in group_status.get("jobs", []):
                job_result = _convert_job_data_to_result(job_data)
                # Add group metadata to each job result
                job_result.group_id = workflow.group_id
                job_result.group_status = group_status.get("status")
                job_result.group_progress = group_status.get("progress")
                job_result.total_jobs = group_status.get("total_jobs")
                job_result.completed_jobs = group_status.get("completed_jobs")
                job_result.failed_jobs = group_status.get("failed_jobs")
                job_result.running_jobs = group_status.get("running_jobs")
                job_result.document_id = workflow.document_id
                job_result.reference = workflow.reference
                job_result.workspace_id = workflow.workspace_id
                results.append(job_result)

            return results
        else:
            # No filters provided - return empty list
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide at least one filter: document_id, reference, or group_id",
            )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving jobs: {e!s}",
        )


def _convert_job_data_to_result(job_data: dict) -> WorkflowJobResult:
    """Convert job data to WorkflowJobResult."""
    return WorkflowJobResult(
        id=job_data.get("id", ""),
        status=job_data.get("status", "unknown"),
        document_id=job_data.get("document_id"),
        reference=job_data.get("reference"),
        workspace_id=job_data.get("workspace_id"),
        workflow_step=job_data.get("workflow_step"),
        progress=job_data.get("meta", {}).get("progress") if job_data.get("meta") else None,
        error=job_data.get("exc_info") or job_data.get("error"),
        result=job_data.get("result"),
        meta=job_data.get("meta"),
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("ended_at"),
        # RQ Groups metadata (will be populated for group queries)
        group_id=job_data.get("group_id"),
    )
