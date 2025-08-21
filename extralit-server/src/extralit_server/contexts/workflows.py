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
from rq.job import Job
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import REDIS_CONNECTION
from extralit_server.models.database import DocumentWorkflow

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
            _LOGGER.info(f"No workflow found for document {document_id}")
            return []

        # Handle group expiration and missing groups gracefully
        try:
            group = Group.fetch(name=workflow.group_id, connection=REDIS_CONNECTION)
        except Exception as e:
            _LOGGER.warning(f"Group {workflow.group_id} not found or expired for document {document_id}: {e}")
            return [
                {
                    "id": "group_expired",
                    "status": "expired",
                    "workflow_step": "unknown",
                    "document_id": document_id,
                    "error": f"Group not found or expired: {e}",
                }
            ]

        jobs = group.get_jobs()

        job_data_list = []
        for job in jobs:
            try:
                job_data = {
                    "id": job.id,
                    "status": job.get_status(refresh=True),
                    "workflow_step": job.meta.get("workflow_step", "unknown") if job.meta else "unknown",
                    "document_id": document_id,
                    "group_id": workflow.group_id,
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
                _LOGGER.warning(f"Error processing job {job.id} for document {document_id}: {e}")
                job_data_list.append(
                    {
                        "id": job.id,
                        "status": "error",
                        "workflow_step": "unknown",
                        "document_id": document_id,
                        "group_id": workflow.group_id,
                        "error": f"Job processing error: {e}",
                    }
                )

        return job_data_list

    except Exception as e:
        _LOGGER.error(f"Error getting jobs for document {document_id}: {e}")
        return []


async def get_jobs_by_reference(db: AsyncSession, reference: str) -> list[dict[str, Any]]:
    """
    Get all jobs for documents with a specific reference using RQ Groups.

    This efficiently queries multiple RQ Groups for all documents in a reference batch
    by reusing the get_jobs_for_document function.

    Args:
        db: Database session
        reference: Document reference to search for

    Returns:
        List of job dictionaries with status and metadata
    """
    try:
        # Get all workflows with the reference
        workflows = await DocumentWorkflow.get_by_reference(db, reference)

        if not workflows:
            _LOGGER.info(f"No workflows found for reference {reference}")
            return []

        all_jobs = []
        for workflow in workflows:
            try:
                # Reuse get_jobs_for_document for each document in the reference
                document_jobs = await get_jobs_for_document(db, workflow.document_id)
                all_jobs.extend(document_jobs)
            except Exception as workflow_error:
                _LOGGER.error(
                    f"Error getting jobs for document {workflow.document_id} in reference {reference}: {workflow_error}"
                )
                # Add placeholder job for workflow processing error
                all_jobs.append(
                    {
                        "id": f"workflow_error_{workflow.id}",
                        "status": "error",
                        "workflow_step": "unknown",
                        "document_id": workflow.document_id,
                        "group_id": workflow.group_id,
                        "reference": reference,
                        "error": f"Workflow processing error: {workflow_error}",
                    }
                )

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
            _LOGGER.info(f"No workflow found for document {document_id}")
            return {
                "document_id": document_id,
                "status": "not_found",
                "progress": 0.0,
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "running_jobs": 0,
                "jobs": [],
                "error": "No workflow found for document",
            }

        # Get workflow status using RQ Groups with enhanced error handling
        workflow_status = get_workflow_status_from_group(workflow.group_id)

        # Add additional workflow metadata
        workflow_status.update(
            {
                "document_id": document_id,
                "workflow_id": workflow.id,
                "workflow_type": workflow.workflow_type,
                "group_id": workflow.group_id,
                "reference": workflow.reference,
                "workspace_id": workflow.workspace_id,
                "created_at": workflow.inserted_at,
                "updated_at": workflow.updated_at,
                "cached_status": workflow.status,  # Include cached status for comparison
            }
        )

        # Update cached status if it differs from RQ Group status
        if workflow.status != workflow_status["status"] and workflow_status["status"] not in ["error", "expired"]:
            try:
                await update_workflow_status(db, workflow, workflow_status["status"])
                _LOGGER.info(
                    f"Updated cached workflow status for document {document_id} from {workflow.status} to {workflow_status['status']}"
                )
            except Exception as update_error:
                _LOGGER.warning(f"Failed to update cached workflow status for document {document_id}: {update_error}")

        return workflow_status

    except Exception as e:
        _LOGGER.error(f"Error getting workflow status for document {document_id}: {e}")
        return {
            "document_id": document_id,
            "status": "error",
            "progress": 0.0,
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "running_jobs": 0,
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
        # Handle group expiration and missing groups gracefully
        try:
            group = Group.fetch(name=group_id, connection=REDIS_CONNECTION)
        except Exception as e:
            _LOGGER.warning(f"Group {group_id} not found or expired: {e}")
            return {
                "status": "expired",
                "progress": 0.0,
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "running_jobs": 0,
                "jobs": [],
                "error": f"Group not found or expired: {e}",
            }

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
            try:
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
            except Exception as job_error:
                # Handle individual job errors gracefully
                _LOGGER.warning(f"Error processing job {job.id}: {job_error}")
                job_details.append(
                    {
                        "id": job.id,
                        "status": "error",
                        "error": f"Job processing error: {job_error}",
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
        _LOGGER.error(f"Error getting workflow status from group {group_id}: {e}")
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
        # Handle group expiration and missing groups gracefully
        try:
            group = Group.fetch(name=group_id, connection=REDIS_CONNECTION)
        except Exception as e:
            _LOGGER.warning(f"Group {group_id} not found or expired, cannot resume: {e}")
            return False

        jobs = group.get_jobs()

        # Check if there are any failed jobs
        failed_jobs = [job for job in jobs if job.is_failed]
        return len(failed_jobs) > 0

    except Exception as e:
        _LOGGER.error(f"Error checking if workflow {group_id} is resumable: {e}")
        return False


def get_failed_jobs_in_group(group_id: str) -> list[dict[str, Any]]:
    """
    Add logic to identify failed jobs using RQ Group.get_jobs() with status filtering.

    Args:
        group_id: RQ Group ID

    Returns:
        List of failed job dictionaries with details
    """
    try:
        # Handle group expiration and missing groups gracefully
        try:
            group = Group.fetch(name=group_id, connection=REDIS_CONNECTION)
        except Exception as e:
            _LOGGER.warning(f"Group {group_id} not found or expired: {e}")
            return []

        jobs = group.get_jobs()

        # Filter failed jobs and return detailed information
        failed_jobs = []
        for job in jobs:
            try:
                if job.is_failed:
                    failed_job_info = {
                        "id": job.id,
                        "status": job.get_status(refresh=True),
                        "created_at": job.created_at,
                        "started_at": job.started_at,
                        "ended_at": job.ended_at,
                        "meta": job.meta,
                        "exc_info": job.exc_info,
                        "failure_reason": str(job.exc_info) if job.exc_info else "Unknown failure",
                        "workflow_step": job.meta.get("workflow_step", "unknown") if job.meta else "unknown",
                    }
                    failed_jobs.append(failed_job_info)
            except Exception as job_error:
                _LOGGER.warning(f"Error processing failed job {job.id}: {job_error}")
                # Add basic info even if detailed processing fails
                failed_jobs.append(
                    {
                        "id": job.id,
                        "status": "failed",
                        "error": f"Job processing error: {job_error}",
                        "workflow_step": "unknown",
                    }
                )

        return failed_jobs

    except Exception as e:
        _LOGGER.error(f"Error getting failed jobs for group {group_id}: {e}")
        return []


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
        # Handle group expiration and missing groups gracefully
        try:
            group = Group.fetch(name=workflow.group_id, connection=REDIS_CONNECTION)
        except Exception as e:
            _LOGGER.error(f"Group {workflow.group_id} not found or expired, cannot restart: {e}")
            return {
                "success": False,
                "error": f"Group not found or expired: {e}",
                "restarted_jobs": [],
                "total_failed": 0,
            }

        jobs = group.get_jobs()

        failed_jobs = [job for job in jobs if job.is_failed]
        restarted_jobs = []

        for job in failed_jobs:
            try:
                # Requeue the failed job
                job.requeue()
                restarted_jobs.append(job.id)
                _LOGGER.info(f"Restarted failed job {job.id} in workflow {workflow.id}")
            except Exception as e:
                # Log individual job restart failures but continue
                _LOGGER.warning(f"Failed to restart job {job.id}: {e}")

        # Update workflow status if jobs were restarted
        if restarted_jobs:
            await update_workflow_status(db, workflow, "running")
            _LOGGER.info(
                f"Updated workflow {workflow.id} status to running after restarting {len(restarted_jobs)} jobs"
            )

        return {"success": True, "restarted_jobs": restarted_jobs, "total_failed": len(failed_jobs)}

    except Exception as e:
        _LOGGER.error(f"Error restarting failed jobs in workflow {workflow.id}: {e}")
        return {"success": False, "error": str(e), "restarted_jobs": [], "total_failed": 0}


async def restart_failed_workflow(db: AsyncSession, document_id: UUID, partial_restart: bool = True) -> dict[str, Any]:
    """
    Create restart_failed_workflow() function using RQ Group failed job identification.

    This function provides a high-level interface for restarting workflows with
    support for partial vs full workflow restart using RQ Group capabilities.

    Args:
        db: Database session
        document_id: Document ID to restart workflow for
        partial_restart: If True, only restart failed jobs; if False, restart entire workflow

    Returns:
        Dictionary with restart results including job re-enqueueing status
    """
    try:
        # Get workflow by document ID
        workflow = await DocumentWorkflow.get_by_document_id(db, document_id)
        if not workflow:
            return {
                "success": False,
                "error": f"No workflow found for document {document_id}",
                "restarted_jobs": [],
                "total_failed": 0,
            }

        # Check if workflow is resumable
        if not is_workflow_resumable(workflow.group_id):
            return {
                "success": False,
                "error": "Workflow is not in a resumable state (no failed jobs found)",
                "restarted_jobs": [],
                "total_failed": 0,
            }

        if partial_restart:
            # Use existing function for partial restart (failed jobs only)
            return await restart_failed_jobs_in_workflow(db, workflow)
        else:
            # Full workflow restart - restart all jobs in the group
            try:
                group = Group.fetch(name=workflow.group_id, connection=REDIS_CONNECTION)
            except Exception as e:
                _LOGGER.error(f"Group {workflow.group_id} not found or expired, cannot restart: {e}")
                return {
                    "success": False,
                    "error": f"Group not found or expired: {e}",
                    "restarted_jobs": [],
                    "total_failed": 0,
                }

            jobs = group.get_jobs()
            restarted_jobs = []
            failed_jobs = [job for job in jobs if job.is_failed]

            # Restart all jobs in the workflow with proper dependencies
            for job in jobs:
                try:
                    # Requeue job (RQ will handle dependencies automatically)
                    job.requeue()
                    restarted_jobs.append(job.id)
                    _LOGGER.info(f"Restarted job {job.id} in full workflow restart for {workflow.id}")
                except Exception as e:
                    _LOGGER.warning(f"Failed to restart job {job.id} in full restart: {e}")

            # Update DocumentWorkflow records with new group state information
            if restarted_jobs:
                await update_workflow_status(db, workflow, "running")
                _LOGGER.info(
                    f"Updated workflow {workflow.id} status to running after full restart of {len(restarted_jobs)} jobs"
                )

            return {
                "success": True,
                "restarted_jobs": restarted_jobs,
                "total_failed": len(failed_jobs),
                "restart_type": "full",
            }

    except Exception as e:
        _LOGGER.error(f"Error restarting workflow for document {document_id}: {e}")
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


async def get_workflow_statuses_by_reference(db: AsyncSession, reference: str) -> list[dict[str, Any]]:
    """
    Get workflow statuses for all documents with a specific reference.

    This is more efficient than calling get_workflow_status for each document individually.

    Args:
        db: Database session
        reference: Document reference to search for

    Returns:
        List of workflow status dictionaries
    """
    try:
        workflows = await DocumentWorkflow.get_by_reference(db, reference)

        if not workflows:
            _LOGGER.info(f"No workflows found for reference {reference}")
            return []

        workflow_statuses = []
        for workflow in workflows:
            try:
                # Get workflow status using RQ Groups
                workflow_status = get_workflow_status_from_group(workflow.group_id)

                # Add workflow metadata
                workflow_status.update(
                    {
                        "document_id": workflow.document_id,
                        "workflow_id": workflow.id,
                        "workflow_type": workflow.workflow_type,
                        "group_id": workflow.group_id,
                        "reference": reference,
                        "workspace_id": workflow.workspace_id,
                        "created_at": workflow.inserted_at,
                        "updated_at": workflow.updated_at,
                        "cached_status": workflow.status,
                    }
                )

                workflow_statuses.append(workflow_status)

                # Update cached status if needed
                if workflow.status != workflow_status["status"] and workflow_status["status"] not in [
                    "error",
                    "expired",
                ]:
                    try:
                        await update_workflow_status(db, workflow, workflow_status["status"])
                    except Exception as update_error:
                        _LOGGER.warning(
                            f"Failed to update cached workflow status for workflow {workflow.id}: {update_error}"
                        )

            except Exception as workflow_error:
                _LOGGER.error(f"Error processing workflow {workflow.id} for reference {reference}: {workflow_error}")
                # Add error status for failed workflow processing
                workflow_statuses.append(
                    {
                        "document_id": workflow.document_id,
                        "workflow_id": workflow.id,
                        "workflow_type": workflow.workflow_type,
                        "group_id": workflow.group_id,
                        "reference": reference,
                        "workspace_id": workflow.workspace_id,
                        "status": "error",
                        "progress": 0.0,
                        "total_jobs": 0,
                        "completed_jobs": 0,
                        "failed_jobs": 0,
                        "running_jobs": 0,
                        "jobs": [],
                        "error": f"Workflow processing error: {workflow_error}",
                        "created_at": workflow.inserted_at,
                        "updated_at": workflow.updated_at,
                        "cached_status": workflow.status,
                    }
                )

        return workflow_statuses

    except Exception as e:
        _LOGGER.error(f"Error getting workflow statuses for reference {reference}: {e}")
        return []


async def list_workflows(
    db: AsyncSession,
    workspace_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List workflows with optional filtering and RQ Group information.

    Args:
        db: Database session
        workspace_id: Optional workspace ID filter
        status_filter: Optional status filter
        limit: Maximum number of workflows to return

    Returns:
        List of workflow status dictionaries with RQ Group information
    """
    try:
        from sqlalchemy import select

        # Build query with efficient database queries using group_id indexing
        query = select(DocumentWorkflow).order_by(DocumentWorkflow.inserted_at.desc()).limit(limit)

        if workspace_id:
            query = query.where(DocumentWorkflow.workspace_id == workspace_id)

        if status_filter:
            query = query.where(DocumentWorkflow.status == status_filter)

        # Execute query
        result = await db.execute(query)
        workflows = result.scalars().all()

        workflow_statuses = []
        for workflow in workflows:
            try:
                # Get workflow status using RQ Groups with enhanced error handling
                workflow_status = get_workflow_status_from_group(workflow.group_id)

                # Add workflow metadata including RQ Group information
                workflow_status.update(
                    {
                        "document_id": workflow.document_id,
                        "workflow_id": workflow.id,
                        "workflow_type": workflow.workflow_type,
                        "group_id": workflow.group_id,
                        "reference": workflow.reference,
                        "workspace_id": workflow.workspace_id,
                        "created_at": workflow.inserted_at,
                        "updated_at": workflow.updated_at,
                        "cached_status": workflow.status,
                    }
                )

                workflow_statuses.append(workflow_status)

                # Update cached status if needed for performance optimization
                if workflow.status != workflow_status["status"] and workflow_status["status"] not in [
                    "error",
                    "expired",
                ]:
                    try:
                        await update_workflow_status(db, workflow, workflow_status["status"])
                    except Exception as update_error:
                        _LOGGER.warning(
                            f"Failed to update cached workflow status for workflow {workflow.id}: {update_error}"
                        )

            except Exception as workflow_error:
                # Handle missing groups and RQ connection issues gracefully
                _LOGGER.warning(f"Error processing workflow {workflow.id}: {workflow_error}")
                # Add basic workflow info even if RQ Group access fails
                workflow_statuses.append(
                    {
                        "document_id": workflow.document_id,
                        "workflow_id": workflow.id,
                        "workflow_type": workflow.workflow_type,
                        "group_id": workflow.group_id,
                        "reference": workflow.reference,
                        "workspace_id": workflow.workspace_id,
                        "status": "error",
                        "progress": 0.0,
                        "total_jobs": 0,
                        "completed_jobs": 0,
                        "failed_jobs": 0,
                        "running_jobs": 0,
                        "jobs": [],
                        "error": f"RQ Group access error: {workflow_error}",
                        "created_at": workflow.inserted_at,
                        "updated_at": workflow.updated_at,
                        "cached_status": workflow.status,
                    }
                )

        return workflow_statuses

    except Exception as e:
        _LOGGER.error(f"Error listing workflows: {e}")
        return []
