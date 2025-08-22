# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Document upload job functions."""

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata
from extralit_server.api.schemas.v1.documents import DocumentCreate
from extralit_server.contexts import files, imports
from extralit_server.contexts.document import preprocessing
from extralit_server.contexts.document.analysis import PDFOCRLayerDetector
from extralit_server.contexts.document.margin import PDFAnalyzer
from extralit_server.contexts.document.preprocessing import PDFPreprocessingSettings, PDFPreprocessor
from extralit_server.database import AsyncSessionLocal, SyncSessionLocal
from extralit_server.jobs.queues import DEFAULT_QUEUE, JOB_TIMEOUT_DISABLED, REDIS_CONNECTION
from extralit_server.models.database import Document

_LOGGER = logging.getLogger(__name__)


@job(
    queue=DEFAULT_QUEUE,
    connection=REDIS_CONNECTION,
    timeout=JOB_TIMEOUT_DISABLED,
    retry=Retry(max=3, interval=[10, 30, 60]),
)
async def upload_and_preprocess_documents_job(  # Deprecated
    reference: str,
    reference_data: dict[str, Any],
    file_data_list: list[tuple[str, bytes]],  # List of (filename, file_data) tuples
    user_id: UUID,
) -> dict[str, Any]:
    """
    Asynchronous job to upload multiple documents for a single reference.

    This job processes multiple files for a single reference in one job,
    creating separate document records for each file while maintaining
    the reference relationship. It reuses existing document upload logic
    and provides detailed error reporting for each file.

    Args:
        reference: BibTeX reference key for tracking
        document_data: Dictionary containing DocumentCreate data (shared metadata)
        file_data_list: List of (filename, file_data) tuples for multiple files
        user_id: UUID of the user creating the documents

    Returns:
        Dictionary with upload results including document_ids or errors for each file
    """
    temp_files = []
    results = {
        "reference": reference,
        "success": True,
        "files": {},  # filename -> result mapping
        "total_files": len(file_data_list),
        "successful_files": 0,
        "failed_files": 0,
        "errors": [],
    }

    try:
        document_create = DocumentCreate.model_validate(reference_data)

        async with AsyncSessionLocal() as db:
            from extralit_server.models import Workspace

            workspace = await Workspace.get(db, document_create.workspace_id)
            if not workspace:
                error_msg = f"Workspace with id `{document_create.workspace_id}` not found"
                _LOGGER.error(error_msg)
                results["success"] = False
                results["errors"].append(error_msg)
                return results

            client = files.get_minio_client()
            if client is None:
                error_msg = "Failed to get minio client"
                _LOGGER.error(error_msg)
                results["success"] = False
                results["errors"].append(error_msg)
                return results

            # Process each file for this reference
            for filename, file_data in file_data_list:
                file_result = {
                    "filename": filename,
                    "success": False,
                    "document_id": None,
                    "status": None,
                    "error": None,
                }

                try:
                    file_metadata: dict[str, Any] = {
                        "collections": (document_create.metadata or {}).get("collections", [])
                    }

                    file_document_create = DocumentCreate(
                        id=uuid4(),
                        reference=document_create.reference,
                        pmid=document_create.pmid,
                        doi=document_create.doi,
                        url=None,  # Will be set after S3 upload
                        file_name=filename,
                        workspace_id=document_create.workspace_id,
                        metadata=file_metadata,
                    )

                    existing_documents = await imports.find_existing_documents(
                        db=db,
                        workspace_id=file_document_create.workspace_id,
                        document_id=file_document_create.id,
                        file_name=file_document_create.file_name,
                        limit=1,
                    )
                    if existing_documents:
                        existing_document_id = existing_documents[0].id
                        _LOGGER.info(f"Document already exists for file {filename} with ID {existing_document_id}")
                        file_result.update(
                            {"success": True, "document_id": str(existing_document_id), "status": "existing"}
                        )
                        results["successful_files"] += 1
                        results["files"][filename] = file_result
                        continue

                    try:
                        # Preprocess PDF files with OCRmyPDF for rotation and OCR, plus layout analysis
                        preprocessing_result = preprocessing.preprocessor.preprocess(
                            file_data=file_data, filename=filename
                        )
                        processed_file_data = preprocessing_result.processed_data

                        # Store preprocessing metadata in file metadata
                        file_metadata.update(preprocessing_result.metadata.model_dump())

                        file_url = files.put_document_file(
                            client=client,
                            workspace_name=workspace.name,
                            document_id=file_document_create.id,  # type: ignore
                            file_data=processed_file_data,
                            filename=filename,
                        )

                        if file_url:
                            file_document_create.url = file_url
                    except Exception as e:
                        error_msg = f"Error uploading file `{filename}` to S3: {e!s}"
                        _LOGGER.error(error_msg)
                        file_result["error"] = error_msg
                        results["failed_files"] += 1
                        results["files"][filename] = file_result
                        continue

                    # Create document in database
                    try:
                        file_document_create.metadata = file_metadata
                        document = await imports.create_document(db, file_document_create)
                        _LOGGER.info(f"Document created successfully for file {filename} with ID {document.id}")
                        file_result.update({"success": True, "document_id": str(document.id), "status": "created"})
                        results["successful_files"] += 1
                    except Exception as e:
                        error_msg = f"Error creating document for file {filename} in database: {e!s}"
                        _LOGGER.error(error_msg)
                        file_result["error"] = error_msg
                        results["failed_files"] += 1

                except Exception as e:
                    error_msg = f"Error processing file {filename}: {e!s}"
                    _LOGGER.error(error_msg)
                    file_result["error"] = error_msg
                    results["failed_files"] += 1

                results["files"][filename] = file_result

            results["success"] = results["failed_files"] == 0

    except Exception as e:
        error_msg = f"Error uploading documents for reference {reference}: {e!s}"
        _LOGGER.error(error_msg)
        results["success"] = False
        results["errors"].append(str(e))

    finally:
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                _LOGGER.warning(f"Failed to cleanup temporary file {temp_file}: {e!s}")

    return results


@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=600, retry=Retry(max=3, interval=[10, 30, 60]))
def analysis_and_preprocess_job(document_id: UUID, s3_url: str, reference: str, workspace_name: str) -> dict[str, Any]:
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
    current_job.meta.update(
        {
            "document_id": str(document_id),
            "reference": reference,
            "workspace_name": str(workspace_name),
            "workflow_step": "analysis_and_preprocess",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    current_job.save_meta()

    try:
        # Download original PDF from storage
        client = files.get_minio_client()
        if client is None:
            raise Exception("Failed to get storage client")

        pdf_data = files.download_file_content(client, s3_url)
        filename = s3_url.split("/")[-1]

        # Step 1: Analyze original PDF structure and content
        ocr_detector = PDFOCRLayerDetector()
        has_ocr_text_layer = ocr_detector.has_ocr_text_layer(pdf_data)
        ocr_quality = ocr_detector.analyze_character_quality(pdf_data)

        pdf_analyzer = PDFAnalyzer()
        layout_analysis = pdf_analyzer.analyze_pdf_layout(pdf_data, filename)

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

        # OCRmyPDF overwrites the same S3 object path, so we upload back to same location
        object_path = s3_url.replace(f"/api/v1/file/{workspace_name}/", "")

        files.put_object(
            client,
            workspace_name,
            object_path,
            processing_response.processed_data,
            len(processing_response.processed_data),
            content_type="application/pdf",
            metadata={"processing_applied": "ocrmypdf_rotation", "original_filename": filename},
        )

        # Combine results
        combined_result = {
            "document_id": str(document_id),
            "analysis_result": analysis_result,
            "preprocessing_result": {
                "processing_time": processing_response.metadata.processing_time,
                "ocr_applied": getattr(processing_response.metadata, "ocr_applied", False),
                "preprocessing_metadata": processing_response.metadata.model_dump(),
            },
            "needs_ocr": analysis_result["needs_ocr"],
        }

        # Store combined results in document.metadata_ using sync database operations
        with SyncSessionLocal() as db:
            document = db.get(Document, document_id)
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
                db.commit()

        # Store results for dependent jobs
        current_job.meta["needs_ocr"] = analysis_result["needs_ocr"]
        current_job.meta["analysis_complete"] = True
        current_job.meta["preprocessing_complete"] = True
        current_job.meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        current_job.save_meta()

        return combined_result

    except Exception as e:
        _LOGGER.error(f"Error in analysis_and_preprocess_job for document {document_id}: {e}")
        current_job.meta["error"] = str(e)
        current_job.meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        current_job.save_meta()
        raise
