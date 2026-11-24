"""Document upload job functions."""

import logging
from typing import Any
from uuid import UUID

from rq import Retry, get_current_job
from rq.decorators import job
from sqlalchemy import select

from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata
from extralit_server.contexts import files
from extralit_server.contexts.document.margin import PDFAnalyzer
from extralit_server.contexts.document.metadata import update_processing_metadata
from extralit_server.contexts.document.preprocessing import PDFPreprocessor
from extralit_server.contexts.ocr.triage import triage_pdf
from extralit_server.contexts.workflows import writer_skip_reason
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import DEFAULT_QUEUE, REDIS_CONNECTION
from extralit_server.models.database import Document

_LOGGER = logging.getLogger(__name__)


@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=600, retry=Retry(max=3, interval=[10, 30, 60]))
async def analysis_and_preprocess_job(
    document_id: UUID, s3_url: str, reference: str, workspace_name: str
) -> dict[str, Any]:
    """
    Rotate a PDF, triage it, estimate its margins, and record what was found.

    Only file 1 is processed, and only when it is a PDF. Everything downstream (triage, margins,
    layout parsers, the viewer) reads the rotated `1.pdf`, so bboxes and the displayed pages agree.
    `1_orig.pdf` is never rewritten, so a rerun starts clean.

    1. Rotation: ocrmypdf on `1_orig.pdf` with OCR disabled; best effort.
    2. Triage (pdf-inspector) and margins + thumbnail, all over the rotated bytes.
    3. Write the thumbnail, then `1.pdf` (dependents key on it), then the metadata and `documents.url`.

    Args:
        document_id: UUID of the document to process
        s3_url: proxy URL of the document's PDF; copied in as file 1 only when nothing was uploaded
        reference: Reference key for tracking
        workspace_name: Name of the workspace where the document is stored

    Returns:
        Dictionary containing combined analysis and preprocessing results
    """
    current_job = get_current_job()
    if current_job is None:
        raise Exception("No current job found")

    current_job.meta.update(
        {
            "document_id": str(document_id),
            "reference": reference,
            "workspace_name": str(workspace_name),
            "workflow_step": "analysis_and_preprocess",
        }
    )
    current_job.save_meta()

    try:
        storage = await files.get_storage()
        original = await _original_pdf_key(storage, workspace_name, document_id, s3_url)
        source = await files.read_object(storage, workspace_name, original)
        # The object keys are fixed names, so the uploaded name comes from the row, not the URL.
        async with AsyncSessionLocal() as db:
            filename = await db.scalar(select(Document.file_name).where(Document.id == document_id))
        filename = filename or original.rsplit("/", 1)[-1]

        # Rotation runs on every PDF: ocrmypdf's OSD is the only thing that knows which scanned
        # pages are sideways, and under skip_text a born-digital page passes through untouched.
        # The preprocessor gates on a `.pdf` name, which the stored key always has and `file_name` may not.
        processing_response = PDFPreprocessor().preprocess(source, original.rsplit("/", 1)[-1])
        if not processing_response.metadata.rotation_ran:
            _LOGGER.warning(f"Rotation did not run for document {document_id}: {processing_response.metadata.error}")
        pdf_data = processing_response.processed_data

        triage = triage_pdf(pdf_data)

        layout_analysis, thumbnail_data = PDFAnalyzer().analyze_pdf_layout(pdf_data, filename)

        analysis_result = {
            "document_id": str(document_id),
            "triage": triage.model_dump(),
            "page_count": triage.page_count,
            "layout_analysis": layout_analysis,
            "thumbnail_generated": False,
        }

        # A forced restart may already be running; its rotation and metadata must not lose to this
        # one's, because stopping a started job is only a request.
        async with AsyncSessionLocal() as db:
            skip = await writer_skip_reason(db, document_id, current_job.meta.get("workflow_id"))
        if skip is not None:
            _LOGGER.info(f"Analysis for document {document_id} was not stored: {skip}")
            return {"document_id": str(document_id), "skipped": skip}

        # The rotated PDF is the last S3 write of this job — dependents key on it.
        ocr_object_path = files.get_ocr_pdf_s3_object_path(document_id)
        ocr_url = files.get_proxy_document_url(workspace_name, ocr_object_path)

        if thumbnail_data is not None:
            try:
                await files.put_object(
                    storage,
                    workspace_name,
                    files.get_thumbnail_s3_object_path(document_id),
                    thumbnail_data,
                    content_type="image/png",
                    metadata={"original_filename": filename},
                )
                analysis_result["thumbnail_generated"] = True
            except Exception as e:
                _LOGGER.warning(f"Failed to store the thumbnail for document {document_id}: {e}")
        else:
            _LOGGER.warning(f"No thumbnail data available for document {document_id}")

        await files.put_object(
            storage,
            workspace_name,
            ocr_object_path,
            pdf_data,
            content_type="application/pdf",
            metadata={"processing_applied": "ocrmypdf_rotation", "original_filename": filename},
        )

        preprocessing_result = {
            "processing_time": processing_response.metadata.processing_time,
            "ocr_applied": False,
            "processed_s3_url": ocr_url,
            "rotation_ran": processing_response.metadata.rotation_ran,
            "error": processing_response.metadata.error,
        }
        combined_result = {
            "document_id": str(document_id),
            "analysis_result": analysis_result,
            "preprocessing_result": preprocessing_result,
        }

        # The layout job writes the same JSON column concurrently; both go through the row lock.
        def apply(metadata: DocumentProcessingMetadata) -> None:
            metadata.update_analysis_results(analysis_result)
            metadata.update_preprocessing_results(preprocessing_result)

        async with AsyncSessionLocal() as db:
            # The viewer shows `documents.url`, and the layout bboxes refer to `1.pdf`.
            if await update_processing_metadata(db, document_id, apply, url=ocr_url) is None:
                _LOGGER.info(f"Document {document_id} was deleted before its analysis could store")
                return {"document_id": str(document_id), "skipped": "document deleted"}

        # Read by the scheduler branch that will enqueue an OCR job once an engine exists.
        current_job.meta["pages_needing_ocr"] = triage.pages_needing_ocr
        current_job.meta["analysis_complete"] = True
        current_job.meta["preprocessing_complete"] = True
        current_job.save_meta()

        return combined_result

    except Exception as e:
        _LOGGER.error(f"Error in analysis_and_preprocess_job for document {document_id}: {e}")
        current_job.meta["error"] = str(e)
        current_job.save_meta()
        await _publish_source_as_ocr_pdf(document_id, workspace_name, s3_url, current_job.meta.get("workflow_id"))
        raise


async def _original_pdf_key(
    storage: files.ObjectStorage, workspace_name: str, document_id: UUID, s3_url: str | None
) -> str:
    """Key of file 1 as uploaded; raises when it is missing or not a PDF, the only type processed.

    A document created from a proxy URL rather than an upload gets that object copied in as file 1,
    so `documents.url`, `1.pdf` and the layout bboxes still describe the same pages.
    """
    first = (await files.list_document_files(storage, workspace_name, document_id)).get(1)
    if first is None and s3_url:
        try:
            url_workspace, url_key = files.split_document_url(s3_url)
        except ValueError:
            url_workspace = url_key = None
        if url_key is not None:
            data = await files.read_object(storage, url_workspace, url_key)
            extension, content_type = files.sniff_file_type(data, url_key.rsplit("/", 1)[-1])
            key = files.get_original_s3_object_path(document_id, extension)
            await files.put_object(storage, workspace_name, key, data, content_type=content_type)
            first = files.DocumentFile(index=1, original_key=key, extension=extension)
    if first is None:
        raise FileNotFoundError(
            f"Document {document_id} has no uploaded file 1 under {files.document_prefix(document_id)}"
            f" and its URL {s3_url!r} is not an object in this server's storage"
        )
    if not first.is_pdf:
        raise ValueError(f"Document {document_id} file 1 is a .{first.extension} upload; only PDFs are processed")
    return first.original_key


async def _publish_source_as_ocr_pdf(
    document_id: UUID, workspace_name: str, s3_url: str | None, workflow_id: str | None
) -> None:
    """Keep `1.pdf` and `documents.url` describing the same pages after analysis fails.

    If `documents.url` already points at `1.pdf`, an earlier run committed it and it is left alone.
    Otherwise the viewer shows the unrotated original, so `1.pdf` becomes a copy of it, which also
    replaces a rotated `1.pdf` this run wrote but never committed. A non-PDF upload gets no `1.pdf`.
    """
    try:
        storage = await files.get_storage()
        ocr_key = files.get_ocr_pdf_s3_object_path(document_id)
        async with AsyncSessionLocal() as db:
            if await writer_skip_reason(db, document_id, workflow_id) is not None:
                return
            url = await db.scalar(select(Document.url).where(Document.id == document_id))
        if url == files.get_proxy_document_url(workspace_name, ocr_key):
            return
        original = await _original_pdf_key(storage, workspace_name, document_id, s3_url)
        source = await files.read_object(storage, workspace_name, original)
        await files.put_object(
            storage,
            workspace_name,
            ocr_key,
            source,
            content_type="application/pdf",
            metadata={"processing_applied": "none"},
        )
        _LOGGER.warning(f"Analysis failed for document {document_id}; published 1_orig.pdf as 1.pdf")
    except Exception as error:
        _LOGGER.error(f"Could not publish a fallback 1.pdf for document {document_id}: {error}")
