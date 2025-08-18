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


import logging
from typing import Any
from uuid import UUID, uuid4

from extralit_server.contexts.ocr.rq_client import enqueue_pdf_extraction
from extralit_server.database import SyncSessionLocal
from extralit_server.jobs.document_jobs import analysis_and_preprocess_job
from extralit_server.jobs.queues import DEFAULT_QUEUE
from extralit_server.models.database import DocumentWorkflow

_LOGGER = logging.getLogger(__name__)


def start_pdf_workflow(document_id: UUID, s3_url: str, reference: str, workspace_name: str) -> dict[str, Any]:
    """
    Start PDF processing workflow by orchestrating job dependencies.

    Creates DocumentWorkflow record and manages entire job chain using RQ's depends_on parameter.
    Handles conditional OCR logic in orchestrator, not in individual jobs.

    Args:
        document_id: UUID of the document to process
        s3_url: S3 URL of the PDF file
        reference: Reference key for tracking
        workspace_id: UUID of the workspace

    Returns:
        Dictionary containing workflow_id and job_ids for tracking
    """

    try:
        # Step 1: Create DocumentWorkflow record for tracking using sync database operations
        with SyncSessionLocal() as db:
            workflow = DocumentWorkflow(
                id=uuid4(), document_id=document_id, workflow_type="pdf_processing", status="running", job_ids={}
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)

        # Step 2: Enqueue analysis and preprocessing job
        analysis_job = DEFAULT_QUEUE.enqueue(
            analysis_and_preprocess_job, document_id, s3_url, reference, workspace_name, job_timeout=600
        )

        pymupdf_job_id = enqueue_pdf_extraction(
            pdf_bytes=None,  # Will be downloaded by the job
            filename=s3_url.split("/")[-1],
            analysis_metadata=None,  # Will get from analysis_job result
            extraction_config=None,
            job_timeout=900,
        )

        # Step 3: Store job IDs in workflow record
        job_ids = {
            "analysis_and_preprocess": analysis_job.id,
            "pymupdf_extraction": pymupdf_job_id,
            "workflow_id": str(workflow.id),
            # 'table_extraction': table_extraction_job.id  # Future implementation
        }

        # Step 4: Update workflow with job IDs using sync database operations
        with SyncSessionLocal() as db:
            workflow.job_ids = job_ids
            db.add(workflow)
            db.commit()

        _LOGGER.info(
            f"Started PDF workflow {workflow.id} for document {document_id} with analysis job {analysis_job.id}"
        )

        return {
            "workflow_id": str(workflow.id),
            "job_ids": job_ids,
            "document_id": str(document_id),
            "reference": reference,
        }

    except Exception as e:
        _LOGGER.error(f"Error starting PDF workflow for document {document_id}: {e}")
        raise
