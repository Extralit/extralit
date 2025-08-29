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

"""
RQ jobs for PDF text extraction using PyMuPDF with document metadata integration.

This module provides the job functions called by extralit-server workflows.
It imports existing metadata classes and uses margin information from document metadata.
"""

import logging
import os
from typing import Any
from uuid import UUID

import requests
from rq import get_current_job

# Import existing metadata classes from extralit-server
try:
    from extralit_server.api.schemas.v1.document.metadata import LayoutAnalysisMetadata
    from extralit_server.database import SyncSessionLocal
    from extralit_server.models.database import Document
except ImportError:
    # Fallback for testing/development
    LayoutAnalysisMetadata = None
    SyncSessionLocal = None
    Document = None

LOGGER = logging.getLogger(__name__)


def get_document_margins(document_id: UUID) -> tuple[int, int, int, int]:
    """
    Retrieve margin information from document metadata in database.

    Args:
        document_id: UUID of the document

    Returns:
        Tuple of (left, top, right, bottom) margins in PDF points
    """
    default_margins = (0, 50, 0, 30)  # Default margins if no metadata available

    if not SyncSessionLocal or not Document:
        LOGGER.info(f"Database classes not available, using default margins for {document_id}")
        return default_margins

    try:
        with SyncSessionLocal() as db:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document or not document.metadata_:
                LOGGER.info(f"No metadata found for document {document_id}, using default margins")
                return default_margins

            # Extract margin analysis from document metadata
            analysis_metadata = document.metadata_.get("analysis_metadata", {})
            layout_analysis = analysis_metadata.get("layout_analysis", {})
            margin_analysis = layout_analysis.get("margin_analysis", {})

            if margin_analysis and "estimated_margins" in margin_analysis:
                estimated_margins = margin_analysis["estimated_margins"]

                # Convert from pixel-based margins to PDF points
                left = estimated_margins.get("left_px", 0)
                top = estimated_margins.get("top_px", 50)
                right = estimated_margins.get("right_px", 0)
                bottom = estimated_margins.get("bottom_px", 30)

                margins = (left, top, right, bottom)
                LOGGER.info(f"Using document-specific margins for {document_id}: {margins}")
                return margins

    except Exception as e:
        LOGGER.warning(f"Error retrieving margins for document {document_id}: {e}")

    LOGGER.info(f"Using default margins for document {document_id}: {default_margins}")
    return default_margins


def pymupdf_to_markdown_job(
    document_id: UUID,
    s3_url: str,
    filename: str,
    job_metadata: dict[str, Any],
    workspace_name: str,
) -> dict[str, Any]:
    """
    RQ job to extract markdown from PDF using PyMuPDF with document-specific margins.

    This function integrates with extralit-hf-space service to perform the actual
    PyMuPDF extraction while using margin information from document metadata.

    Args:
        document_id: UUID of the document being processed
        s3_url: S3 URL of the PDF file
        filename: Original filename
        job_metadata: Additional job metadata
        workspace_name: Name of the workspace

    Returns:
        Dictionary containing extraction results and metadata
    """
    job = get_current_job()
    LOGGER.info(f"Starting PyMuPDF extraction for document {document_id}")

    try:
        # Call extralit-hf-space service with document ID (service fetches margins from DB)
        service_url = os.getenv("EXTRALIT_HF_SPACE_URL", "http://localhost:8000")

        # Download PDF from S3
        pdf_response = requests.get(s3_url)
        pdf_response.raise_for_status()

        # Call extraction service with document ID (service will fetch margins from DB)
        files = {"pdf": (filename, pdf_response.content, "application/pdf")}

        extract_response = requests.post(f"{service_url}/extract_with_document/{document_id}", files=files)
        extract_response.raise_for_status()
        extraction_result = extract_response.json()

        result = {
            "status": "success",
            "document_id": str(document_id),
            "filename": filename,
            "margins_used": extraction_result.get("margins_used"),
            "extraction_method": "pymupdf4llm",
            "job_id": job.id if job else None,
            "workspace_name": workspace_name,
            "markdown": extraction_result.get("markdown"),
            "metadata": extraction_result.get("metadata"),
        }

        LOGGER.info(f"PyMuPDF extraction completed for document {document_id}")
        return result

    except Exception as e:
        LOGGER.error(f"PyMuPDF extraction failed for document {document_id}: {e}")
        return {
            "status": "error",
            "document_id": str(document_id),
            "error": str(e),
            "job_id": job.id if job else None,
        }
