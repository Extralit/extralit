import logging
from uuid import UUID, uuid4

from rq import Retry
from rq.group import Group
from rq.job import Dependency

from extralit_server.contexts.ocr.parsers import default_parser_name
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.document_jobs import analysis_and_preprocess_job
from extralit_server.jobs.ocr_jobs import async_document_layout_job
from extralit_server.jobs.queues import DEFAULT_QUEUE, OCR_QUEUE, REDIS_CONNECTION
from extralit_server.models.database import DocumentWorkflow

_LOGGER = logging.getLogger(__name__)

# RQ's 500s default drops finished jobs from the group, decaying derived workflow status to pending.
JOB_RESULT_TTL = 24 * 3600


async def create_document_workflow(
    document_id: UUID,
    s3_url: str,
    reference: str,
    workspace_name: str,
    workspace_id: UUID,
    layout_parser: str | None = None,
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
        layout_parser: Layout parser to run; None uses the default parser

    Returns:
        Dictionary containing workflow_id and group_id for tracking
    """
    run_suffix = uuid4().hex[:8]
    group_id = f"document_workflow_{document_id}_{run_suffix}"
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

    # Step 4: Prepare jobs using Queue.prepare_data(); the @job decorator kwargs are inert here.
    analysis_job_data = DEFAULT_QUEUE.prepare_data(
        analysis_and_preprocess_job,
        (document_id, s3_url, reference, workspace_name),
        timeout=600,
        job_id=f"analysis_preprocess_{document_id}_{run_suffix}",
        retry=Retry(max=3, interval=[10, 30, 60]),
        result_ttl=JOB_RESULT_TTL,
        meta={
            "document_id": str(document_id),
            "reference": reference,
            "workflow_step": "analysis_and_preprocess",
            "workflow_id": str(workflow.id),
        },
    )

    analysis_jobs = group.enqueue_many(queue=DEFAULT_QUEUE, job_datas=[analysis_job_data])

    # Preprocessing rewrites the PDF at the same S3 key as its last step and writes the margins
    # every downstream reader needs, so dependents wait on it. Rotation is best effort, hence
    # allow_failure: otherwise a failed triage strands them in DEFERRED forever.
    on_analysis = Dependency(jobs=[analysis_jobs[0]], allow_failure=True) if analysis_jobs else None

    text_extraction_job_data = OCR_QUEUE.prepare_data(
        "extralit_ocr.jobs.pymupdf_to_markdown_job",
        (document_id, s3_url, s3_url.split("/")[-1], {}, workspace_name),
        timeout=900,
        job_id=f"text_extraction_{document_id}_{run_suffix}",
        depends_on=on_analysis,
        retry=Retry(max=2, interval=[30, 60]),
        result_ttl=JOB_RESULT_TTL,
        meta={
            "document_id": str(document_id),
            "reference": reference,
            "workflow_step": "text_extraction",
            "workflow_id": str(workflow.id),
        },
    )

    group.enqueue_many(queue=OCR_QUEUE, job_datas=[text_extraction_job_data])

    # Deferred OCR branch: once an OCR engine is configured, an `ocr_job` is enqueued here when
    # triage reports pages needing OCR, and layout depends on it instead of on triage. pdf-inspector
    # classifies those pages but bundles no engine, so today they stay an explicitly surfaced gap.
    layout_job_data = OCR_QUEUE.prepare_data(
        async_document_layout_job,
        (document_id, s3_url, workspace_name, layout_parser or default_parser_name()),
        timeout=1800,
        job_id=f"document_layout_{document_id}_{run_suffix}",
        depends_on=on_analysis,
        retry=Retry(max=2, interval=[30, 60]),
        result_ttl=JOB_RESULT_TTL,
        meta={
            "document_id": str(document_id),
            "reference": reference,
            "workflow_step": "document_layout",
            "workflow_id": str(workflow.id),
        },
    )
    group.enqueue_many(queue=OCR_QUEUE, job_datas=[layout_job_data])

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
