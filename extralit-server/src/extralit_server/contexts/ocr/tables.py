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
Table processing context for PDF documents using existing PyMuPDF workflow.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import OCR_QUEUE
from extralit_server.models.database import Document

_LOGGER = logging.getLogger(__name__)


async def prepare_table_extraction_job(
    db: AsyncSession, document_id: UUID, s3_url: str, filename: str, workspace_name: str, workflow_id: str
) -> dict:
    """
    Prepare table extraction job data using existing PyMuPDF workflow.

    Fetches margins from stored document metadata (from analysis_and_preprocess_job)
    and passes them to the existing pymupdf_to_markdown_job in extralit-hf-space.

    Args:
        db: Database session
        document_id: UUID of document to process
        s3_url: S3 URL of the PDF file
        filename: Original filename
        workspace_name: Workspace name
        workflow_id: Workflow ID for tracking

    Returns:
        Job data prepared for OCR queue
    """
    # Fetch stored analysis metadata from document
    document = await db.get(Document, document_id)
    analysis_metadata = {}

    if document and document.metadata_:
        # Extract analysis metadata that contains margin analysis
        stored_metadata = document.metadata_
        analysis_metadata = stored_metadata.get("analysis_metadata", {})
        _LOGGER.info(f"Retrieved analysis metadata for document {document_id} with margin data")
    else:
        _LOGGER.warning(f"No stored analysis metadata found for document {document_id}")

    return OCR_QUEUE.prepare_data(
        "extralit_ocr.jobs.pymupdf_to_markdown_job",
        (document_id, s3_url, filename, analysis_metadata, workspace_name),
        timeout=900,
        job_id=f"table_extraction_{document_id}",
        meta={
            "document_id": str(document_id),
            "workflow_step": "table_extraction",
            "workflow_id": workflow_id,
        },
    )
