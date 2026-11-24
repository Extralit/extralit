"""Tests for the triage + margins + rotation job."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata
from extralit_server.contexts.files import DocumentFile
from extralit_server.jobs.document_jobs import analysis_and_preprocess_job

MODULE = "extralit_server.jobs.document_jobs"

DOCUMENT_ID = uuid4()
PREFIX = f"documents/{DOCUMENT_ID}"
S3_URL = f"/api/v1/file/test-workspace/{PREFIX}/1_orig.pdf"
UPLOADED_NAME = "Smith 2020 - malaria.pdf"
WORKSPACE = "test-workspace"
LAYOUT_ANALYSIS = {
    "pages_sampled": 5,
    "page_dimensions": {"width": 612, "height": 792},
    "layout_analysis": {"estimated_margins": {"left_px": 40, "top_px": 60, "right_px": 40, "bottom_px": 60}},
}


def triage(**overrides) -> TriageMetadata:
    return TriageMetadata(
        **{
            "pdf_type": "text_based",
            "confidence": 0.9,
            "page_count": 12,
            "pages_needing_ocr": [],
            "pages_with_tables": [3],
            **overrides,
        }
    )


@pytest.fixture
def job_context():
    """Everything the job talks to, with a well-behaved PDF."""
    current_job = MagicMock(meta={})
    analyzer = MagicMock()
    analyzer.analyze_pdf_layout.return_value = (LAYOUT_ANALYSIS, b"thumbnail-bytes")
    response = MagicMock()
    response.processed_data = b"%PDF rotated"
    response.metadata.processing_time = 3.0
    response.metadata.rotation_ran = True
    response.metadata.error = None
    preprocessor = MagicMock()
    preprocessor.preprocess.return_value = response
    written: list[dict] = []

    async def put_object(client, workspace, key, data, **kwargs):
        written.append({"key": key, "data": data, **kwargs})

    with (
        patch(f"{MODULE}.files") as files,
        patch(f"{MODULE}.PDFAnalyzer", return_value=analyzer),
        patch(f"{MODULE}.PDFPreprocessor", return_value=preprocessor),
        patch(f"{MODULE}.triage_pdf", return_value=triage()) as triage_pdf,
        patch(f"{MODULE}.update_processing_metadata", AsyncMock()) as update_metadata,
        patch(f"{MODULE}.writer_skip_reason", AsyncMock(return_value=None)) as skip,
        patch(f"{MODULE}.get_current_job", return_value=current_job),
        patch(f"{MODULE}.AsyncSessionLocal") as session,
    ):
        files.get_storage = AsyncMock(return_value=MagicMock())
        files.read_object = AsyncMock(return_value=b"%PDF original")
        files.list_document_files = AsyncMock(
            return_value={1: DocumentFile(index=1, original_key=f"{PREFIX}/1_orig.pdf", extension="pdf")}
        )
        files.get_thumbnail_s3_object_path.return_value = f"{PREFIX}/thumbnail.png"
        files.get_ocr_pdf_s3_object_path.return_value = f"{PREFIX}/1.pdf"
        files.get_proxy_document_url.side_effect = lambda workspace, key: f"/api/v1/file/{workspace}/{key}"
        files.put_object = AsyncMock(side_effect=put_object)
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=UPLOADED_NAME)
        session.return_value.__aenter__ = AsyncMock(return_value=db)
        session.return_value.__aexit__ = AsyncMock(return_value=None)
        yield {
            "job": current_job,
            "files": files,
            "analyzer": analyzer,
            "preprocessor": preprocessor,
            "response": response,
            "triage_pdf": triage_pdf,
            "update_metadata": update_metadata,
            "written": written,
            "db": db,
            "skip": skip,
        }


async def run_job():
    return await analysis_and_preprocess_job(DOCUMENT_ID, S3_URL, "test_ref", WORKSPACE)


@pytest.mark.asyncio
class TestTriage:
    async def test_triage_is_persisted_and_returned(self, job_context):
        result = await run_job()

        analysis = result["analysis_result"]
        assert analysis["triage"]["pdf_type"] == "text_based"
        assert analysis["triage"]["pages_with_tables"] == [3]
        assert analysis["page_count"] == 12

    async def test_pages_needing_ocr_reach_the_job_meta(self, job_context):
        job_context["triage_pdf"].return_value = triage(pdf_type="image_based", pages_needing_ocr=[1, 2])

        await run_job()

        assert job_context["job"].meta["pages_needing_ocr"] == [1, 2]

    async def test_margins_are_estimated_from_the_leading_pages_only(self, job_context):
        from extralit_server.contexts.document.margin import MARGIN_SAMPLE_PAGES

        await run_job()

        _pdf, filename = job_context["analyzer"].analyze_pdf_layout.call_args.args
        assert filename == UPLOADED_NAME
        assert MARGIN_SAMPLE_PAGES == 5

    async def test_metadata_is_written_under_the_row_lock(self, job_context):
        await run_job()

        assert job_context["update_metadata"].await_count == 1


@pytest.mark.asyncio
class TestOriginalFilename:
    @pytest.mark.parametrize("url_name", ["1_orig.pdf", "1.pdf"])
    async def test_the_uploaded_name_is_recorded_whatever_the_url_says(self, job_context, url_name):
        # A forced rerun passes documents.url, which points at 1.pdf after the first run.
        await analysis_and_preprocess_job(
            DOCUMENT_ID, f"/api/v1/file/{WORKSPACE}/{PREFIX}/{url_name}", "test_ref", WORKSPACE
        )

        assert {w["metadata"]["original_filename"] for w in job_context["written"]} == {UPLOADED_NAME}
        assert job_context["analyzer"].analyze_pdf_layout.call_args.args[1] == UPLOADED_NAME

    @pytest.mark.parametrize("file_name", ["paper", "paper.bin", UPLOADED_NAME, None])
    async def test_rotation_is_gated_on_the_stored_key_not_the_uploaded_name(self, job_context, file_name):
        job_context["db"].scalar.return_value = file_name

        await run_job()

        assert job_context["preprocessor"].preprocess.call_args.args[1] == "1_orig.pdf"

    async def test_a_document_without_a_file_name_falls_back_to_a_fixed_name(self, job_context):
        job_context["db"].scalar.return_value = None

        await run_job()

        assert {w["metadata"]["original_filename"] for w in job_context["written"]} == {"1_orig.pdf"}


@pytest.mark.asyncio
class TestRotation:
    async def test_rotation_runs_on_every_pdf(self, job_context):
        # Not gated on triage: ocrmypdf's OSD is the only thing that can see a sideways page.
        job_context["triage_pdf"].return_value = triage(pdf_type="text_based", pages_needing_ocr=[])

        await run_job()

        job_context["preprocessor"].preprocess.assert_called_once()

    async def test_the_rotated_pdf_is_written_last_to_1_pdf_and_the_upload_is_kept(self, job_context):
        result = await run_job()

        keys = [write["key"] for write in job_context["written"]]
        assert keys[-1] == f"{PREFIX}/1.pdf"
        assert f"{PREFIX}/thumbnail.png" in keys
        assert f"{PREFIX}/1_orig.pdf" not in keys
        assert job_context["written"][-1]["data"] == b"%PDF rotated"
        assert job_context["written"][-1]["content_type"] == "application/pdf"
        assert result["preprocessing_result"]["processed_s3_url"].endswith(f"{PREFIX}/1.pdf")

    async def test_rotation_reads_1_orig_pdf_and_triage_and_margins_see_the_rotated_bytes(self, job_context):
        await run_job()

        assert job_context["files"].read_object.await_args.args[2] == f"{PREFIX}/1_orig.pdf"
        assert job_context["preprocessor"].preprocess.call_args.args[0] == b"%PDF original"
        assert job_context["triage_pdf"].call_args.args[0] == b"%PDF rotated"
        assert job_context["analyzer"].analyze_pdf_layout.call_args.args[0] == b"%PDF rotated"

    async def test_the_document_url_is_pointed_at_1_pdf(self, job_context):
        await run_job()

        url = job_context["update_metadata"].await_args.kwargs["url"]
        assert url == f"/api/v1/file/{WORKSPACE}/{PREFIX}/1.pdf"

    async def test_a_failed_rotation_is_recorded_and_the_job_still_succeeds(self, job_context):
        job_context["response"].metadata.rotation_ran = False
        job_context["response"].metadata.error = "ghostscript died"
        job_context["response"].processed_data = b"%PDF original"

        result = await run_job()

        preprocessing = result["preprocessing_result"]
        assert preprocessing["rotation_ran"] is False
        assert preprocessing["error"] == "ghostscript died"
        assert preprocessing["ocr_applied"] is False
        assert job_context["written"][-1]["data"] == b"%PDF original"

    async def test_a_missing_thumbnail_does_not_fail_the_job(self, job_context):
        job_context["analyzer"].analyze_pdf_layout.return_value = (LAYOUT_ANALYSIS, None)

        result = await run_job()

        assert result["analysis_result"]["thumbnail_generated"] is False
        assert [write["key"] for write in job_context["written"]] == [f"{PREFIX}/1.pdf"]


@pytest.mark.asyncio
class TestFailures:
    async def test_a_storage_failure_surfaces_on_the_job(self, job_context):
        job_context["files"].read_object = AsyncMock(side_effect=RuntimeError("s3 down"))

        with pytest.raises(RuntimeError, match="s3 down"):
            await run_job()

        assert job_context["job"].meta["error"] == "s3 down"

    async def test_a_failed_analysis_publishes_1_orig_pdf_as_1_pdf(self, job_context):
        files = job_context["files"]
        files.put_object_if_absent = AsyncMock(return_value=True)
        job_context["analyzer"].analyze_pdf_layout.side_effect = TimeoutError("margins took too long")

        with pytest.raises(TimeoutError):
            await run_job()

        files.put_object_if_absent.assert_awaited_once()
        _, workspace, key, data = files.put_object_if_absent.await_args.args
        assert (workspace, key, data) == (WORKSPACE, f"{PREFIX}/1.pdf", b"%PDF original")
        assert job_context["files"].read_object.await_args.args[2] == f"{PREFIX}/1_orig.pdf"
        assert job_context["update_metadata"].await_count == 0

    async def test_the_fallback_failing_does_not_mask_the_original_error(self, job_context):
        job_context["files"].put_object_if_absent = AsyncMock(side_effect=RuntimeError("s3 down"))
        job_context["analyzer"].analyze_pdf_layout.side_effect = TimeoutError("margins took too long")

        with pytest.raises(TimeoutError):
            await run_job()


@pytest.mark.asyncio
class TestNonPdfUploads:
    async def test_a_non_pdf_upload_fails_analysis_and_gets_no_processed_pdf(self, job_context):
        files = job_context["files"]
        files.list_document_files.return_value = {
            1: DocumentFile(index=1, original_key=f"{PREFIX}/1_orig.xlsx", extension="xlsx")
        }
        files.put_object_if_absent = AsyncMock(return_value=True)

        with pytest.raises(ValueError, match=r"file 1 is a \.xlsx upload; only PDFs are processed"):
            await run_job()

        assert job_context["written"] == []
        files.put_object_if_absent.assert_not_awaited()
        files.read_object.assert_not_awaited()
        job_context["preprocessor"].preprocess.assert_not_called()
        assert job_context["update_metadata"].await_count == 0

    async def test_a_document_without_an_upload_fails_with_its_directory_named(self, job_context):
        job_context["files"].list_document_files.return_value = {}
        job_context["files"].document_prefix.return_value = f"{PREFIX}/"

        with pytest.raises(FileNotFoundError, match="no uploaded file 1"):
            await run_job()


@pytest.mark.asyncio
class TestSupersededRuns:
    async def test_a_superseded_run_rewrites_nothing(self, job_context):
        job_context["skip"].return_value = "workflow superseded"

        result = await run_job()

        assert result["skipped"] == "workflow superseded"
        assert job_context["written"] == []
        assert job_context["update_metadata"].await_count == 0
