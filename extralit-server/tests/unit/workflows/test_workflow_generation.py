"""Tests for the workflow-generation guard every artifact writer checks."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts.workflows import is_current_workflow_run

MODULE = "extralit_server.contexts.workflows"

pytestmark = pytest.mark.asyncio


class TestIsCurrentWorkflowRun:
    async def test_the_newest_run_is_current(self):
        workflow = MagicMock(id=uuid4())

        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock(return_value=workflow)):
            assert await is_current_workflow_run(AsyncMock(), uuid4(), str(workflow.id)) is True

    async def test_a_superseded_run_is_not_current(self):
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock(return_value=MagicMock(id=uuid4()))):
            assert await is_current_workflow_run(AsyncMock(), uuid4(), str(uuid4())) is False

    async def test_a_job_without_a_workflow_is_always_current(self):
        # Direct calls and ad-hoc enqueues carry no workflow; they must not be gated on one.
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock()) as lookup:
            assert await is_current_workflow_run(AsyncMock(), uuid4(), None) is True

        lookup.assert_not_awaited()

    async def test_a_document_without_a_workflow_row_is_current(self):
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock(return_value=None)):
            assert await is_current_workflow_run(AsyncMock(), uuid4(), str(uuid4())) is True
