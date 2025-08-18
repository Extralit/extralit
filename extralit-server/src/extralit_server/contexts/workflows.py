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
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.jobs.queues import REDIS_CONNECTION
from extralit_server.models.database import Document, DocumentWorkflow

_LOGGER = logging.getLogger(__name__)


async def get_jobs_for_document(db: AsyncSession, document_id: UUID) -> list[dict[str, Any]]:
    """
    Get all jobs for a document using DocumentWorkflow lookup.

    This replaces expensive registry scanning with efficient database queries.

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

        jobs = []
        for job_name, job_id in workflow.job_ids.items():
            try:
                # Get job from Redis
                job = Job.fetch(job_id, connection=REDIS_CONNECTION)
                job_data = {
                    "id": job.id,
                    "status": job.get_status(refresh=True),
                    "workflow_step": job_name,
                    "document_id": document_id,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "ended_at": job.ended_at,
                    "meta": job.meta,
                    "result": job.result if job.is_finished else None,
                    "exc_info": job.exc_info if job.is_failed else None,
                }
                jobs.append(job_data)
            except (NoSuchJobError, Exception) as e:
                # Handle expired or missing jobs gracefully
                _LOGGER.warning(f"Job {job_id} not found in Redis: {e}")
                jobs.append(
                    {
                        "id": job_id,
                        "status": JobStatus.FAILED,
                        "workflow_step": job_name,
                        "document_id": document_id,
                        "error": f"Job not found: {e}",
                    }
                )

        return jobs

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
    Get complete workflow status for a document.

    Args:
        db: Database session
        document_id: Document ID to get workflow status for

    Returns:
        Dictionary with workflow status and progress information
    """
    try:
        # Get workflow record
        workflow = await DocumentWorkflow.get_by_document_id(db, document_id)
        if not workflow:
            return {
                "document_id": document_id,
                "status": "not_found",
                "progress": 0.0,
                "jobs": [],
                "error": "No workflow found for document",
            }

        # Get all jobs for the document
        jobs = await get_jobs_for_document(db, document_id)

        # Calculate overall status and progress
        total_jobs = len(jobs)
        if total_jobs == 0:
            return {
                "document_id": document_id,
                "status": "pending",
                "progress": 0.0,
                "jobs": [],
            }

        completed_jobs = sum(1 for job in jobs if job["status"] in [JobStatus.FINISHED])
        failed_jobs = sum(1 for job in jobs if job["status"] in [JobStatus.FAILED])
        running_jobs = sum(1 for job in jobs if job["status"] in [JobStatus.STARTED])

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

        return {
            "document_id": document_id,
            "workflow_id": workflow.id,
            "workflow_type": workflow.workflow_type,
            "status": overall_status,
            "progress": progress,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": running_jobs,
            "jobs": jobs,
            "created_at": workflow.inserted_at,
            "updated_at": workflow.updated_at,
        }

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
    workflow status based on the current state of all jobs.

    Args:
        db: Database session
        document_id: Document ID to update workflow status for
    """
    try:
        workflow = await DocumentWorkflow.get_by_document_id(db, document_id)
        if not workflow:
            _LOGGER.warning(f"No workflow found for document {document_id}")
            return

        # Get current workflow status
        workflow_status = await get_workflow_status(db, document_id)

        # Update workflow status based on job states
        new_status = workflow_status["status"]

        # Update the workflow record
        if workflow.status != new_status:
            await workflow.update_status(db, new_status)
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


async def cleanup_expired_workflows(db: AsyncSession, max_age_days: int = 7) -> int:
    """
    Clean up expired/completed workflows older than max_age_days.

    Args:
        db: Database session
        max_age_days: Maximum age in days for completed workflows

    Returns:
        Number of workflows cleaned up
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        # Find completed workflows older than cutoff
        stmt = (
            select(DocumentWorkflow)
            .where(DocumentWorkflow.status.in_(["completed", "failed"]))
            .where(DocumentWorkflow.updated_at < cutoff_date)
        )
        result = await db.execute(stmt)
        expired_workflows = result.scalars().all()

        cleaned_count = 0
        for workflow in expired_workflows:
            try:
                # Clean up associated job data if needed
                for _job_name, job_id in workflow.job_ids.items():
                    try:
                        Job.fetch(job_id, connection=REDIS_CONNECTION)
                        # Let RQ handle job cleanup naturally
                        # We just remove our workflow tracking
                    except (NoSuchJobError, Exception):
                        # Job already expired/cleaned up
                        pass

                # Delete workflow record
                await db.delete(workflow)
                cleaned_count += 1

            except Exception as e:
                _LOGGER.warning(f"Error cleaning up workflow {workflow.id}: {e}")

        if cleaned_count > 0:
            await db.commit()
            _LOGGER.info(f"Cleaned up {cleaned_count} expired workflows")

        return cleaned_count

    except Exception as e:
        _LOGGER.error(f"Error during workflow cleanup: {e}")
        return 0


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
