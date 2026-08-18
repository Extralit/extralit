"""Tests for how the layout job orders its writes."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

MODULE = "extralit_server.jobs.ocr_jobs"

pytestmark = pytest.mark.asyncio


@pytest.fixture
def job_context(tmp_path, monkeypatch):
    """Everything the layout job touches outside its own logic, with the document present."""
    from extralit_server.contexts.ocr.layout_store import LayoutStore

    calls = []
    store = LayoutStore(str(tmp_path / "ws" / "layout"))
    doc = MagicMock(version="1.7.0", pages={1: MagicMock()})
    doc.iterate_items.return_value = []

    async def store_layout(s3_client, workspace_name, document_id, document, store=None):
        calls.append(("store_layout", store._lock_depth))
        return {"layout_url": "layout/x.docling.json", "items_uri": "items", "pages_uri": "pages"}

    async def update_metadata(db, document_id, mutate):
        calls.append(("update_metadata", store._lock_depth))
        return None

    db = MagicMock()
    db.scalar = AsyncMock(return_value=uuid4())

    with (
        patch(f"{MODULE}.files.get_s3_client", AsyncMock(return_value=AsyncMock())),
        patch(f"{MODULE}.files.download_file_content", AsyncMock(return_value=b"%PDF-1.4")),
        patch(f"{MODULE}.route_parser", return_value=("pdf_inspector", {"pages_needing_ocr": [2]})),
        patch(f"{MODULE}.get_parser", return_value=lambda *args, **kwargs: doc),
        patch(f"{MODULE}.LayoutStore.for_workspace", return_value=store),
        patch(f"{MODULE}.storage.store_layout", store_layout),
        patch(f"{MODULE}.update_processing_metadata", update_metadata),
        patch(f"{MODULE}.get_current_job", return_value=MagicMock(meta={"workflow_id": "wf-1"})),
        patch(f"{MODULE}.is_current_workflow_run", AsyncMock(return_value=True)) as is_current,
        patch(f"{MODULE}.AsyncSessionLocal") as session,
    ):
        session.return_value.__aenter__ = AsyncMock(return_value=db)
        session.return_value.__aexit__ = AsyncMock(return_value=False)
        yield {"calls": calls, "db": db, "store": store, "is_current": is_current}


async def run_job(document_id=None):
    from extralit_server.jobs.ocr_jobs import async_document_layout_job

    return await async_document_layout_job(
        document_id or uuid4(),
        "/api/v1/file/ws/pdf/doc.pdf",
        "ws",
        "pdf_inspector",
    )


class TestLayoutJobOrdering:
    async def test_rows_are_written_under_the_workspace_lock(self, job_context):
        await run_job()

        assert ("store_layout", 1) in job_context["calls"]

    async def test_metadata_is_updated_after_the_lock_is_released(self, job_context):
        await run_job()

        steps = [name for name, _ in job_context["calls"]]
        assert steps == ["store_layout", "update_metadata"]
        assert ("update_metadata", 0) in job_context["calls"]

    async def test_a_document_deleted_mid_parse_is_not_resurrected(self, job_context):
        job_context["db"].scalar = AsyncMock(return_value=None)

        result = await run_job()

        assert result["skipped"] == "document deleted"
        assert job_context["calls"] == []

    async def test_pages_needing_ocr_are_surfaced(self, job_context):
        result = await run_job()

        assert result["pages_needing_ocr"] == [2]


class TestSupersededRuns:
    async def test_a_superseded_run_does_not_write(self, job_context):
        # Stopping a started job is only a request, so a forced restart can overlap this run.
        job_context["is_current"].return_value = False

        result = await run_job()

        assert job_context["is_current"].await_args.args[2] == "wf-1"
        assert result["skipped"] == "workflow superseded"
        assert job_context["calls"] == []
