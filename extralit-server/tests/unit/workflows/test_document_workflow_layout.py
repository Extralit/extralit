"""Tests for how the layout job is sequenced into the document workflow."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

MODULE = "extralit_server.workflows.documents"


@pytest.fixture
def enqueued():
    """Capture prepare_data calls and enqueue_many batches without touching Redis."""
    calls = {"prepared": [], "batches": []}

    def prepare_data(func, args=None, **kwargs):
        record = {"func": func, "args": args, **kwargs}
        calls["prepared"].append(record)
        return record

    def enqueue_many(queue=None, job_datas=None):
        calls["batches"].append(job_datas)
        return [MagicMock(name=f"job-{d.get('job_id')}", _data=d) for d in (job_datas or [])]

    group = MagicMock()
    group.enqueue_many.side_effect = enqueue_many

    with (
        patch(f"{MODULE}.DEFAULT_QUEUE") as default_queue,
        patch(f"{MODULE}.OCR_QUEUE") as ocr_queue,
        patch(f"{MODULE}.Group", return_value=group),
        patch(f"{MODULE}.AsyncSessionLocal") as session,
    ):
        default_queue.prepare_data.side_effect = prepare_data
        ocr_queue.prepare_data.side_effect = prepare_data
        db = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        session.return_value.__aenter__ = AsyncMock(return_value=db)
        session.return_value.__aexit__ = AsyncMock(return_value=False)
        yield calls


async def run_workflow(layout_parser=None):
    from extralit_server.workflows.documents import create_document_workflow

    return await create_document_workflow(
        document_id=uuid4(),
        s3_url="/api/v1/file/ws/documents/doc.pdf",
        reference="ref-1",
        workspace_name="ws",
        workspace_id=uuid4(),
        layout_parser=layout_parser,
    )


def prepared_for(calls, step):
    return next((c for c in calls["prepared"] if c.get("meta", {}).get("workflow_step") == step), None)


@pytest.mark.asyncio
class TestLayoutJobSequencing:
    async def test_no_layout_job_is_enqueued_by_default(self, enqueued):
        await run_workflow(layout_parser=None)

        assert prepared_for(enqueued, "document_layout") is None

    async def test_layout_job_is_enqueued_when_a_parser_is_named(self, enqueued):
        await run_workflow(layout_parser="pdf_inspector")

        layout = prepared_for(enqueued, "document_layout")
        assert layout is not None
        assert layout["args"][3] == "pdf_inspector"

    async def test_layout_job_depends_on_preprocessing(self, enqueued):
        # Preprocessing rotates pages and overwrites the PDF in place; running layout first
        # would persist bboxes describing a PDF that nobody renders.
        await run_workflow(layout_parser="pdf_inspector")

        layout = prepared_for(enqueued, "document_layout")
        assert layout["depends_on"] is not None

    async def test_layout_depends_on_the_analysis_job_specifically(self, enqueued):
        await run_workflow(layout_parser="pdf_inspector")

        analysis = prepared_for(enqueued, "analysis_and_preprocess")
        layout = prepared_for(enqueued, "document_layout")

        assert layout["depends_on"]._data["job_id"] == analysis["job_id"]

    async def test_text_extraction_is_not_blocked_on_layout(self, enqueued):
        await run_workflow(layout_parser="pdf_inspector")

        text_extraction = prepared_for(enqueued, "text_extraction")
        assert text_extraction.get("depends_on") is None

    async def test_layout_is_enqueued_after_the_analysis_batch(self, enqueued):
        await run_workflow(layout_parser="pdf_inspector")

        # The analysis job must already be enqueued before layout can depend on it.
        batch_steps = [[d["meta"]["workflow_step"] for d in batch] for batch in enqueued["batches"]]
        assert batch_steps.index(["analysis_and_preprocess"]) < batch_steps.index(["document_layout"])
