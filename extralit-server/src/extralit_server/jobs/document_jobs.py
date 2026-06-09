"""Document upload job functions."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata
from extralit_server.contexts import files
from extralit_server.contexts.document.analysis import PDFOCRLayerDetector
from extralit_server.contexts.document.margin import PDFAnalyzer
from extralit_server.contexts.document.preprocessing import PDFPreprocessingSettings, PDFPreprocessor
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import DEFAULT_QUEUE, REDIS_CONNECTION
from extralit_server.models.database import Document

_LOGGER = logging.getLogger(__name__)


@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=600, retry=Retry(max=3, interval=[10, 30, 60]))
async def analysis_and_preprocess_job(
    document_id: UUID, s3_url: str, reference: str, workspace_name: str
) -> dict[str, Any]:
    """
    Analyze PDF structure and content, then preprocess using existing modules.

    This job combines PDFOCRLayerDetector, PDFAnalyzer, and PDFPreprocessor to:
    1. Analyze original PDF structure and content
    2. Preprocess PDF using OCRmyPDF for page rotation (overwrites same S3 path)
    3. Store combined results in documents.metadata_ using DocumentProcessingMetadata schema

    Args:
        document_id: UUID of the document to process
        s3_url: S3 URL of the PDF file
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
        s3_client = await files.get_s3_client()
        pdf_data = await files.download_file_content(s3_client, s3_url)
        filename = s3_url.split("/")[-1]

        # Step 1: Analyze original PDF structure and content
        ocr_detector = PDFOCRLayerDetector()
        has_ocr_text_layer = ocr_detector.has_ocr_text_layer(pdf_data)
        ocr_quality = ocr_detector.analyze_character_quality(pdf_data)

        pdf_analyzer = PDFAnalyzer()
        layout_analysis, thumbnail_data = pdf_analyzer.analyze_pdf_layout(pdf_data, filename)

        analysis_result = {
            "document_id": str(document_id),
            "has_ocr_text_layer": has_ocr_text_layer,
            "ocr_quality_score": ocr_quality.get("ocr_quality_score", 0.0),
            "layout_analysis": layout_analysis,
            "needs_ocr": not has_ocr_text_layer or ocr_quality.get("ocr_quality_score", 0.0) < 0.7,
            "analysis_metadata": {
                "total_chars": ocr_quality.get("total_chars", 0),
                "ocr_artifacts": ocr_quality.get("ocr_artifacts", 0),
                "suspicious_patterns": ocr_quality.get("suspicious_patterns", 0),
                "ocr_quality_score": ocr_quality.get("ocr_quality_score", 0.0),
            },
        }

        # Step 2: Preprocess PDF (OCRmyPDF for page rotation, overwrites same S3 path)
        settings = PDFPreprocessingSettings(enable_analysis=False)  # Analysis already done
        preprocessor = PDFPreprocessor(settings)
        processing_response = preprocessor.preprocess(pdf_data, filename)

        # Step 2.5: Prepare concurrent file uploads
        # OCRmyPDF overwrites the same S3 object path, so we upload back to same location
        object_path = s3_url.replace(f"/api/v1/file/{workspace_name}/", "")

        upload_tasks = [
            files.put_object(
                s3_client,
                workspace_name,
                object_path,
                processing_response.processed_data,
                content_type="application/pdf",
                metadata={"processing_applied": "ocrmypdf_rotation", "original_filename": filename},
            )
        ]

        # Step 3: Add thumbnail upload task if thumbnail data exists
        analysis_result["thumbnail_generated"] = False
        if thumbnail_data is not None:
            thumbnail_object_path = files.get_thumbnail_s3_object_path(document_id)
            upload_tasks.append(
                files.put_object(
                    s3_client,
                    workspace_name,
                    thumbnail_object_path,
                    thumbnail_data,
                    content_type="image/png",
                    metadata={"original_filename": filename},
                )
            )

        # Execute uploads concurrently
        try:
            await asyncio.gather(*upload_tasks)
            _LOGGER.info(f"Successfully uploaded processed PDF for document {document_id}")
            if thumbnail_data is not None:
                _LOGGER.info(f"Generated and stored thumbnail for document {document_id}")
                analysis_result["thumbnail_generated"] = True
        except Exception as e:
            _LOGGER.warning(f"Failed to upload files for document {document_id}: {e}")
            if thumbnail_data is not None:
                analysis_result["thumbnail_generated"] = False
            # Re-raise the exception as this is a critical failure
            raise

        if thumbnail_data is None:
            _LOGGER.warning(f"No thumbnail data available for document {document_id}")

        # Combine results
        combined_result = {
            "document_id": str(document_id),
            "analysis_result": analysis_result,
            "preprocessing_result": {
                "processing_time": processing_response.metadata.processing_time,
                "ocr_applied": getattr(processing_response.metadata, "ocr_applied", False),
                "preprocessing_metadata": processing_response.metadata.model_dump(),
            },
        }

        # Store combined results in document.metadata_ using async database operations
        async with AsyncSessionLocal() as db:
            document = await db.get(Document, document_id)
            if document:
                # Initialize or update document metadata
                if document.metadata_ is None:
                    document.metadata_ = DocumentProcessingMetadata(
                        workflow_started_at=datetime.now(timezone.utc)
                    ).model_dump()

                metadata = DocumentProcessingMetadata(**document.metadata_)
                metadata.update_analysis_results(analysis_result)
                metadata.update_preprocessing_results(combined_result["preprocessing_result"])
                document.metadata_ = metadata.model_dump()
                await db.commit()

        # Store results for dependent jobs
        current_job.meta["needs_ocr"] = analysis_result["needs_ocr"]
        current_job.meta["analysis_complete"] = True
        current_job.meta["preprocessing_complete"] = True
        current_job.save_meta()

        return combined_result

    except Exception as e:
        _LOGGER.error(f"Error in analysis_and_preprocess_job for document {document_id}: {e}")
        current_job.meta["error"] = str(e)
        current_job.save_meta()
        raise
