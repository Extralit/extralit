"""Tests for how the layout job is sequenced into the document workflow."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from rq.job import Job

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
        # Real Job instances: rq.job.Dependency type-checks what it is given.
        return [Job(id=d.get("job_id"), connection=MagicMock()) for d in (job_datas or [])]

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


async def run_workflow(layout_parser=None, document_id=None):
    from extralit_server.workflows.documents import create_document_workflow

    return await create_document_workflow(
        document_id=document_id or uuid4(),
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

        assert layout["depends_on"].dependencies[0].id == analysis["job_id"]

    async def test_text_extraction_depends_on_preprocessing(self, enqueued):
        # Text extraction reads margins written by preprocessing and must not race the PDF rewrite.
        await run_workflow(layout_parser="pdf_inspector")

        analysis = prepared_for(enqueued, "analysis_and_preprocess")
        text_extraction = prepared_for(enqueued, "text_extraction")

        assert text_extraction["depends_on"].dependencies[0].id == analysis["job_id"]

    async def test_dependents_are_not_stranded_when_preprocessing_fails(self, enqueued):
        # Rotation is best effort; without allow_failure RQ leaves dependents DEFERRED forever.
        await run_workflow(layout_parser="pdf_inspector")

        for step in ("text_extraction", "document_layout"):
            assert prepared_for(enqueued, step)["depends_on"].allow_failure is True

    async def test_layout_is_enqueued_after_the_analysis_batch(self, enqueued):
        await run_workflow(layout_parser="pdf_inspector")

        # The analysis job must already be enqueued before layout can depend on it.
        batch_steps = [[d["meta"]["workflow_step"] for d in batch] for batch in enqueued["batches"]]
        assert batch_steps.index(["analysis_and_preprocess"]) < batch_steps.index(["document_layout"])


@pytest.mark.asyncio
class TestJobRetentionAndIdentity:
    async def test_every_job_carries_retry_and_a_long_result_ttl(self, enqueued):
        # @job decorator values are inert under Queue.prepare_data(); without these the default
        # 500s result TTL expires finished jobs and the derived workflow status decays to pending.
        await run_workflow(layout_parser="pdf_inspector")

        assert enqueued["prepared"]
        for prepared in enqueued["prepared"]:
            assert prepared["retry"] is not None
            assert prepared["result_ttl"] >= 6 * 3600

    async def test_job_ids_are_unique_per_workflow_run(self, enqueued):
        document_id = uuid4()

        await run_workflow(layout_parser="pdf_inspector", document_id=document_id)
        first = {c["meta"]["workflow_step"]: c["job_id"] for c in enqueued["prepared"]}
        enqueued["prepared"].clear()

        await run_workflow(layout_parser="pdf_inspector", document_id=document_id)
        second = {c["meta"]["workflow_step"]: c["job_id"] for c in enqueued["prepared"]}

        assert first.keys() == second.keys()
        for step, job_id in first.items():
            assert str(document_id) in job_id
            assert job_id != second[step]
