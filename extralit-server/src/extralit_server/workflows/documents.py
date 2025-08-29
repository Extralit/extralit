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
from uuid import UUID, uuid4

from rq.group import Group

from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.document_jobs import analysis_and_preprocess_job
from extralit_server.jobs.queues import DEFAULT_QUEUE, OCR_QUEUE, REDIS_CONNECTION
from extralit_server.models.database import DocumentWorkflow

_LOGGER = logging.getLogger(__name__)


async def create_document_workflow(
    document_id: UUID, s3_url: str, reference: str, workspace_name: str, workspace_id: UUID
) -> Group:
    """
    Start PDF processing workflow using RQ Groups for job tracking.

    Creates DocumentWorkflow record and manages entire job chain using RQ Groups.
    Handles conditional OCR logic in orchestrator, not in individual jobs.

    Args:
        document_id: UUID of the document to process
        s3_url: S3 URL of the PDF file
        reference: Reference key for tracking
        workspace_name: Workspace name for job context
        workspace_id: UUID of the workspace

    Returns:
        Dictionary containing workflow_id and group_id for tracking
    """
    group_id = f"document_workflow_{document_id}_{uuid4().hex[:8]}"
    group = Group(REDIS_CONNECTION, name=group_id)

    # Step 3: Create DocumentWorkflow record for tracking
    async with AsyncSessionLocal() as db:
        workflow = DocumentWorkflow(
            id=uuid4(),
            document_id=document_id,
            workflow_type="pdf_processing",
            workspace_id=workspace_id,
            reference=reference,
            group_id=group_id,
            status="running",
        )
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

    # Step 4: Prepare jobs using Queue.prepare_data()
    analysis_job_data = DEFAULT_QUEUE.prepare_data(
        analysis_and_preprocess_job,
        (document_id, s3_url, reference, workspace_name),
        timeout=600,
        job_id=f"analysis_preprocess_{document_id}",
        meta={
            "document_id": str(document_id),
            "reference": reference,
            "workflow_step": "analysis_and_preprocess",
            "workflow_id": str(workflow.id),
        },
    )

    text_extraction_job_data = OCR_QUEUE.prepare_data(
        "extralit_ocr.jobs.pymupdf_to_markdown_job",
        (document_id, s3_url, s3_url.split("/")[-1], {}, workspace_name),
        timeout=900,
        job_id=f"text_extraction_{document_id}",
        meta={
            "document_id": str(document_id),
            "reference": reference,
            "workflow_step": "text_extraction",
            "workflow_id": str(workflow.id),
        },
    )

    group.enqueue_many(queue=DEFAULT_QUEUE, job_datas=[analysis_job_data])
    group.enqueue_many(queue=OCR_QUEUE, job_datas=[text_extraction_job_data])

    # Step 6: Future table extraction job (conditional based on analysis results)
    # This will be added when table extraction is implemented
    # table_extraction_job_data = OCR_QUEUE.prepare_data(
    #     "extralit_ocr.jobs.table_extraction_job",
    #     (document_id, s3_url),
    #     depends_on=[jobs[0]],  # depends on analysis job
    #     group=group,
    #     job_id=f"table_extraction_{document_id}",
    #     meta={
    #         "document_id": str(document_id),
    #         "reference": reference,
    #         "workflow_step": "table_extraction",
    #         "workflow_id": str(workflow.id)
    #     }
    # )

    _LOGGER.info(f"Started PDF workflow {workflow.id} for document {document_id} with group {group_id}")

    return group
