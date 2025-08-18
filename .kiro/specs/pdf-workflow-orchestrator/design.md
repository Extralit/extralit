# PDF Workflow Orchestrator Design

## Overview

The PDF Workflow Orchestrator refactors the existing document upload and processing pipeline to use RQ's native job chaining capabilities. Instead of a single monolithic job, the system splits processing into 6 chained jobs using RQ's built-in features without custom abstractions.

## Current vs New Architecture

### Current Flow (Single Job)
```
POST /documents/bulk → process_bulk_upload() → upload_and_preprocess_documents_job → (File upload + preprocessing + DB creation in one step)
```

### New Flow (Chained Jobs)
```
POST /documents/bulk → process_bulk_upload() → Upload files to S3 + Create DB records → analysis_job(document_id, s3_url) → preprocess_job(document_id, s3_url) → conditional_ocr_job (if needed) → text_extraction_job + table_extraction_job (parallel) → embedding_job
```

### Key Changes from Current Implementation

1. **File Upload Moved to API**: Files uploaded to S3 in `process_bulk_upload()` before job enqueueing
2. **Job Splitting**: `upload_and_preprocess_documents_job` split into separate chained jobs
3. **S3 URLs Instead of File Data**: Jobs receive document IDs and S3 URLs, not raw file bytes
4. **RQ Dependencies**: Use `depends_on` parameter for job chaining
5. **Job Metadata**: Track workflow progress using `job.meta`

## Integration with Existing Code

### Refactoring process_bulk_upload()

```python
# Current implementation in contexts/imports.py
async def process_bulk_upload(
    bulk_create: DocumentsBulkCreate,
    files: list[UploadFile],
    user_id: str,
) -> DocumentsBulkResponse:
    # ... validation logic ...

    # OLD: Enqueue single job with file data
    job = DEFAULT_QUEUE.enqueue(
        upload_and_preprocess_documents_job,
        reference=reference,
        reference_data=doc.document_create.model_dump(),
        file_data_list=file_data_list,  # Raw file bytes
        user_id=user_id,
    )

# NEW: Upload files first, then enqueue workflow
async def process_bulk_upload(
    bulk_create: DocumentsBulkCreate,
    files: list[UploadFile],
    user_id: str,
) -> DocumentsBulkResponse:
    # ... validation logic ...

    # NEW: Upload files to S3 immediately
    s3_urls = await upload_files_to_s3(file_data_list)

    # NEW: Create document records in database
    document = await create_document(db, doc.document_create)

    # NEW: Start workflow with document ID and S3 URLs
    workflow_jobs = start_pdf_workflow(
        document_id=document.id,
        reference=reference,
        s3_urls=s3_urls,
        workspace_id=document.workspace_id,
        user_id=user_id
    )

    return DocumentsBulkResponse(
        job_ids=workflow_jobs,  # Multiple job IDs instead of single
        total_documents=len(reference_to_doc),
        failed_validations=failed_validations
    )
```

### Splitting upload_and_preprocess_documents_job

```python
# Current monolithic job in jobs/document_jobs.py
def upload_and_preprocess_documents_job(
    reference: str,
    reference_data: dict,
    file_data_list: list[tuple[str, bytes]],
    user_id: str
):
    # Does everything: upload, DB creation, preprocessing
    pass

# NEW: Separate job functions with RQ chaining
from rq.decorators import job
from rq import get_current_job

@job(queue='default', timeout=300, result_ttl=3600)
def analysis_job(document_id: UUID, s3_url: str, reference: str, workspace_id: UUID) -> dict:
    """Analyze PDF structure and content."""
    current_job = get_current_job()
    current_job.meta.update({
        'document_id': str(document_id),
        'reference': reference,
        'workspace_id': str(workspace_id),
        'workflow_step': 'analysis',
        'started_at': datetime.utcnow().isoformat()
    })
    current_job.save_meta()

    # Download PDF from S3 and analyze
    analysis_result = perform_pdf_analysis(s3_url)

    # Conditionally enqueue OCR job based on analysis
    if analysis_result.get('needs_ocr'):
        ocr_job_instance = ocr_job.delay(document_id, s3_url, reference, workspace_id, analysis_result)
        current_job.meta['ocr_job_id'] = ocr_job_instance.id

    # Always enqueue text extraction
    text_job_instance = text_extraction_job.delay(document_id, s3_url, reference, workspace_id, analysis_result)
    current_job.meta['text_job_id'] = text_job_instance.id

    current_job.meta['completed_at'] = datetime.utcnow().isoformat()
    current_job.save_meta()
    return analysis_result

@job(queue='default', timeout=300, result_ttl=3600)
def preprocess_job(document_id: UUID, s3_url: str, reference: str, workspace_id: UUID) -> dict:
    """Preprocess PDF for downstream tasks."""
    current_job = get_current_job()
    current_job.meta.update({
        'document_id': str(document_id),
        'reference': reference,
        'workspace_id': str(workspace_id),
        'workflow_step': 'preprocess',
        'started_at': datetime.utcnow().isoformat()
    })
    current_job.save_meta()

    # Preprocessing logic
    preprocess_result = preprocess_pdf(s3_url)

    current_job.meta['completed_at'] = datetime.utcnow().isoformat()
    current_job.save_meta()
    return preprocess_result

@job(queue='gpu', timeout=600, result_ttl=3600)  # GPU queue for table extraction
def table_extraction_job(document_id: UUID, s3_url: str, reference: str, workspace_id: UUID,
                        analysis_result: dict, ocr_result: dict = None) -> dict:
    """Extract tables using GPU resources."""
    current_job = get_current_job()
    current_job.meta.update({
        'document_id': str(document_id),
        'reference': reference,
        'workspace_id': str(workspace_id),
        'workflow_step': 'table_extraction',
        'started_at': datetime.utcnow().isoformat()
    })
    current_job.save_meta()

    # Table extraction logic using GPU
    table_result = extract_tables_gpu(s3_url, analysis_result, ocr_result)

    current_job.meta['completed_at'] = datetime.utcnow().isoformat()
    current_job.save_meta()
    return table_result
```

## RQ Native Features Usage

### Job Dependencies and Chaining

```python
def start_pdf_workflow(document_id: UUID, s3_url: str, reference: str, workspace_id: UUID, user_id: UUID) -> dict:
    """Start complete PDF workflow using RQ native dependencies."""

    # Step 1 & 2: Parallel jobs (no dependencies)
    analysis_job_instance = analysis_job.delay(document_id, s3_url, reference, workspace_id)
    preprocess_job_instance = preprocess_job.delay(document_id, s3_url, reference, workspace_id)

    # Step 3: Text extraction depends on analysis
    text_job_instance = text_extraction_job.delay(
        document_id, s3_url, reference, workspace_id,
        depends_on=[analysis_job_instance]  # RQ native dependency
    )

    # Step 4: Table extraction depends on analysis (and OCR if it runs)
    table_job_instance = table_extraction_job.delay(
        document_id, s3_url, reference, workspace_id,
        depends_on=[analysis_job_instance]  # OCR job will be added dynamically if needed
    )

    # Step 5: Embedding depends on both text and table extraction
    embedding_job_instance = embedding_job.delay(
        document_id, reference, workspace_id,
        depends_on=[text_job_instance, table_job_instance]
    )

    return {
        'analysis_job_id': analysis_job_instance.id,
        'preprocess_job_id': preprocess_job_instance.id,
        'text_job_id': text_job_instance.id,
        'table_job_id': table_job_instance.id,
        'embedding_job_id': embedding_job_instance.id
    }
```

### Job Metadata for Tracking

```python
# Simple job metadata (no custom database tables needed)
job.meta = {
    'document_id': str(document_id),
    'reference': reference,
    'workspace_id': str(workspace_id),
    'workflow_step': 'analysis',  # analysis, preprocess, ocr, text_extraction, table_extraction, embedding
    'started_at': datetime.utcnow().isoformat(),
    'completed_at': None,  # Set when job completes
    'progress': 0,  # 0-100
    'child_job_ids': []  # Track jobs enqueued by this job
}
```

### Job Querying by Metadata

```python
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry

def get_jobs_for_document(document_id: UUID) -> list[dict]:
    """Find all jobs for a document by scanning RQ registries."""
    all_jobs = []

    # Scan all RQ job registries
    registries = [
        ('started', StartedJobRegistry(connection=REDIS_CONNECTION)),
        ('finished', FinishedJobRegistry(connection=REDIS_CONNECTION)),
        ('failed', FailedJobRegistry(connection=REDIS_CONNECTION))
    ]

    for status, registry in registries:
        for job_id in registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=REDIS_CONNECTION)
                if job.meta.get('document_id') == str(document_id):
                    job_info = {
                        'job_id': job.id,
                        'status': status,
                        'workflow_step': job.meta.get('workflow_step'),
                        'reference': job.meta.get('reference'),
                        'started_at': job.meta.get('started_at'),
                        'completed_at': job.meta.get('completed_at'),
                        'progress': job.meta.get('progress', 0),
                        'error': str(job.exc_info) if job.is_failed else None
                    }
                    all_jobs.append(job_info)
            except Exception:
                # Job might have expired
                continue

    return sorted(all_jobs, key=lambda x: x.get('started_at', ''))
```

## API Extensions

### Enhanced Jobs Endpoint

```python
# Extend existing jobs.py endpoint
@router.get("/jobs/", response_model=List[JobSchema])
async def get_jobs(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    document_id: Optional[UUID] = Query(None, description="Filter by document ID"),
    reference: Optional[str] = Query(None, description="Filter by reference"),
    workflow_step: Optional[str] = Query(None, description="Filter by workflow step"),
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Get jobs with workflow filtering."""

    if document_id:
        jobs_data = get_jobs_for_document(document_id)
    elif reference:
        jobs_data = get_jobs_by_reference(reference)
    else:
        jobs_data = get_recent_jobs(limit=100)

    # Apply filters
    if workflow_step:
        jobs_data = [j for j in jobs_data if j.get('workflow_step') == workflow_step]

    return jobs_data

@router.get("/documents/{document_id}/workflow-status")
async def get_document_workflow_status(
    document_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Get complete workflow status for a document."""

    jobs = get_jobs_for_document(document_id)

    # Calculate progress
    workflow_steps = ['analysis', 'preprocess', 'text_extraction', 'table_extraction', 'embedding']
    completed_steps = {j['workflow_step'] for j in jobs if j['status'] == 'finished'}
    progress = len(completed_steps) / len(workflow_steps)

    return {
        'document_id': document_id,
        'progress': progress,
        'status': 'completed' if progress == 1.0 else 'running',
        'jobs': jobs
    }
```

## Queue Configuration

```python
# Add to existing jobs/queues.py
from rq import Queue

# Existing queues
DEFAULT_QUEUE = Queue('default', connection=REDIS_CONNECTION)
HIGH_QUEUE = Queue('high', connection=REDIS_CONNECTION)

# NEW: GPU queue for table extraction
GPU_QUEUE = Queue('gpu', connection=REDIS_CONNECTION)

# Queue routing
WORKFLOW_QUEUES = {
    'analysis': DEFAULT_QUEUE,
    'preprocess': DEFAULT_QUEUE,
    'ocr': DEFAULT_QUEUE,
    'text_extraction': DEFAULT_QUEUE,
    'table_extraction': GPU_QUEUE,  # Route to GPU workers
    'embedding': DEFAULT_QUEUE
}
```

## CLI Commands (Using Typer)

```python
# Add to existing CLI using typer
import typer
from extralit_server.jobs.pdf_workflow import start_pdf_workflow, get_jobs_for_document

workflow_app = typer.Typer()

@workflow_app.command()
def start(
    document_id: str = typer.Option(..., help="Document UUID to process"),
    reference: str = typer.Option(None, help="Document reference"),
    workspace_id: str = typer.Option(..., help="Workspace UUID"),
    user_id: str = typer.Option(..., help="User UUID")
):
    """Start PDF processing workflow for a document."""
    try:
        # Get document and S3 URL from database
        doc = get_document_by_id(UUID(document_id))
        s3_url = get_document_s3_url(doc)

        job_ids = start_pdf_workflow(
            UUID(document_id),
            s3_url,
            reference or f"doc_{document_id[:8]}",
            UUID(workspace_id),
            UUID(user_id)
        )
        typer.echo(f"Started workflow jobs: {job_ids}")
    except Exception as e:
        typer.echo(f"Error starting workflow: {e}", err=True)

@workflow_app.command()
def status(
    document_id: str = typer.Option(None, help="Document UUID to check"),
    reference: str = typer.Option(None, help="Document reference to check")
):
    """Check workflow status."""
    try:
        if document_id:
            jobs = get_jobs_for_document(UUID(document_id))
        elif reference:
            jobs = get_jobs_by_reference(reference)
        else:
            typer.echo("Must specify either --document-id or --reference", err=True)
            return

        if not jobs:
            typer.echo("No jobs found")
            return

        typer.echo(f"Found {len(jobs)} jobs:")
        for job in jobs:
            typer.echo(f"  {job['workflow_step']}: {job['status']} ({job['job_id']})")
    except Exception as e:
        typer.echo(f"Error checking status: {e}", err=True)

# Add to main CLI app
app.add_typer(workflow_app, name="workflow")
```

## Implementation Strategy

### Phase 1: Minimal Viable Workflow
1. **Refactor Existing Job**: Split `upload_and_preprocess_documents_job` into `analysis_job` and `preprocess_job`
2. **Move File Upload**: Upload files to S3 in `process_bulk_upload()` before job enqueueing
3. **Add Job Metadata**: Track workflow progress using `job.meta`
4. **Test Basic Chaining**: Verify jobs can enqueue dependent jobs

### Phase 2: Complete Workflow
1. **Add Remaining Jobs**: Implement OCR, text extraction, table extraction, embedding jobs
2. **RQ Dependencies**: Use `depends_on` parameter for job chaining
3. **GPU Queue**: Route table extraction to GPU workers
4. **API Extensions**: Add document workflow status endpoint

### Phase 3: Management and Recovery
1. **CLI Commands**: Add workflow start/status commands using typer
2. **Error Handling**: Implement job restart for failed workflows
3. **Testing**: Add comprehensive tests for workflow execution
4. **Performance**: Optimize for multiple concurrent workflows

### Key Principles
- **No Custom Abstractions**: Use only RQ's built-in features
- **Incremental Refactoring**: Modify existing code gradually
- **Backward Compatibility**: Maintain existing API contracts
- **Simple Recovery**: Use RQ registries and metadata for workflow state