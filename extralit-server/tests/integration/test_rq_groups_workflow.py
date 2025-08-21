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

"""Integration tests for complete workflow using RQ Groups."""

import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from rq.group import Group
from rq.job import Job

from extralit_server.contexts.workflows import (
    get_jobs_for_document,
    get_workflow_status,
    restart_failed_workflow,
)
from extralit_server.models.database import Document, DocumentWorkflow, Workspace
from extralit_server.workflows.documents import create_document_workflow


@pytest.mark.asyncio
class TestRQGroupsWorkflowIntegration:
    """Integration tests for RQ Groups workflow functionality."""

    @pytest.fixture
    async def test_workspace(self, async_db):
        """Create test workspace."""
        workspace = Workspace(
            id=uuid4(),
            name="test_workspace",
            title="Test Workspace",
            description="Test workspace for RQ Groups integration tests",
        )
        async_db.add(workspace)
        await async_db.commit()
        await async_db.refresh(workspace)
        return workspace

    @pytest.fixture
    async def test_document(self, async_db, test_workspace):
        """Create test document."""
        document = Document(
            id=uuid4(),
            reference="test_ref_123",
            file_name="test.pdf",
            workspace_id=test_workspace.id,
            url="s3://test-bucket/test.pdf",
            metadata_={},
        )
        async_db.add(document)
        await async_db.commit()
        await async_db.refresh(document)
        return document

    @pytest.fixture
    def mock_redis_connection(self):
        """Mock Redis connection for RQ Groups."""
        with (
            patch("extralit_server.workflows.documents.REDIS_CONNECTION") as mock_conn,
            patch("extralit_server.contexts.workflows.REDIS_CONNECTION", mock_conn),
        ):
            yield mock_conn

    @pytest.fixture
    def mock_rq_queues(self):
        """Mock RQ queues."""
        with (
            patch("extralit_server.workflows.documents.DEFAULT_QUEUE") as mock_default,
            patch("extralit_server.workflows.documents.OCR_QUEUE") as mock_ocr,
        ):
            # Setup queue prepare_data methods
            mock_default.prepare_data.return_value = {
                "func": "analysis_and_preprocess_job",
                "args": [],
                "kwargs": {},
                "timeout": 600,
                "job_id": "test_job_1",
            }

            mock_ocr.prepare_data.return_value = {
                "func": "text_extraction_job",
                "args": [],
                "kwargs": {},
                "timeout": 900,
                "job_id": "test_job_2",
            }

            yield mock_default, mock_ocr

    async def test_create_document_workflow_with_rq_groups(
        self, async_db, test_document, test_workspace, mock_redis_connection, mock_rq_queues
    ):
        """Test creating document workflow with RQ Groups integration."""
        mock_default_queue, mock_ocr_queue = mock_rq_queues

        # Mock RQ Group
        mock_group = MagicMock(spec=Group)
        mock_group.name = f"document_workflow_{test_document.id}_12345678"

        with patch("extralit_server.workflows.documents.Group", return_value=mock_group):
            group = await create_document_workflow(
                document_id=test_document.id,
                s3_url=test_document.url,
                reference=test_document.reference,
                workspace_name=test_workspace.name,
                workspace_id=test_workspace.id,
            )

            # Verify group was created
            assert group == mock_group

            # Verify DocumentWorkflow record was created
            workflow = await DocumentWorkflow.get_by_document_id(async_db, test_document.id)
            assert workflow is not None
            assert workflow.document_id == test_document.id
            assert workflow.workflow_type == "pdf_processing"
            assert workflow.status == "running"
            assert workflow.group_id.startswith(f"document_workflow_{test_document.id}")

            # Verify jobs were prepared and enqueued
            mock_default_queue.prepare_data.assert_called_once()
            mock_ocr_queue.prepare_data.assert_called_once()
            mock_group.enqueue_many.assert_called()

    async def test_workflow_status_tracking_with_rq_groups(self, async_db, test_document, mock_redis_connection):
        """Test workflow status tracking using RQ Groups."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="test_group_123",
            status="running",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Mock RQ Group with jobs
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = "job1"
        mock_job1.is_finished = True
        mock_job1.is_failed = False
        mock_job1.get_status.return_value = "finished"
        mock_job1.meta = {"workflow_step": "analysis_and_preprocess"}
        mock_job1.created_at = None
        mock_job1.started_at = None
        mock_job1.ended_at = None
        mock_job1.result = None
        mock_job1.exc_info = None

        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = "job2"
        mock_job2.is_finished = False
        mock_job2.is_failed = False
        mock_job2.is_started = True
        mock_job2.get_status.return_value = "started"
        mock_job2.meta = {"workflow_step": "text_extraction"}
        mock_job2.created_at = None
        mock_job2.started_at = None
        mock_job2.ended_at = None
        mock_job2.result = None
        mock_job2.exc_info = None

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [mock_job1, mock_job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            status = await get_workflow_status(async_db, test_document.id)

            assert status["status"] == "running"
            assert status["progress"] == 0.5  # 1 of 2 jobs completed
            assert status["total_jobs"] == 2
            assert status["completed_jobs"] == 1
            assert status["failed_jobs"] == 0
            assert status["running_jobs"] == 1
            assert status["document_id"] == test_document.id
            assert status["group_id"] == "test_group_123"

    async def test_workflow_restart_with_rq_groups(self, async_db, test_document, mock_redis_connection):
        """Test workflow restart functionality using RQ Groups."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="test_group_123",
            status="failed",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Mock failed job
        mock_failed_job = MagicMock(spec=Job)
        mock_failed_job.id = "failed_job"
        mock_failed_job.is_failed = True
        mock_failed_job.requeue = MagicMock()

        # Mock completed job
        mock_completed_job = MagicMock(spec=Job)
        mock_completed_job.id = "completed_job"
        mock_completed_job.is_failed = False

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [mock_failed_job, mock_completed_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            result = await restart_failed_workflow(async_db, test_document.id, partial_restart=True)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["failed_job"]
            assert result["total_failed"] == 1

            # Verify failed job was requeued
            mock_failed_job.requeue.assert_called_once()

            # Verify workflow status was updated
            await async_db.refresh(workflow)
            assert workflow.status == "running"

    async def test_job_querying_with_rq_groups(self, async_db, test_document, mock_redis_connection):
        """Test job querying functionality using RQ Groups."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="test_group_123",
            status="running",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Mock RQ jobs with metadata
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = "analysis_job"
        mock_job1.get_status.return_value = "finished"
        mock_job1.meta = {
            "document_id": str(test_document.id),
            "reference": test_document.reference,
            "workflow_step": "analysis_and_preprocess",
            "workflow_id": str(workflow.id),
        }
        mock_job1.created_at = None
        mock_job1.started_at = None
        mock_job1.ended_at = None
        mock_job1.result = {"analysis_complete": True}
        mock_job1.exc_info = None
        mock_job1.is_finished = True

        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = "text_extraction_job"
        mock_job2.get_status.return_value = "started"
        mock_job2.meta = {
            "document_id": str(test_document.id),
            "reference": test_document.reference,
            "workflow_step": "text_extraction",
            "workflow_id": str(workflow.id),
        }
        mock_job2.created_at = None
        mock_job2.started_at = None
        mock_job2.ended_at = None
        mock_job2.result = None
        mock_job2.exc_info = None
        mock_job2.is_finished = False

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [mock_job1, mock_job2]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            jobs = await get_jobs_for_document(async_db, test_document.id)

            assert len(jobs) == 2

            # Verify job details
            analysis_job = next(job for job in jobs if job["id"] == "analysis_job")
            assert analysis_job["status"] == "finished"
            assert analysis_job["workflow_step"] == "analysis_and_preprocess"
            assert analysis_job["document_id"] == test_document.id
            assert analysis_job["group_id"] == "test_group_123"
            assert analysis_job["result"] == {"analysis_complete": True}

            text_job = next(job for job in jobs if job["id"] == "text_extraction_job")
            assert text_job["status"] == "started"
            assert text_job["workflow_step"] == "text_extraction"
            assert text_job["result"] is None

    async def test_workflow_group_expiration_handling(self, async_db, test_document, mock_redis_connection):
        """Test handling of expired RQ Groups."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="expired_group_123",
            status="running",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Mock expired group
        with patch("extralit_server.contexts.workflows.Group.fetch", side_effect=Exception("Group expired")):
            jobs = await get_jobs_for_document(async_db, test_document.id)

            assert len(jobs) == 1
            assert jobs[0]["id"] == "group_expired"
            assert jobs[0]["status"] == "expired"
            assert "Group not found or expired" in jobs[0]["error"]

    async def test_workflow_api_integration_with_rq_groups(
        self, async_client: AsyncClient, owner_auth_header: dict, async_db, test_document
    ):
        """Test workflow API endpoints with RQ Groups integration."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="api_test_group_123",
            status="running",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Mock RQ Group for API calls
        mock_job = MagicMock(spec=Job)
        mock_job.id = "api_test_job"
        mock_job.get_status.return_value = "started"
        mock_job.meta = {
            "document_id": str(test_document.id),
            "reference": test_document.reference,
            "workflow_step": "analysis_and_preprocess",
        }
        mock_job.created_at = None
        mock_job.started_at = None
        mock_job.ended_at = None
        mock_job.result = None
        mock_job.exc_info = None
        mock_job.is_finished = False

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [mock_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            # Test jobs API with document_id filter
            response = await async_client.get(
                f"/api/v1/jobs/?document_id={test_document.id}", headers=owner_auth_header
            )

            assert response.status_code == 200
            jobs_data = response.json()
            assert len(jobs_data) == 1
            assert jobs_data[0]["id"] == "api_test_job"
            assert jobs_data[0]["status"] == "started"
            assert jobs_data[0]["workflow_step"] == "analysis_and_preprocess"

    async def test_concurrent_workflow_processing(
        self, async_db, test_workspace, mock_redis_connection, mock_rq_queues
    ):
        """Test multiple concurrent workflows using RQ Groups."""
        mock_default_queue, mock_ocr_queue = mock_rq_queues

        # Create multiple test documents
        documents = []
        for i in range(3):
            doc = Document(
                id=uuid4(),
                reference=f"concurrent_test_{i}",
                file_name=f"test_{i}.pdf",
                workspace_id=test_workspace.id,
                url=f"s3://test-bucket/test_{i}.pdf",
                metadata_={},
            )
            async_db.add(doc)
            documents.append(doc)

        await async_db.commit()

        # Mock RQ Groups for each workflow
        mock_groups = []
        for i, doc in enumerate(documents):
            mock_group = MagicMock(spec=Group)
            mock_group.name = f"document_workflow_{doc.id}_{i:08d}"
            mock_groups.append(mock_group)

        with patch("extralit_server.workflows.documents.Group", side_effect=mock_groups):
            # Create workflows concurrently
            tasks = []
            for doc in documents:
                task = create_document_workflow(
                    document_id=doc.id,
                    s3_url=doc.url,
                    reference=doc.reference,
                    workspace_name=test_workspace.name,
                    workspace_id=test_workspace.id,
                )
                tasks.append(task)

            # Execute all workflows concurrently
            results = await asyncio.gather(*tasks)

            # Verify all workflows were created
            assert len(results) == 3
            for i, group in enumerate(results):
                assert group == mock_groups[i]

            # Verify all DocumentWorkflow records were created
            for doc in documents:
                workflow = await DocumentWorkflow.get_by_document_id(async_db, doc.id)
                assert workflow is not None
                assert workflow.document_id == doc.id
                assert workflow.status == "running"

    async def test_workflow_failure_and_restart_scenarios(self, async_db, test_document, mock_redis_connection):
        """Test various workflow failure and restart scenarios."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="failure_test_group",
            status="failed",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Test scenario 1: Partial failure with some jobs completed
        mock_completed_job = MagicMock(spec=Job)
        mock_completed_job.id = "completed_job"
        mock_completed_job.is_failed = False
        mock_completed_job.is_finished = True

        mock_failed_job = MagicMock(spec=Job)
        mock_failed_job.id = "failed_job"
        mock_failed_job.is_failed = True
        mock_failed_job.requeue = MagicMock()

        mock_group = MagicMock(spec=Group)
        mock_group.get_jobs.return_value = [mock_completed_job, mock_failed_job]

        with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
            # Test partial restart (failed jobs only)
            result = await restart_failed_workflow(async_db, test_document.id, partial_restart=True)

            assert result["success"] is True
            assert result["restarted_jobs"] == ["failed_job"]
            assert result["total_failed"] == 1
            mock_failed_job.requeue.assert_called_once()

            # Reset mock
            mock_failed_job.requeue.reset_mock()

            # Test full restart (all jobs)
            result = await restart_failed_workflow(async_db, test_document.id, partial_restart=False)

            assert result["success"] is True
            assert len(result["restarted_jobs"]) == 2  # Both jobs restarted
            assert result["restart_type"] == "full"

    async def test_workflow_progress_calculation(self, async_db, test_document, mock_redis_connection):
        """Test workflow progress calculation with various job states."""
        # Create workflow record
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=test_document.id,
            workflow_type="pdf_processing",
            workspace_id=test_document.workspace_id,
            reference=test_document.reference,
            group_id="progress_test_group",
            status="running",
        )
        async_db.add(workflow)
        await async_db.commit()

        # Test different progress scenarios
        test_scenarios = [
            # (completed, failed, running, expected_status, expected_progress)
            ([1, 1], [], [], "completed", 1.0),  # All completed
            ([1], [1], [], "failed", 1.0),  # Mixed with failures
            ([1], [], [1], "running", 0.5),  # Half completed, half running
            ([], [], [2], "running", 0.0),  # All running
            ([], [], [], "pending", 0.0),  # No jobs started
        ]

        for completed_count, failed_count, running_count, expected_status, expected_progress in test_scenarios:
            mock_jobs = []

            # Add completed jobs
            for i in range(len(completed_count)):
                job = MagicMock(spec=Job)
                job.id = f"completed_{i}"
                job.is_finished = True
                job.is_failed = False
                job.is_started = True
                job.get_status.return_value = "finished"
                job.meta = {}
                job.created_at = None
                job.started_at = None
                job.ended_at = None
                job.result = None
                job.exc_info = None
                mock_jobs.append(job)

            # Add failed jobs
            for i in range(len(failed_count)):
                job = MagicMock(spec=Job)
                job.id = f"failed_{i}"
                job.is_finished = True
                job.is_failed = True
                job.is_started = True
                job.get_status.return_value = "failed"
                job.meta = {}
                job.created_at = None
                job.started_at = None
                job.ended_at = None
                job.result = None
                job.exc_info = "Test error"
                mock_jobs.append(job)

            # Add running jobs
            for i in range(len(running_count)):
                job = MagicMock(spec=Job)
                job.id = f"running_{i}"
                job.is_finished = False
                job.is_failed = False
                job.is_started = True
                job.get_status.return_value = "started"
                job.meta = {}
                job.created_at = None
                job.started_at = None
                job.ended_at = None
                job.result = None
                job.exc_info = None
                mock_jobs.append(job)

            mock_group = MagicMock(spec=Group)
            mock_group.get_jobs.return_value = mock_jobs

            with patch("extralit_server.contexts.workflows.Group.fetch", return_value=mock_group):
                status = await get_workflow_status(async_db, test_document.id)

                assert status["status"] == expected_status, f"Expected {expected_status}, got {status['status']}"
                assert status["progress"] == expected_progress, (
                    f"Expected {expected_progress}, got {status['progress']}"
                )
