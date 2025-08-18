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


@router.get("/jobs/", response_model=list[WorkflowJobResult])
async def get_jobs(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    document_id: Annotated[Optional[UUID], Query()] = None,
    reference: Annotated[Optional[str], Query()] = None,
    workflow_step: Annotated[Optional[str], Query()] = None,
):
    """
    Get jobs with optional filtering by document_id, reference, or workflow_step.
    """
    await authorize(current_user, JobPolicy.get)

    jobs = []

    if document_id:
        jobs = await get_jobs_for_document(db, document_id)
    elif reference:
        jobs = await get_jobs_by_reference(db, reference)
    else:
        # If no filters provided, return empty list to avoid expensive operations
        return []

    # Filter by workflow_step if provided
    if workflow_step:
        jobs = [job for job in jobs if job.get("workflow_step") == workflow_step]

    # Convert to WorkflowJobResult schema
    result = []
    for job_data in jobs:
        workflow_job = WorkflowJobResult(
            id=job_data["id"],
            status=job_data["status"],
            document_id=job_data.get("document_id"),
            reference=job_data.get("reference"),
            workspace_id=job_data.get("meta", {}).get("workspace_id"),
            workflow_step=job_data.get("workflow_step"),
            progress=job_data.get("meta", {}).get("progress"),
            started_at=job_data.get("started_at"),
            completed_at=job_data.get("ended_at"),
            error=job_data.get("error") or (job_data.get("exc_info") if job_data.get("exc_info") else None),
            result=job_data.get("result"),
            meta=job_data.get("meta"),
        )
        result.append(workflow_job)

    return result


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
