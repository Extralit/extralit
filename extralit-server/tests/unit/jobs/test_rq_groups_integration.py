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

"""Unit tests for RQ Groups integration functions."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from rq.group import Group
from rq.job import Job

from extralit_server.contexts.workflows import (
    get_failed_jobs_in_group,
    get_jobs_by_reference,
    get_jobs_for_document,
    get_workflow_status,
    get_workflow_status_from_group,
    is_workflow_resumable,
    restart_failed_jobs_in_workflow,
    restart_failed_workflow,
)
from extralit_server.models.database import DocumentWorkflow


class TestRQGroupsIntegration:
    """Test RQ Groups integration functions."""

    @pytest.fixture
    def mock_document_workflow(self):
        """Create mock DocumentWorkflow."""
        workflow = MagicMock(spec=DocumentWorkflow)
        workflow.id = uuid4()
        workflow.document_id = uuid4()
        workflow.group_id = "test_group_123"
        workflow.status = "running"
        workflow.reference = "test_ref"
        workflow.workspace_id = uuid4()
        workflow.inserted_at = datetime.now(timezone.utc)
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    @pytest.fixture
    def mock_rq_job(self):
        """Create mock RQ Job."""
        job = MagicMock(spec=Job)
        job.id = "test_job_123"
        job.meta = {
            "document_id": str(uuid4()),
            "reference": "test_ref",
            "workflow_step": "analysis_and_preprocess",
            "workflow_id": str(uuid4()),
        }
        job.created_at = datetime.now(timezone.utc)
        job.started_at = datetime.now(timezone.utc)
        job.ended_at = None
        job.result = None
        job.exc_info = None
        job.is_finished = False
        job.is_failed = False
        job.is_started = True
        job.get_status.return_value = "started"
        return job

    @pytest.fixture
    def mock_rq_group(self, mock_rq_job):
        """Create mock RQ Group."""
        group = MagicMock(spec=Group)
        group.name = "test_group_123"
        group.get_jobs.return_value = [mock_rq_job]
        return group

    @pytest.mark.asyncio
    async def test_get_jobs_for_document_success(self, mock_document_workflow, mock_rq_group):
        """Test successful job retrieval for document using RQ Groups."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group),
        ):
            jobs = await get_jobs_for_document(db_mock, document_id)

            assert len(jobs) == 1
            assert jobs[0]["id"] == "test_job_123"
            assert jobs[0]["status"] == "started"
            assert jobs[0]["workflow_step"] == "analysis_and_preprocess"
            assert jobs[0]["document_id"] == document_id
            assert jobs[0]["group_id"] == "test_group_123"

    @pytest.mark.asyncio
    async def test_get_jobs_for_document_no_workflow(self):
        """Test job retrieval when no workflow exists."""
        db_mock = AsyncMock()
        document_id = uuid4()

        with patch.object(DocumentWorkflow, "get_by_document_id", return_value=None):
            jobs = await get_jobs_for_document(db_mock, document_id)

            assert jobs == []

    @pytest.mark.asyncio
    async def test_get_jobs_for_document_group_expired(self, mock_document_workflow):
        """Test job retrieval when RQ Group is expired or missing."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Group not found")),
        ):
            jobs = await get_jobs_for_document(db_mock, document_id)

            assert len(jobs) == 1
            assert jobs[0]["id"] == "group_expired"
            assert jobs[0]["status"] == "expired"
            assert "Group not found or expired" in jobs[0]["error"]

    @pytest.mark.asyncio
    async def test_get_jobs_by_reference_success(self, mock_document_workflow):
        """Test successful job retrieval by reference using RQ Groups."""
        db_mock = AsyncMock()
        reference = "test_ref"

        # Mock multiple workflows for the reference
        workflow1 = mock_document_workflow
        workflow2 = MagicMock(spec=DocumentWorkflow)
        workflow2.document_id = uuid4()
        workflow2.group_id = "test_group_456"

        with (
            patch.object(DocumentWorkflow, "get_by_reference", return_value=[workflow1, workflow2]),
            patch("extralit_server.contexts.workflows.get_jobs_for_document") as mock_get_jobs,
        ):
            # Mock return values for each document
            mock_get_jobs.side_effect = [
                [{"id": "job1", "document_id": workflow1.document_id}],
                [{"id": "job2", "document_id": workflow2.document_id}],
            ]

            jobs = await get_jobs_by_reference(db_mock, reference)

            assert len(jobs) == 2
            assert jobs[0]["id"] == "job1"
            assert jobs[1]["id"] == "job2"
            assert mock_get_jobs.call_count == 2

    @pytest.mark.asyncio
    async def test_get_jobs_by_reference_no_workflows(self):
        """Test job retrieval by reference when no workflows exist."""
        db_mock = AsyncMock()
        reference = "nonexistent_ref"

        with patch.object(DocumentWorkflow, "get_by_reference", return_value=[]):
            jobs = await get_jobs_by_reference(db_mock, reference)

            assert jobs == []

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self, mock_document_workflow):
        """Test successful workflow status retrieval using RQ Groups."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        mock_status = {
            "status": "running",
            "progress": 0.5,
            "total_jobs": 2,
            "completed_jobs": 1,
            "failed_jobs": 0,
            "running_jobs": 1,
            "jobs": [],
        }

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.get_workflow_status_from_group", return_value=mock_status),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            status = await get_workflow_status(db_mock, document_id)

            assert status["status"] == "running"
            assert status["progress"] == 0.5
            assert status["document_id"] == document_id
            assert status["workflow_id"] == mock_document_workflow.id
            assert status["group_id"] == "test_group_123"

            # Should not update status if it matches
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_workflow_status_no_workflow(self):
        """Test workflow status retrieval when no workflow exists."""
        db_mock = AsyncMock()
        document_id = uuid4()

        with patch.object(DocumentWorkflow, "get_by_document_id", return_value=None):
            status = await get_workflow_status(db_mock, document_id)

            assert status["status"] == "not_found"
            assert status["document_id"] == document_id
            assert status["progress"] == 0.0
            assert "No workflow found" in status["error"]

    def test_get_workflow_status_from_group_success(self, mock_rq_group, mock_rq_job):
        """Test workflow status calculation from RQ Group."""
        # Setup job states
        job1 = mock_rq_job
        job1.is_finished = True
        job1.is_failed = False
        job1.get_status.return_value = "finished"

        job2 = MagicMock(spec=Job)
        job2.id = "test_job_456"
        job2.is_finished = False
        job2.is_failed = False
        job2.is_started = True
        job2.get_status.return_value = "started"
        job2.meta = {"workflow_step": "text_extraction"}
        job2.created_at = datetime.now(timezone.utc)
        job2.started_at = datetime.now(timezone.utc)
        job2.ended_at = None
        job2.result = None
        job2.exc_info = None

        mock_rq_group.get_jobs.return_value = [job1, job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "running"  # Has running jobs
            assert status["progress"] == 0.5  # 1 of 2 completed
            assert status["total_jobs"] == 2
            assert status["completed_jobs"] == 1
            assert status["failed_jobs"] == 0
            assert status["running_jobs"] == 1
            assert len(status["jobs"]) == 2

    def test_get_workflow_status_from_group_expired(self):
        """Test workflow status when group is expired or missing."""
        with patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Group expired")):
            status = get_workflow_status_from_group("expired_group")

            assert status["status"] == "expired"
            assert status["progress"] == 0.0
            assert "Group not found or expired" in status["error"]

    def test_get_workflow_status_from_group_all_completed(self, mock_rq_group):
        """Test workflow status when all jobs are completed."""
        job1 = MagicMock(spec=Job)
        job1.is_finished = True
        job1.is_failed = False
        job1.get_status.return_value = "finished"

        job2 = MagicMock(spec=Job)
        job2.is_finished = True
        job2.is_failed = False
        job2.get_status.return_value = "finished"

        mock_rq_group.get_jobs.return_value = [job1, job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "completed"
            assert status["progress"] == 1.0
            assert status["completed_jobs"] == 2
            assert status["running_jobs"] == 0

    def test_get_workflow_status_from_group_with_failures(self, mock_rq_group):
        """Test workflow status when some jobs have failed."""
        job1 = MagicMock(spec=Job)
        job1.is_finished = True
        job1.is_failed = True
        job1.get_status.return_value = "failed"
        job1.exc_info = "Test error"

        job2 = MagicMock(spec=Job)
        job2.is_finished = True
        job2.is_failed = False
        job2.get_status.return_value = "finished"

        mock_rq_group.get_jobs.return_value = [job1, job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            status = get_workflow_status_from_group("test_group_123")

            assert status["status"] == "failed"  # Has failed jobs
            assert status["progress"] == 1.0  # Both jobs finished
            assert status["completed_jobs"] == 2
            assert status["failed_jobs"] == 1

    def test_is_workflow_resumable_with_failed_jobs(self, mock_rq_group):
        """Test workflow resumability when there are failed jobs."""
        failed_job = MagicMock(spec=Job)
        failed_job.is_failed = True

        completed_job = MagicMock(spec=Job)
        completed_job.is_failed = False

        mock_rq_group.get_jobs.return_value = [failed_job, completed_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            resumable = is_workflow_resumable("test_group_123")

            assert resumable is True

    def test_is_workflow_resumable_no_failed_jobs(self, mock_rq_group):
        """Test workflow resumability when there are no failed jobs."""
        completed_job1 = MagicMock(spec=Job)
        completed_job1.is_failed = False

        completed_job2 = MagicMock(spec=Job)
        completed_job2.is_failed = False

        mock_rq_group.get_jobs.return_value = [completed_job1, completed_job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            resumable = is_workflow_resumable("test_group_123")

            assert resumable is False

    def test_is_workflow_resumable_group_expired(self):
        """Test workflow resumability when group is expired."""
        with patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Group expired")):
            resumable = is_workflow_resumable("expired_group")

            assert resumable is False

    def test_get_failed_jobs_in_group_success(self, mock_rq_group):
        """Test retrieval of failed jobs from RQ Group."""
        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job_123"
        failed_job.is_failed = True
        failed_job.get_status.return_value = "failed"
        failed_job.exc_info = "Test failure reason"
        failed_job.meta = {"workflow_step": "analysis_and_preprocess"}
        failed_job.created_at = datetime.now(timezone.utc)
        failed_job.started_at = datetime.now(timezone.utc)
        failed_job.ended_at = datetime.now(timezone.utc)

        completed_job = MagicMock(spec=Job)
        completed_job.is_failed = False

        mock_rq_group.get_jobs.return_value = [failed_job, completed_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            failed_jobs = get_failed_jobs_in_group("test_group_123")

            assert len(failed_jobs) == 1
            assert failed_jobs[0]["id"] == "failed_job_123"
            assert failed_jobs[0]["status"] == "failed"
            assert failed_jobs[0]["failure_reason"] == "Test failure reason"
            assert failed_jobs[0]["workflow_step"] == "analysis_and_preprocess"

    def test_get_failed_jobs_in_group_no_failures(self, mock_rq_group):
        """Test retrieval of failed jobs when there are none."""
        completed_job1 = MagicMock(spec=Job)
        completed_job1.is_failed = False

        completed_job2 = MagicMock(spec=Job)
        completed_job2.is_failed = False

        mock_rq_group.get_jobs.return_value = [completed_job1, completed_job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group):
            failed_jobs = get_failed_jobs_in_group("test_group_123")

            assert failed_jobs == []

    def test_get_failed_jobs_in_group_expired(self):
        """Test failed job retrieval when group is expired."""
        with patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Group expired")):
            failed_jobs = get_failed_jobs_in_group("expired_group")

            assert failed_jobs == []

    @pytest.mark.asyncio
    async def test_restart_failed_jobs_in_workflow_success(self, mock_document_workflow, mock_rq_group):
        """Test successful restart of failed jobs in workflow."""
        db_mock = AsyncMock()

        failed_job = MagicMock(spec=Job)
        failed_job.id = "failed_job_123"
        failed_job.is_failed = True
        failed_job.requeue = MagicMock()

        completed_job = MagicMock(spec=Job)
        completed_job.is_failed = False

        mock_rq_group.get_jobs.return_value = [failed_job, completed_job]

        with (
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            result = await restart_failed_jobs_in_workflow(db_mock, mock_document_workflow)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["failed_job_123"]
            assert result["total_failed"] == 1
            failed_job.requeue.assert_called_once()
            mock_update.assert_called_once_with(db_mock, mock_document_workflow, "running")

    @pytest.mark.asyncio
    async def test_restart_failed_jobs_in_workflow_group_expired(self, mock_document_workflow):
        """Test restart when group is expired."""
        db_mock = AsyncMock()

        with patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Group expired")):
            result = await restart_failed_jobs_in_workflow(db_mock, mock_document_workflow)

            assert result["success"] is False
            assert "Group not found or expired" in result["error"]
            assert result["restarted_jobs"] == []

    @pytest.mark.asyncio
    async def test_restart_failed_workflow_partial_success(self, mock_document_workflow):
        """Test partial workflow restart (failed jobs only)."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.is_workflow_resumable", return_value=True),
            patch("extralit_server.contexts.workflows.restart_failed_jobs_in_workflow") as mock_restart,
        ):
            mock_restart.return_value = {"success": True, "restarted_jobs": ["job1", "job2"], "total_failed": 2}

            result = await restart_failed_workflow(db_mock, document_id, partial_restart=True)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["job1", "job2"]
            assert result["total_failed"] == 2
            mock_restart.assert_called_once_with(db_mock, mock_document_workflow)

    @pytest.mark.asyncio
    async def test_restart_failed_workflow_full_restart(self, mock_document_workflow, mock_rq_group):
        """Test full workflow restart (all jobs)."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        job1 = MagicMock(spec=Job)
        job1.id = "job1"
        job1.is_failed = True
        job1.requeue = MagicMock()

        job2 = MagicMock(spec=Job)
        job2.id = "job2"
        job2.is_failed = False
        job2.requeue = MagicMock()

        mock_rq_group.get_jobs.return_value = [job1, job2]

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.is_workflow_resumable", return_value=True),
            patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_rq_group),
            patch("extralit_server.contexts.workflows.update_workflow_status") as mock_update,
        ):
            result = await restart_failed_workflow(db_mock, document_id, partial_restart=False)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["job1", "job2"]
            assert result["total_failed"] == 1  # Only job1 was failed
            assert result["restart_type"] == "full"

            # Both jobs should be requeued
            job1.requeue.assert_called_once()
            job2.requeue.assert_called_once()
            mock_update.assert_called_once_with(db_mock, mock_document_workflow, "running")

    @pytest.mark.asyncio
    async def test_restart_failed_workflow_no_workflow(self):
        """Test restart when no workflow exists."""
        db_mock = AsyncMock()
        document_id = uuid4()

        with patch.object(DocumentWorkflow, "get_by_document_id", return_value=None):
            result = await restart_failed_workflow(db_mock, document_id)

            assert result["success"] is False
            assert "No workflow found" in result["error"]

    @pytest.mark.asyncio
    async def test_restart_failed_workflow_not_resumable(self, mock_document_workflow):
        """Test restart when workflow is not resumable."""
        db_mock = AsyncMock()
        document_id = mock_document_workflow.document_id

        with (
            patch.object(DocumentWorkflow, "get_by_document_id", return_value=mock_document_workflow),
            patch("extralit_server.contexts.workflows.is_workflow_resumable", return_value=False),
        ):
            result = await restart_failed_workflow(db_mock, document_id)

            assert result["success"] is False
            assert "not in a resumable state" in result["error"]
