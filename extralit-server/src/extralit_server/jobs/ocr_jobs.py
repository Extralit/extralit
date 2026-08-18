"""Document layout extraction jobs."""

import logging
from collections.abc import Sequence
from typing import Any, Optional
from uuid import UUID

from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.api.schemas.v1.document.metadata import LayoutMetadata
from extralit_server.contexts import files
from extralit_server.contexts.document.metadata import update_processing_metadata
from extralit_server.contexts.ocr import storage
from extralit_server.contexts.ocr.layout_store import LayoutStore
from extralit_server.contexts.ocr.parsers import default_parser_name, get_parser
from extralit_server.contexts.ocr.parsers.pdf_inspector import classify
from extralit_server.contexts.workflows import writer_skip_reason
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import OCR_QUEUE, REDIS_CONNECTION

_LOGGER = logging.getLogger(__name__)


def route_parser(pdf_bytes: bytes) -> tuple[str, dict[str, Any]]:
    """Pick a parser and record what classification saw.

    `pages_needing_ocr` is surfaced rather than acted on, so scanned pages show up as an
    explicit gap instead of silently producing an empty layout.
    """
    try:
        classification = classify(pdf_bytes)
    except Exception as e:
        _LOGGER.warning(f"PDF classification failed, falling back to the default parser: {e}")
        classification = {"pages_needing_ocr": [], "page_count": 0, "pdf_type": "unknown"}
    return default_parser_name(), classification


@job(
    queue=OCR_QUEUE,
    connection=REDIS_CONNECTION,
    timeout=1800,
    result_ttl=3600,
    retry=Retry(max=2, interval=[30, 60]),
)
async def async_document_layout_job(
    document_id: UUID,
    s3_url: str,
    workspace_name: str,
    parser: Optional[str] = None,
    pages: Optional[Sequence[int]] = None,
) -> dict[str, Any]:
    """Extract document layout into a `DoclingDocument` and persist it.

    Args:
        document_id: UUID of the document to process
        s3_url: proxy URL of the PDF, as stored on the document
        workspace_name: workspace bucket the artifacts are written to
        parser: layout parser name; None routes automatically
        pages: 1-indexed page allowlist; None processes every page

    Returns:
        Object paths and counts. Never the document itself — it does not belong in a job result.
    """
    current_job = get_current_job()
    if current_job is not None:
        current_job.meta.update(
            {
                "document_id": str(document_id),
                "workspace_name": workspace_name,
                "workflow_step": "document_layout",
            }
        )
        current_job.save_meta()

    try:
        # Shared client — do not enter it as a context manager, that would close it for everyone.
        s3_client = await files.get_s3_client()
        pdf_bytes = await files.download_file_content(s3_client, s3_url)

        routed, classification = route_parser(pdf_bytes)
        parser_name = parser or routed
        _LOGGER.info(f"Extracting layout for document {document_id} with parser {parser_name}")

        doc = get_parser(parser_name)(
            pdf_bytes,
            name=str(document_id),
            pages=pages,
            filename=s3_url.split("/")[-1],
        )

        # Ordering closes the delete-vs-running-job race: nothing may write rows for a document
        # whose delete already ran, and the workspace lock is held across the check and the write.
        workflow_id = (current_job.meta or {}).get("workflow_id") if current_job is not None else None
        store = LayoutStore.for_workspace(workspace_name)
        async with store.locked():
            async with AsyncSessionLocal() as db:
                skip = await writer_skip_reason(db, document_id, workflow_id)
            if skip is not None:
                _LOGGER.info(f"Layout for document {document_id} was not stored: {skip}")
                return {"document_id": str(document_id), "parser": parser_name, "skipped": skip}

            paths = await storage.store_layout(s3_client, workspace_name, document_id, doc, store=store)

        layout = LayoutMetadata(
            **paths,
            parser=parser_name,
            docling_version=doc.version,
            num_items=sum(1 for _ in doc.iterate_items(with_groups=False)),
            num_pages=len(doc.pages),
            pages_needing_ocr=classification.get("pages_needing_ocr", []),
        )

        # Outside the workspace lock: the row lock only serializes writers of this JSON column.
        async with AsyncSessionLocal() as db:
            await update_processing_metadata(db, document_id, lambda m: setattr(m, "layout_metadata", layout))

        result = {
            "document_id": str(document_id),
            "parser": parser_name,
            **layout.model_dump(),
        }

        if current_job is not None:
            current_job.meta["layout_complete"] = True
            current_job.save_meta()

        _LOGGER.info(f"Layout extraction complete for {document_id}: {layout.num_items} items")
        return result

    except Exception as e:
        _LOGGER.error(f"Error in layout extraction for document {document_id}: {e}", exc_info=True)
        if current_job is not None:
            current_job.meta["error"] = str(e)
            current_job.save_meta()
        raise
