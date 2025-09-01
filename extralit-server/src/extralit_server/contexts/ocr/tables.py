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

from extralit_server.jobs.queues import OCR_QUEUE

_LOGGER = logging.getLogger(__name__)


def prepare_table_extraction_job(
    document_id: UUID, s3_url: str, filename: str, workspace_name: str, workflow_id: str
) -> dict:
    """
    Prepare table extraction job data using existing PyMuPDF workflow.

    Uses the same pattern as workflows/documents.py for consistency.
    The existing pymupdf_to_markdown_job will fetch margins from stored analysis.

    Args:
        document_id: UUID of document to process
        s3_url: S3 URL of the PDF file
        filename: Original filename
        workspace_name: Workspace name
        workflow_id: Workflow ID for tracking

    Returns:
        Job data prepared for OCR queue
    """
    return OCR_QUEUE.prepare_data(
        "extralit_ocr.jobs.pymupdf_to_markdown_job",
        (document_id, s3_url, filename, {}, workspace_name),
        timeout=900,
        job_id=f"table_extraction_{document_id}",
        meta={
            "document_id": str(document_id),
            "workflow_step": "table_extraction",
            "workflow_id": workflow_id,
        },
    )
