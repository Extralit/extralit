"""Tests for the per-document artifact fan-out."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts import files

pytestmark = pytest.mark.asyncio

WORKSPACE = "ws1"


class TestDeleteDocumentArtifacts:
    async def test_every_artifact_of_the_document_is_removed(self):
        document_id = uuid4()

        with (
            patch.object(files, "delete_object", AsyncMock()) as delete_object,
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock()) as delete_layout,
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, document_id)

        deleted = [call.args[2] for call in delete_object.await_args_list]
        assert deleted == [f"pdf/{document_id}", f"thumbnails/{document_id}"]
        assert delete_layout.await_args.args[1:] == (WORKSPACE, document_id)

    async def test_a_failing_artifact_does_not_stop_the_others(self):
        document_id = uuid4()

        with (
            patch.object(files, "delete_object", AsyncMock(side_effect=RuntimeError("gone"))) as delete_object,
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock()) as delete_layout,
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, document_id)

        assert delete_object.await_count == 2
        assert delete_layout.await_count == 1

    async def test_a_failing_layout_delete_is_swallowed(self):
        with (
            patch.object(files, "delete_object", AsyncMock()),
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, uuid4())
