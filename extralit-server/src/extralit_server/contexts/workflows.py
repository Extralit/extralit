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

"""Workflow job querying and management functions."""

import logging
from typing import Any, Optional
from uuid import UUID

from rq.exceptions import NoSuchJobError
from rq.group import Group
from rq.job import Job, JobStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.jobs.queues import REDIS_CONNECTION
from extralit_server.models.database import Document, DocumentWorkflow

_LOGGER = logging.getLogger(__name__)


async def get_jobs_for_document(db: AsyncSession, document_id: UUID) -> list[dict[str, Any]]:
    """
    Get all jobs for a document using RQ Group lookup.

    This replaces expensive registry scanning with efficient RQ Group queries.

    Args:
        db: Database session
        document_id: Document ID to get jobs for

    Returns:
        List of job dictionaries with status and metadata
    """
    try:
        # Get workflow record for the document
        workflow = await DocumentWorkflow.get_by_document_id(db, document_id)
        if not workflow:
            return []

        # Use RQ Group to get all jobs
        group = Group.fetch(name=workflow.group_id, connection=REDIS_CONNECTION)
        jobs = group.get_jobs()

        job_data_list = []
        for job in jobs:
            try:
                job_data = {
                    "id": job.id,
                    "status": job.get_status(refresh=True),
                    "workflow_step": job.meta.get("workflow_step", "unknown") if job.meta else "unknown",
                    "document_id": document_id,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "ended_at": job.ended_at,
                    "meta": job.meta,
                    "result": job.result if job.is_finished else None,
                    "exc_info": job.exc_info if job.is_failed else None,
                }
                job_data_list.append(job_data)
            except Exception as e:
                # Handle individual job errors gracefully
                _LOGGER.warning(f"Error processing job {job.id}: {e}")
                job_data_list.append(
                    {
                        "id": job.id,
                        "status": JobStatus.FAILED,
                        "workflow_step": "unknown",
                        "document_id": document_id,
                        "error": f"Job processing error: {e}",
                    }
                )

        return job_data_list

    except Exception as e:
        _LOGGER.error(f"Error getting jobs for document {document_id}: {e}")
        return []


async def get_jobs_by_reference(db: AsyncSession, reference: str) -> list[dict[str, Any]]:
    """
    Get all jobs for documents with a specific reference.

    Args:
        db: Database session
        reference: Document reference to search for

    Returns:
        List of job dictionaries with status and metadata
    """
    try:
        # Get all documents with the reference
        stmt = select(Document).where(Document.reference == reference).options(selectinload(Document.workflows))
        result = await db.execute(stmt)
        documents = result.scalars().all()

        all_jobs = []
        for document in documents:
            document_jobs = await get_jobs_for_document(db, document.id)
            # Add reference to each job
            for job in document_jobs:
                job["reference"] = reference
            all_jobs.extend(document_jobs)

        return all_jobs

    except Exception as e:
        _LOGGER.error(f"Error getting jobs for reference {reference}: {e}")
        return []


async def get_workflow_status(db: AsyncSession, document_id: UUID) -> dict[str, Any]:
    """
    Get complete workflow status for a document using RQ Groups.

    Args:
        db: Database session
        document_id: Document ID to get workflow status for

    Returns:
        Dictionary with workflow status and progress information
    """
    try:
        workflow = await DocumentWorkflow.get_by_document_id(db, document_id)
        if not workflow:
            return {
                "document_id": document_id,
                "status": "not_found",
                "progress": 0.0,
                "jobs": [],
                "error": "No workflow found for document",
            }

        # Get workflow status using RQ Groups
        workflow_status = get_workflow_status_from_group(workflow.group_id)

        # Add additional workflow metadata
        workflow_status.update(
            {
                "document_id": document_id,
                "workflow_id": workflow.id,
                "workflow_type": workflow.workflow_type,
                "group_id": workflow.group_id,
                "created_at": workflow.inserted_at,
                "updated_at": workflow.updated_at,
            }
        )

        return workflow_status

    except Exception as e:
        _LOGGER.error(f"Error getting workflow status for document {document_id}: {e}")
        return {
            "document_id": document_id,
            "status": "error",
            "progress": 0.0,
            "jobs": [],
            "error": str(e),
        }


def get_job_by_id(job_id: str) -> Optional[dict[str, Any]]:
    """
    Get a single job by ID with error handling.

    Args:
        job_id: Job ID to fetch

    Returns:
        Job dictionary or None if not found
    """
    try:
        job = Job.fetch(job_id, connection=REDIS_CONNECTION)
        return {
            "id": job.id,
            "status": job.get_status(refresh=True),
            "created_at": job.created_at,
            "started_at": job.started_at,
            "ended_at": job.ended_at,
            "meta": job.meta,
            "result": job.result if job.is_finished else None,
            "exc_info": job.exc_info if job.is_failed else None,
        }
    except (NoSuchJobError, Exception) as e:
        _LOGGER.warning(f"Job {job_id} not found: {e}")
        return None


async def update_workflow_status_on_job_completion(db: AsyncSession, document_id: UUID) -> None:
    """
    Update workflow status when a job completes or fails.

    This function should be called when jobs complete to update the overall
    workflow status based on the current state of all jobs using RQ Groups.

    Args:
        db: Database session
        document_id: Document ID to update workflow status for
    """
    try:
        workflow = await DocumentWorkflow.get_by_document_id(db, document_id)
        if not workflow:
            _LOGGER.warning(f"No workflow found for document {document_id}")
            return

        # Get current workflow status using RQ Groups
        workflow_status = get_workflow_status_from_group(workflow.group_id)
        new_status = workflow_status["status"]

        # Update the workflow record if status changed
        if workflow.status != new_status:
            await update_workflow_status(db, workflow, new_status)
            _LOGGER.info(f"Updated workflow status for document {document_id} to {new_status}")

    except Exception as e:
        _LOGGER.error(f"Error updating workflow status for document {document_id}: {e}")


async def calculate_workflow_progress(db: AsyncSession, document_id: UUID) -> float:
    """
    Calculate workflow progress based on completed steps.

    Args:
        db: Database session
        document_id: Document ID to calculate progress for

    Returns:
        Progress as float between 0.0 and 1.0
    """
    try:
        workflow_status = await get_workflow_status(db, document_id)
        return workflow_status.get("progress", 0.0)
    except Exception as e:
        _LOGGER.error(f"Error calculating workflow progress for document {document_id}: {e}")
        return 0.0


def create_job_completion_callback(document_id: UUID):
    """
    Create a callback function for job completion that updates workflow status.

    This can be used with RQ's job callbacks to automatically update workflow
    status when jobs complete.

    Args:
        document_id: Document ID associated with the job

    Returns:
        Callback function that can be used with RQ jobs
    """

    async def callback(job, connection, result, *args, **kwargs):
        """Job completion callback to update workflow status."""
        try:
            from extralit_server.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                await update_workflow_status_on_job_completion(db, document_id)
        except Exception as e:
            _LOGGER.error(f"Error in job completion callback for document {document_id}: {e}")

    return callback


def get_workflow_status_from_group(group_id: str) -> dict[str, Any]:
    """
    Get workflow status using RQ Group.

    Args:
        group_id: RQ Group ID

    Returns:
        Dictionary with workflow status and job information
    """
    try:
        group = Group.fetch(name=group_id, connection=REDIS_CONNECTION)
        jobs = group.get_jobs()

        total_jobs = len(jobs)
        if total_jobs == 0:
            return {
                "status": "pending",
                "progress": 0.0,
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "running_jobs": 0,
                "jobs": [],
            }

        completed_jobs = sum(1 for job in jobs if job.is_finished)
        failed_jobs = sum(1 for job in jobs if job.is_failed)
        running_jobs = sum(1 for job in jobs if job.is_started and not job.is_finished)

        # Determine overall status
        if failed_jobs > 0:
            overall_status = "failed"
        elif completed_jobs == total_jobs:
            overall_status = "completed"
        elif running_jobs > 0:
            overall_status = "running"
        else:
            overall_status = "pending"

        # Calculate progress (0.0 to 1.0)
        progress = completed_jobs / total_jobs if total_jobs > 0 else 0.0

        job_details = []
        for job in jobs:
            job_details.append(
                {
                    "id": job.id,
                    "status": job.get_status(refresh=True),
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "ended_at": job.ended_at,
                    "meta": job.meta,
                    "result": job.result if job.is_finished else None,
                    "exc_info": job.exc_info if job.is_failed else None,
                }
            )

        return {
            "status": overall_status,
            "progress": progress,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": running_jobs,
            "jobs": job_details,
        }

    except Exception as e:
        return {
            "status": "error",
            "progress": 0.0,
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "running_jobs": 0,
            "jobs": [],
            "error": str(e),
        }


def is_workflow_resumable(group_id: str) -> bool:
    """
    Check if workflow can be resumed (has failed jobs that can be retried).

    Args:
        group_id: RQ Group ID

    Returns:
        True if workflow has failed jobs that can be resumed
    """
    try:
        group = Group.fetch(name=group_id, connection=REDIS_CONNECTION)
        jobs = group.get_jobs()

        # Check if there are any failed jobs
        failed_jobs = [job for job in jobs if job.is_failed]
        return len(failed_jobs) > 0

    except Exception:
        return False


async def restart_failed_jobs_in_workflow(db: AsyncSession, workflow: DocumentWorkflow) -> dict[str, Any]:
    """
    Restart failed jobs in the workflow group.

    Args:
        db: Database session
        workflow: DocumentWorkflow instance

    Returns:
        Dictionary with restart results
    """
    try:
        group = Group.fetch(name=workflow.group_id, connection=REDIS_CONNECTION)
        jobs = group.get_jobs()

        failed_jobs = [job for job in jobs if job.is_failed]
        restarted_jobs = []

        for job in failed_jobs:
            try:
                # Requeue the failed job
                job.requeue()
                restarted_jobs.append(job.id)
            except Exception as e:
                # Log individual job restart failures but continue
                _LOGGER.warning(f"Failed to restart job {job.id}: {e}")

        # Update workflow status if jobs were restarted
        if restarted_jobs:
            await update_workflow_status(db, workflow, "running")

        return {"success": True, "restarted_jobs": restarted_jobs, "total_failed": len(failed_jobs)}

    except Exception as e:
        return {"success": False, "error": str(e), "restarted_jobs": [], "total_failed": 0}


async def update_workflow_status(db: AsyncSession, workflow: DocumentWorkflow, new_status: str) -> None:
    """
    Update workflow status in database.

    Args:
        db: Database session
        workflow: DocumentWorkflow instance
        new_status: New status to set
    """
    workflow.status = new_status
    db.add(workflow)
    await db.commit()


async def get_workflow_by_document_id(db: AsyncSession, document_id: UUID) -> Optional[DocumentWorkflow]:
    """
    Get workflow by document ID with enhanced functionality.

    Args:
        db: Database session
        document_id: Document ID

    Returns:
        DocumentWorkflow instance or None
    """
    return await DocumentWorkflow.get_by_document_id(db, document_id)


async def get_workflow_by_group_id(db: AsyncSession, group_id: str) -> Optional[DocumentWorkflow]:
    """
    Get workflow by RQ Group ID.

    Args:
        db: Database session
        group_id: RQ Group ID

    Returns:
        DocumentWorkflow instance or None
    """
    return await DocumentWorkflow.get_by_group_id(db, group_id)


async def get_workflows_by_reference(
    db: AsyncSession, reference: str, workspace_id: Optional[UUID] = None
) -> list[DocumentWorkflow]:
    """
    Get workflows by reference (batch tracking).

    Args:
        db: Database session
        reference: Document reference
        workspace_id: Optional workspace ID filter

    Returns:
        List of DocumentWorkflow instances
    """
    return await DocumentWorkflow.get_by_reference(db, reference, str(workspace_id) if workspace_id else None)
