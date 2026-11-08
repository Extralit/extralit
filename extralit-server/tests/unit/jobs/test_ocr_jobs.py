"""Tests for how the layout job orders its writes."""

import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata
from extralit_server.contexts.ocr.parsers.registry import default_service
from extralit_server.contexts.ocr.parsers.service import ParserService

FIXTURES = Path(__file__).parents[2] / "fixtures" / "pdf"

MODULE = "extralit_server.jobs.ocr_jobs"

pytestmark = pytest.mark.asyncio


class StubParser:
    def parse_pages(self, pdf_bytes, pages, *, ocr):
        return {p: [] for p in pages}


@pytest.fixture
def job_context(tmp_path, monkeypatch):
    """Everything the layout job touches outside its own logic, with the document present."""
    from extralit_server.contexts.ocr.layout_store import LayoutStore

    calls = []
    store = LayoutStore(str(tmp_path / "ws" / "layout"))
    pdf_bytes = (FIXTURES / "two_page.pdf").read_bytes()
    triage = TriageMetadata(
        pdf_type="mixed", page_count=2, pages_needing_ocr=[2], ocr_reasons_by_page={"2": ["invisible_text_layer"]}
    )
    service = ParserService({"pymupdf": StubParser(), "liteparse": StubParser()}, triage=lambda _: triage)
    layouts = []

    async def store_layout(s3_client, workspace_name, document_id, document, store=None):
        calls.append(("store_layout", store._lock_depth))
        return {"layout_url": "layout/x.docling.json", "items_uri": "items", "pages_uri": "pages"}

    async def update_metadata(db, document_id, mutate):
        calls.append(("update_metadata", store._lock_depth))
        holder = MagicMock()
        mutate(holder)
        layouts.append(holder.layout_metadata)
        return None

    db = MagicMock()

    with (
        patch(f"{MODULE}.files.get_storage", AsyncMock(return_value=AsyncMock())),
        patch(f"{MODULE}.files.download_file_content", AsyncMock(return_value=pdf_bytes)),
        patch(f"{MODULE}.default_service", return_value=service),
        patch(f"{MODULE}.LayoutStore.for_workspace", return_value=store),
        patch(f"{MODULE}.layout_storage.store_layout", store_layout),
        patch(f"{MODULE}.update_processing_metadata", update_metadata),
        patch(f"{MODULE}.get_current_job", return_value=MagicMock(meta={"workflow_id": "wf-1"})),
        patch(f"{MODULE}.writer_skip_reason", AsyncMock(return_value=None)) as skip,
        patch(f"{MODULE}.AsyncSessionLocal") as session,
    ):
        session.return_value.__aenter__ = AsyncMock(return_value=db)
        session.return_value.__aexit__ = AsyncMock(return_value=False)
        yield {"calls": calls, "store": store, "skip": skip, "layouts": layouts}


async def run_job(document_id=None, parser=None):
    from extralit_server.jobs.ocr_jobs import async_document_layout_job

    return await async_document_layout_job(
        document_id or uuid4(),
        "/api/v1/file/ws/pdf/doc.pdf",
        "ws",
        parser,
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
        job_context["skip"].return_value = "document deleted"

        result = await run_job()

        assert result["skipped"] == "document deleted"
        assert job_context["calls"] == []

    async def test_pages_needing_ocr_are_surfaced(self, job_context):
        result = await run_job()

        assert result["pages_needing_ocr"] == [2]


class TestExecutedPlanMetadata:
    async def test_the_executed_plan_is_recorded(self, job_context):
        result = await run_job()

        layout = job_context["layouts"][0]
        assert layout.parsers == {"pymupdf": [1], "liteparse": [2]}
        assert layout.parser == "liteparse+pymupdf"
        assert result["parsers"] == layout.parsers

    async def test_ocr_pages_exclude_pages_whose_text_layer_was_read(self, job_context):
        await run_job()

        layout = job_context["layouts"][0]
        assert layout.ocr_pages == []
        assert layout.ocr_skipped_pages == [2]
        assert layout.pages_needing_ocr == [2]

    async def test_the_parser_runs_off_the_event_loop(self, job_context):
        threads = []

        class Spy(StubParser):
            def parse_pages(self, pdf_bytes, pages, *, ocr):
                threads.append(threading.current_thread())
                return super().parse_pages(pdf_bytes, pages, ocr=ocr)

        service = ParserService(
            {"pymupdf": Spy(), "liteparse": Spy()}, triage=lambda _: TriageMetadata(pdf_type="mixed")
        )
        with patch(f"{MODULE}.default_service", return_value=service):
            await run_job()

        assert threads
        assert all(t is not threading.main_thread() for t in threads)

    async def test_layout_job_on_the_two_page_fixture_writes_parsers_and_ocr_pages(self, job_context):
        pytest.importorskip("pymupdf4llm")
        with patch(f"{MODULE}.default_service", default_service):
            await run_job()

        layout = job_context["layouts"][0]
        assert layout.parsers == {"pymupdf": [1, 2]}
        assert layout.ocr_pages == []
        assert layout.num_pages == 2


class TestSupersededRuns:
    async def test_a_superseded_run_does_not_write(self, job_context):
        # Stopping a started job is only a request, so a forced restart can overlap this run.
        job_context["skip"].return_value = "workflow superseded"

        result = await run_job()

        assert job_context["skip"].await_args.args[2] == "wf-1"
        assert result["skipped"] == "workflow superseded"
        assert job_context["calls"] == []
