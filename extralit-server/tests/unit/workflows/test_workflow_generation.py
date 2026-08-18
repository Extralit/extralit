"""Tests for the guard every artifact writer checks before it commits."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts.workflows import writer_skip_reason

MODULE = "extralit_server.contexts.workflows"

pytestmark = pytest.mark.asyncio


def db(document_exists: bool = True) -> AsyncMock:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=uuid4() if document_exists else None)
    return session


class TestWriterSkipReason:
    async def test_the_newest_run_may_write(self):
        workflow = MagicMock(id=uuid4())

        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock(return_value=workflow)):
            assert await writer_skip_reason(db(), uuid4(), str(workflow.id)) is None

    async def test_a_superseded_run_is_told_why(self):
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock(return_value=MagicMock(id=uuid4()))):
            assert await writer_skip_reason(db(), uuid4(), str(uuid4())) == "workflow superseded"

    async def test_a_deleted_document_is_told_why(self):
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock()) as lookup:
            assert await writer_skip_reason(db(document_exists=False), uuid4(), str(uuid4())) == "document deleted"

        # Deletion wins outright; a superseded run of a deleted document is still just deleted.
        lookup.assert_not_awaited()

    async def test_a_job_without_a_workflow_may_always_write(self):
        # Direct calls and ad-hoc enqueues carry no workflow; they must not be gated on one.
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock()) as lookup:
            assert await writer_skip_reason(db(), uuid4(), None) is None

        lookup.assert_not_awaited()

    async def test_a_document_without_a_workflow_row_may_write(self):
        with patch(f"{MODULE}.DocumentWorkflow.get_by_document_id", AsyncMock(return_value=None)):
            assert await writer_skip_reason(db(), uuid4(), str(uuid4())) is None
