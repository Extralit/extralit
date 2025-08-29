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

"""Unit tests for RQ Groups failure and restart scenarios."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from rq.group import Group
from rq.job import Job

from extralit_server.contexts.workflows import (
    get_failed_jobs_in_group,
    get_workflow_status_from_group,
    is_workflow_resumable,
    restart_failed_jobs_in_workflow,
    restart_failed_workflow,
)
from extralit_server.models.database import DocumentWorkflow


class TestRQGroupsFailureScenarios:
    """Test RQ Groups failure and restart scenarios."""

    @pytest.fixture
    def mock_document_workflow(self):
        """Create mock DocumentWorkflow."""
        workflow = MagicMock(spec=DocumentWorkflow)
        workflow.id = uuid4()
        workflow.document_id = uuid4()
        workflow.group_id = "test_group_123"
        workflow.status = "failed"
        workflow.reference = "test_ref"
        workflow.workspace_id = uuid4()
        workflow.inserted_at = datetime.now(timezone.utc)
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    def test_single_job_failure_scenario(self):
        """Test workflow status when a single job fails."""
        # Create mock jobs - one completed, one failed
        completed_job = MagicMock(spec=Job)
        completed_job.id = "completed_job"
        completed_job.is_finished = True
        completed_job.is_failed = False
        completed_job.is_started = True
        completed_job.get_status.return_value = "finished"
        completed_job.meta = {"workflow_step": "analysis_and_preprocess"}
        completed_job.created_at = datetime.now(timezone.utc)
        completed_job.started_at = datetime.now(timezone.utc)
        completed_job.ended_at = datetime.now(timezone.utc)
        completed_job.result = {"analysis_complete": True}
        completed_job.exc_info = None

        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job"
        failed_job.is_finished = True
        failed_job.is_failed = True
        failed_job.is_started = True
        failed_job.get_status.return_value = "failed"
        failed_job.meta = {"workflow_step": "text_extraction"}
        failed_job.created_at = datetime.now(timezone.utc)
        failed_job.started_at = datetime.now(timezone.utc)
        failed_job.ended_at = datetime.now(timezone.utc)
        failed_job.result = None
        failed_job.exc_info = "OCR processing failed: timeout"

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [completed_job, failed_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "failed"
            assert status["progress"] == 1.0  # Both jobs finished
            assert status["total_jobs"] == 2
            assert status["completed_jobs"] == 2
            assert status["failed_jobs"] == 1
            assert status["running_jobs"] == 0
            assert len(status["jobs"]) == 2

    def test_multiple_job_failures_scenario(self):
        """Test workflow status when multiple jobs fail."""
        # Create mock jobs - one completed, two failed
        completed_job = MagicMock(spec=Job)
        completed_job.is_finished = True
        completed_job.is_failed = False
        completed_job.get_status.return_value = "finished"

        failed_job1 = MagicMock(spec=Job)
        failed_job1.is_finished = True
        failed_job1.is_failed = True
        failed_job1.get_status.return_value = "failed"
        failed_job1.exc_info = "Analysis failed: invalid PDF"

        failed_job2 = MagicMock(spec=Job)
        failed_job2.is_finished = True
        failed_job2.is_failed = True
        failed_job2.get_status.return_value = "failed"
        failed_job2.exc_info = "Text extraction failed: timeout"

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [completed_job, failed_job1, failed_job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "failed"
            assert status["progress"] == 1.0  # All jobs finished
            assert status["total_jobs"] == 3
            assert status["completed_jobs"] == 3
            assert status["failed_jobs"] == 2
            assert status["running_jobs"] == 0

    def test_job_timeout_failure_scenario(self):
        """Test handling of job timeout failures."""
        timeout_job = MagicMock(spec=Job)
        timeout_job.id = "timeout_job"
        timeout_job.is_finished = True
        timeout_job.is_failed = True
        timeout_job.get_status.return_value = "failed"
        timeout_job.meta = {"workflow_step": "text_extraction"}
        timeout_job.exc_info = "rq.timeouts.JobTimeoutException: Job exceeded maximum timeout value (900s)"
        timeout_job.created_at = datetime.now(timezone.utc)
        timeout_job.started_at = datetime.now(timezone.utc)
        timeout_job.ended_at = datetime.now(timezone.utc)

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [timeout_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            failed_jobs = get_failed_jobs_in_group("test_group_123")

            assert len(failed_jobs) == 1
            assert failed_jobs[0]["id"] == "timeout_job"
            assert failed_jobs[0]["workflow_step"] == "text_extraction"
            assert "JobTimeoutException" in failed_jobs[0]["failure_reason"]

    def test_job_memory_error_failure_scenario(self):
        """Test handling of job memory error failures."""
        memory_error_job = MagicMock(spec=Job)
        memory_error_job.id = "memory_error_job"
        memory_error_job.is_finished = True
        memory_error_job.is_failed = True
        memory_error_job.get_status.return_value = "failed"
        memory_error_job.meta = {"workflow_step": "analysis_and_preprocess"}
        memory_error_job.exc_info = "MemoryError: Unable to allocate memory for PDF processing"
        memory_error_job.created_at = datetime.now(timezone.utc)
        memory_error_job.started_at = datetime.now(timezone.utc)
        memory_error_job.ended_at = datetime.now(timezone.utc)

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [memory_error_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            failed_jobs = get_failed_jobs_in_group("test_group_123")

            assert len(failed_jobs) == 1
            assert "MemoryError" in failed_jobs[0]["failure_reason"]

    def test_job_dependency_failure_scenario(self):
        """Test workflow when job fails due to dependency failure."""
        # First job fails
        failed_dependency_job = MagicMock(spec=Job)
        failed_dependency_job.id = "analysis_job"
        failed_dependency_job.is_finished = True
        failed_dependency_job.is_failed = True
        failed_dependency_job.get_status.return_value = "failed"
        failed_dependency_job.meta = {"workflow_step": "analysis_and_preprocess"}

        # Dependent job should not start (or be cancelled)
        cancelled_job = MagicMock(spec=Job)
        cancelled_job.id = "text_extraction_job"
        cancelled_job.is_finished = False
        cancelled_job.is_failed = False
        cancelled_job.is_started = False
        cancelled_job.get_status.return_value = "deferred"  # RQ status for jobs waiting on dependencies
        cancelled_job.meta = {"workflow_step": "text_extraction"}

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [failed_dependency_job, cancelled_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "failed"  # Has failed jobs
            assert status["total_jobs"] == 2
            assert status["completed_jobs"] == 1  # Only the failed job "completed"
            assert status["failed_jobs"] == 1
            assert status["running_jobs"] == 0

    @pytest.mark.asyncio
    async def test_partial_workflow_restart_scenario(self, mock_document_workflow):
        """Test partial restart of workflow (failed jobs only)."""
        db_mock = AsyncMock()

        # Mock jobs: one completed, one failed
        completed_job = MagicMock(spec=Job)
        completed_job.id = "completed_job"
        completed_job.is_failed = False

        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job"
        failed_job.is_failed = True
        failed_job.requeue = MagicMock()

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [completed_job, failed_job]

        with (
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            result = await restart_failed_jobs_in_workflow(db_mock, mock_document_workflow)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["failed_job"]
            assert result["total_failed"] == 1

            # Only failed job should be requeued
            failed_job.requeue.assert_called_once()

            # Workflow status should be updated to running
            mock_update.assert_called_once_with(db_mock, mock_document_workflow, "running")

    @pytest.mark.asyncio
    async def test_full_workflow_restart_scenario(self, mock_document_workflow):
        """Test full restart of workflow (all jobs)."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        # Mock jobs: completed, failed, and running
        completed_job = MagicMock(spec=Job)
        completed_job.id = "completed_job"
        completed_job.is_failed = False
        completed_job.requeue = MagicMock()

        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job"
        failed_job.is_failed = True
        failed_job.requeue = MagicMock()

        running_job = MagicMock(spec=Job)
        running_job.id = "running_job"
        running_job.is_failed = False
        running_job.requeue = MagicMock()

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [completed_job, failed_job, running_job]

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.is_workflow_resumable", return_value=True),
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            result = await restart_failed_workflow(db_mock, document_id, partial_restart=False)

            assert result["success"] is True
            assert len(result["restarted_jobs"]) == 3  # All jobs restarted
            assert result["total_failed"] == 1  # Only one was actually failed
            assert result["restart_type"] == "full"

            # All jobs should be requeued
            completed_job.requeue.assert_called_once()
            failed_job.requeue.assert_called_once()
            running_job.requeue.assert_called_once()

            mock_update.assert_called_once_with(db_mock, mock_document_workflow, "running")

    @pytest.mark.asyncio
    async def test_restart_with_job_requeue_failure(self, mock_document_workflow):
        """Test restart scenario when job requeue fails."""
        db_mock = AsyncMock()

        # Mock failed job that fails to requeue
        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job"
        failed_job.is_failed = True
        failed_job.requeue.side_effect = Exception("Failed to requeue job")

        # Mock successful job
        successful_job = MagicMock(spec=Job)
        successful_job.id = "successful_job"
        successful_job.is_failed = True
        successful_job.requeue = MagicMock()

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [failed_job, successful_job]

        with (
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            result = await restart_failed_jobs_in_workflow(db_mock, mock_document_workflow)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["successful_job"]  # Only successful requeue
            assert result["total_failed"] == 2

            # Both jobs should have requeue attempted
            failed_job.requeue.assert_called_once()
            successful_job.requeue.assert_called_once()

            # Workflow should still be updated if any jobs were restarted
            mock_update.assert_called_once()

    def test_workflow_not_resumable_scenario(self):
        """Test scenario where workflow is not resumable (no failed jobs)."""
        # All jobs completed successfully
        completed_job1 = MagicMock(spec=Job)
        completed_job1.is_failed = False

        completed_job2 = MagicMock(spec=Job)
        completed_job2.is_failed = False

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [completed_job1, completed_job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            resumable = is_workflow_resumable("test_group_123")

            assert resumable is False

    def test_group_corruption_scenario(self):
        """Test handling of corrupted or inconsistent group state."""
        # Mock job that raises exception during processing
        corrupted_job = MagicMock(spec=Job)
        corrupted_job.id = "corrupted_job"
        corrupted_job.get_status.side_effect = Exception("Job data corrupted")
        corrupted_job.is_failed = True  # This should still work

        normal_job = MagicMock(spec=Job)
        normal_job.id = "normal_job"
        normal_job.is_failed = False
        normal_job.is_finished = True
        normal_job.get_status.return_value = "finished"
        normal_job.meta = {"workflow_step": "analysis"}
        normal_job.created_at = datetime.now(timezone.utc)
        normal_job.started_at = None
        normal_job.ended_at = None
        normal_job.result = None
        normal_job.exc_info = None

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [corrupted_job, normal_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            status = get_workflow_status_from_group("test_group_123")

            # Should handle corrupted job gracefully
            assert status["total_jobs"] == 2
            assert len(status["jobs"]) == 2

            # Find the corrupted job in results
            corrupted_job_result = next(job for job in status["jobs"] if job["id"] == "corrupted_job")
            assert corrupted_job_result["status"] == "error"
            assert "Job processing error" in corrupted_job_result["error"]

    def test_redis_connection_failure_scenario(self):
        """Test handling of Redis connection failures."""
        with patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Redis connection failed")):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "expired"
            assert "Group not found or expired" in status["error"]
            assert status["progress"] == 0.0
            assert status["total_jobs"] == 0

    def test_group_expiration_during_processing(self):
        """Test handling of group expiration during job processing."""
        # First call succeeds, second call fails (group expired)
        mock_group = MagicMock(spec=Group)
        mock_job = MagicMock(spec=Job)
        mock_job.id = "test_job"
        mock_job.is_failed = False
        mock_group.get_jobs.return_value = [mock_job]

        with patch(
            "extralit_server.contexts.workflows.Group.fetch", side_effect=[mock_group, Exception("Group expired")]
        ):
            # First call should succeed
            status1 = get_workflow_status_from_group("test_group_123")
            assert status1["status"] != "expired"

            # Second call should handle expiration
            status2 = get_workflow_status_from_group("test_group_123")
            assert status2["status"] == "expired"

    @pytest.mark.asyncio
    async def test_concurrent_restart_attempts(self, mock_document_workflow):
        """Test handling of concurrent restart attempts on the same workflow."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job"
        failed_job.is_failed = True
        failed_job.requeue = MagicMock()

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [failed_job]

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.is_workflow_resumable", return_value=True),
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group),
            patch("extralit_server.contexts.workflows.update_workflow_status"),
        ):
            # Simulate concurrent restart attempts
            import asyncio

            tasks = [
                restart_failed_workflow(db_mock, document_id, partial_restart=True),
                restart_failed_workflow(db_mock, document_id, partial_restart=True),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Both should succeed (RQ handles concurrency)
            for result in results:
                if isinstance(result, dict):
                    assert result["success"] is True
                    assert result["restarted_jobs"] == ["failed_job"]

    def test_large_workflow_failure_scenario(self):
        """Test handling of workflows with many jobs and mixed failure states."""
        # Create 50 jobs with mixed states
        jobs = []
        for i in range(50):
            job = MagicMock(spec=Job)
            job.id = f"job_{i}"
            job.meta = {"workflow_step": f"step_{i % 5}"}
            job.created_at = datetime.now(timezone.utc)
            job.started_at = None
            job.ended_at = None
            job.result = None
            job.exc_info = None

            if i < 30:  # 30 completed
                job.is_finished = True
                job.is_failed = False
                job.get_status.return_value = "finished"
            elif i < 40:  # 10 failed
                job.is_finished = True
                job.is_failed = True
                job.get_status.return_value = "failed"
                job.exc_info = f"Error in job {i}"
            else:  # 10 running
                job.is_finished = False
                job.is_failed = False
                job.is_started = True
                job.get_status.return_value = "started"

            jobs.append(job)

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = jobs

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            status = get_workflow_status_from_group("large_workflow_group")

            assert status["status"] == "failed"  # Has failed jobs
            assert status["total_jobs"] == 50
            assert status["completed_jobs"] == 40  # 30 successful + 10 failed
            assert status["failed_jobs"] == 10
            assert status["running_jobs"] == 10
            assert status["progress"] == 0.8  # 40/50 completed

            # Test failed job retrieval
            failed_jobs = get_failed_jobs_in_group("large_workflow_group")
            assert len(failed_jobs) == 10
            for i, failed_job in enumerate(failed_jobs):
                assert failed_job["id"] == f"job_{30 + i}"
                assert "Error in job" in failed_job["failure_reason"]

    @pytest.mark.asyncio
    async def test_workflow_restart_after_partial_completion(self, mock_document_workflow):
        """Test restarting workflow that had some jobs complete before failure."""
        db_mock = AsyncMock()

        # Simulate workflow that had analysis complete but text extraction failed
        analysis_job = MagicMock(spec=Job)
        analysis_job.id = "analysis_job"
        analysis_job.is_failed = False
        analysis_job.is_finished = True
        analysis_job.meta = {"workflow_step": "analysis_and_preprocess"}

        text_job = MagicMock(spec=Job)
        text_job.id = "text_extraction_job"
        text_job.is_failed = True
        text_job.requeue = MagicMock()
        text_job.meta = {"workflow_step": "text_extraction"}

        table_job = MagicMock(spec=Job)
        table_job.id = "table_extraction_job"
        table_job.is_failed = True  # Failed due to dependency
        table_job.requeue = MagicMock()
        table_job.meta = {"workflow_step": "table_extraction"}

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [analysis_job, text_job, table_job]

        with (
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            result = await restart_failed_jobs_in_workflow(db_mock, mock_document_workflow)

            assert result["success"] is True
            assert len(result["restarted_jobs"]) == 2  # Only failed jobs restarted
            assert "text_extraction_job" in result["restarted_jobs"]
            assert "table_extraction_job" in result["restarted_jobs"]
            assert result["total_failed"] == 2

            # Failed jobs should be requeued
            text_job.requeue.assert_called_once()
            table_job.requeue.assert_called_once()

            mock_update.assert_called_once_with(db_mock, mock_document_workflow, "running")
