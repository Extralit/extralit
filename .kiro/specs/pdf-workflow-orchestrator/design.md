# PDF Workflow Orchestrator Design

## Overview

The PDF Workflow Orchestrator leverages RQ's native job chaining capabilities to process PDFs through a 6-step workflow. The design uses RQ's built-in features (job dependencies, job groups, job metadata, job registries) without custom abstractions, focusing on practical implementation and maintainability.

## Architecture

### RQ Native Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF Upload    │    │   RQ Job        │    │   Job Status    │
│   Triggers      │────│   Dependencies  │────│   Tracking      │
│   Workflow      │    │   & Groups      │    │   via API       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Job Functions │    │   Redis Queue   │    │   Worker Pools  │
│   with @job     │────│   (Existing)    │────│   CPU + GPU     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### PDF Processing Workflow

```
Document Upload
       │
       ▼
┌─────────────┐    ┌─────────────┐
│  analysis   │    │ preprocess  │  (Parallel)
│    job      │    │    job      │
└─────────────┘    └─────────────┘
       │                   │
       ▼                   │
┌─────────────┐            │
│  ocr_job    │            │  (Conditional)
│ (if needed) │            │
└─────────────┘            │
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│text_extract │    │table_extract│  (Depends on analysis/OCR)
│    job      │    │job (GPU)    │
└─────────────┘    └─────────────┘
       │                   │
       └─────────┬─────────┘
                 ▼
         ┌─────────────┐
         │ embedding   │
         │    job      │
         └─────────────┘
```

### Integration with Existing Infrastructure

- **RQ Jobs**: Uses existing RQ infrastructure with enhanced job functions
- **SQLAlchemy**: Uses existing database models and connections
- **Redis**: Uses existing Redis connection for job queues and metadata
- **S3/MinIO**: Uses existing file storage with presigned URLs
- **FastAPI**: Extends existing job API endpoints for workflow queries

## Components and Interfaces

### 1. RQ Job Functions with Type Hints

```python
from rq.decorators import job
from rq import get_current_job
from typing import UUID, Optional
from extralit_server.jobs.queues import DEFAULT_QUEUE, HIGH_QUEUE, GPU_QUEUE

@job(queue=DEFAULT_QUEUE, timeout=300, result_ttl=3600)
def analysis_job(document_id: UUID, reference: str, workspace_id: UUID) -> dict:
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

    # Analysis logic here
    analysis_result = perform_analysis(document_id)

    # Conditionally enqueue OCR job
    if analysis_result.needs_ocr:
        ocr_job_instance = ocr_job.delay(document_id, reference, workspace_id, analysis_result)
        current_job.meta['ocr_job_id'] = ocr_job_instance.id

    # Always enqueue text extraction
    text_job_instance = text_extraction_job.delay(document_id, reference, workspace_id, analysis_result)
    current_job.meta['text_job_id'] = text_job_instance.id

    current_job.save_meta()
    return analysis_result

@job(queue=GPU_QUEUE, timeout=600, result_ttl=3600)
def table_extraction_job(document_id: UUID, reference: str, workspace_id: UUID,
                        analysis_result: dict, ocr_result: Optional[dict] = None) -> dict:
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

    # Table extraction logic here
    table_result = extract_tables(document_id, analysis_result, ocr_result)

    current_job.meta['completed_at'] = datetime.utcnow().isoformat()
    current_job.save_meta()
    return table_result
```

### 2. RQ Job Groups for Document Workflows

```python
from rq.group import Group
from rq import Queue
from extralit_server.jobs.queues import REDIS_CONNECTION

def start_pdf_workflow(document_id: UUID, reference: str, workspace_id: UUID, user_id: UUID) -> str:
    """Start complete PDF processing workflow using RQ Groups."""

    # Create group for this document's workflow
    group = Group.create(connection=REDIS_CONNECTION, name=f"pdf_workflow_{document_id}")

    # Enqueue parallel jobs (analysis + preprocess)
    analysis_job_instance = analysis_job.delay(document_id, reference, workspace_id)
    preprocess_job_instance = preprocess_job.delay(document_id, reference, workspace_id)

    # Store job IDs in group metadata (if needed)
    group_jobs = {
        'analysis_job_id': analysis_job_instance.id,
        'preprocess_job_id': preprocess_job_instance.id,
        'document_id': str(document_id),
        'reference': reference,
        'workspace_id': str(workspace_id),
        'user_id': str(user_id),
        'started_at': datetime.utcnow().isoformat()
    }

    return group.id

def get_workflow_status(group_id: str) -> dict:
    """Get workflow status using RQ Group."""
    group = Group.fetch(group_id, connection=REDIS_CONNECTION)
    jobs = group.get_jobs()

    workflow_status = {
        'group_id': group_id,
        'total_jobs': len(jobs),
        'completed_jobs': len([j for j in jobs if j.is_finished]),
        'failed_jobs': len([j for j in jobs if j.is_failed]),
        'jobs': []
    }

    for job in jobs:
        job_info = {
            'job_id': job.id,
            'status': job.get_status(),
            'workflow_step': job.meta.get('workflow_step'),
            'document_id': job.meta.get('document_id'),
            'reference': job.meta.get('reference'),
            'started_at': job.meta.get('started_at'),
            'completed_at': job.meta.get('completed_at'),
            'error': str(job.exc_info) if job.is_failed else None
        }
        workflow_status['jobs'].append(job_info)

    return workflow_status
```

### 3. Job Querying by Document Metadata

```python
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry, DeferredJobRegistry
from rq import Job

def get_jobs_for_document(document_id: UUID, connection=REDIS_CONNECTION) -> list[dict]:
    """Find all jobs for a document using job metadata."""
    all_jobs = []

    # Check all job registries
    registries = [
        ('started', StartedJobRegistry),
        ('finished', FinishedJobRegistry),
        ('failed', FailedJobRegistry),
        ('deferred', DeferredJobRegistry)
    ]

    for registry_name, registry_class in registries:
        registry = registry_class(connection=connection)
        for job_id in registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=connection)
                if job.meta.get('document_id') == str(document_id):
                    job_info = {
                        'job_id': job.id,
                        'status': registry_name,
                        'workflow_step': job.meta.get('workflow_step'),
                        'reference': job.meta.get('reference'),
                        'workspace_id': job.meta.get('workspace_id'),
                        'started_at': job.meta.get('started_at'),
                        'completed_at': job.meta.get('completed_at'),
                        'progress': job.meta.get('progress', 0),
                        'error': str(job.exc_info) if job.is_failed else None,
                        'result': job.result if job.is_finished else None
                    }
                    all_jobs.append(job_info)
            except Exception as e:
                # Job might have expired or been deleted
                continue

    return sorted(all_jobs, key=lambda x: x.get('started_at', ''))

def get_jobs_by_reference(reference: str, connection=REDIS_CONNECTION) -> list[dict]:
    """Find all jobs for a reference using job metadata."""
    all_jobs = []

    registries = [
        ('started', StartedJobRegistry),
        ('finished', FinishedJobRegistry),
        ('failed', FailedJobRegistry),
        ('deferred', DeferredJobRegistry)
    ]

    for registry_name, registry_class in registries:
        registry = registry_class(connection=connection)
        for job_id in registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=connection)
                if job.meta.get('reference') == reference:
                    job_info = {
                        'job_id': job.id,
                        'status': registry_name,
                        'workflow_step': job.meta.get('workflow_step'),
                        'document_id': job.meta.get('document_id'),
                        'workspace_id': job.meta.get('workspace_id'),
                        'started_at': job.meta.get('started_at'),
                        'completed_at': job.meta.get('completed_at'),
                        'error': str(job.exc_info) if job.is_failed else None
                    }
                    all_jobs.append(job_info)
            except Exception:
                continue

    return sorted(all_jobs, key=lambda x: x.get('started_at', ''))
```

### 4. Enhanced Job API Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from extralit_server.api.schemas.v1.jobs import JobSchema, WorkflowStatusSchema

@router.get("/jobs/", response_model=List[JobSchema])
async def get_jobs(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    document_id: Optional[UUID] = Query(None, description="Filter by document ID"),
    reference: Optional[str] = Query(None, description="Filter by reference"),
    workflow_step: Optional[str] = Query(None, description="Filter by workflow step"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Get jobs with optional filtering by document, reference, or workflow step."""

    if document_id:
        jobs_data = get_jobs_for_document(document_id)
    elif reference:
        jobs_data = get_jobs_by_reference(reference)
    else:
        # Return recent jobs if no filter specified
        jobs_data = get_recent_jobs(limit=100)

    # Apply additional filters
    if workflow_step:
        jobs_data = [j for j in jobs_data if j.get('workflow_step') == workflow_step]
    if status:
        jobs_data = [j for j in jobs_data if j.get('status') == status]

    return [JobSchema(**job_data) for job_data in jobs_data]

@router.get("/documents/{document_id}/workflow-status", response_model=WorkflowStatusSchema)
async def get_document_workflow_status(
    document_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Get complete workflow status for a document."""

    jobs_data = get_jobs_for_document(document_id)

    # Calculate workflow progress
    workflow_steps = ['analysis', 'preprocess', 'ocr', 'text_extraction', 'table_extraction', 'embedding']
    completed_steps = set(j['workflow_step'] for j in jobs_data if j['status'] == 'finished')
    progress = len(completed_steps) / len(workflow_steps)

    # Determine overall status
    if any(j['status'] == 'failed' for j in jobs_data):
        overall_status = 'failed'
    elif progress == 1.0:
        overall_status = 'completed'
    elif any(j['status'] in ['started', 'queued'] for j in jobs_data):
        overall_status = 'running'
    else:
        overall_status = 'pending'

    return WorkflowStatusSchema(
        document_id=document_id,
        status=overall_status,
        progress=progress,
        jobs=jobs_data,
        started_at=min((j['started_at'] for j in jobs_data if j['started_at']), default=None),
        completed_at=max((j['completed_at'] for j in jobs_data if j['completed_at']), default=None)
    )
```

### 5. Queue Configuration for Multi-Host Processing

```python
# extralit_server/jobs/queues.py
from rq import Queue
from redis import Redis

# Existing Redis connection
REDIS_CONNECTION = Redis.from_url(settings.REDIS_URL)

# Define queues for different processing types
DEFAULT_QUEUE = Queue('default', connection=REDIS_CONNECTION)
HIGH_QUEUE = Queue('high', connection=REDIS_CONNECTION)
GPU_QUEUE = Queue('gpu', connection=REDIS_CONNECTION)  # For table extraction on GPU hosts

# Queue routing for different job types
QUEUE_ROUTING = {
    'analysis': DEFAULT_QUEUE,
    'preprocess': DEFAULT_QUEUE,
    'ocr': DEFAULT_QUEUE,
    'text_extraction': DEFAULT_QUEUE,
    'table_extraction': GPU_QUEUE,  # Route to GPU workers
    'embedding': DEFAULT_QUEUE
}

def get_queue_for_job(job_type: str) -> Queue:
    """Get appropriate queue for job type."""
    return QUEUE_ROUTING.get(job_type, DEFAULT_QUEUE)
```

### 6. CLI Commands for Workflow Management

```python
# Add to extralit-server CLI
import click
from extralit_server.jobs.pdf_workflow import start_pdf_workflow, get_workflow_status

@cli.group()
def workflow():
    """PDF workflow management commands."""
    pass

@workflow.command()
@click.option("--document-id", required=True, help="Document UUID to process")
@click.option("--reference", help="Document reference")
@click.option("--workspace-id", required=True, help="Workspace UUID")
@click.option("--user-id", required=True, help="User UUID")
def start(document_id: str, reference: str, workspace_id: str, user_id: str):
    """Start PDF processing workflow for a document."""
    try:
        group_id = start_pdf_workflow(
            UUID(document_id),
            reference or f"doc_{document_id[:8]}",
            UUID(workspace_id),
            UUID(user_id)
        )
        click.echo(f"Started workflow group: {group_id}")
    except Exception as e:
        click.echo(f"Error starting workflow: {e}", err=True)

@workflow.command()
@click.option("--document-id", help="Document UUID to check")
@click.option("--reference", help="Document reference to check")
def status(document_id: str = None, reference: str = None):
    """Check workflow status by document ID or reference."""
    try:
        if document_id:
            jobs = get_jobs_for_document(UUID(document_id))
        elif reference:
            jobs = get_jobs_by_reference(reference)
        else:
            click.echo("Must specify either --document-id or --reference", err=True)
            return

        if not jobs:
            click.echo("No jobs found")
            return

        click.echo(f"Found {len(jobs)} jobs:")
        for job in jobs:
            click.echo(f"  {job['workflow_step']}: {job['status']} ({job['job_id']})")
    except Exception as e:
        click.echo(f"Error checking status: {e}", err=True)

@workflow.command()
@click.option("--document-id", required=True, help="Document UUID to restart")
@click.option("--step", help="Specific step to restart (optional)")
def restart(document_id: str, step: str = None):
    """Restart failed workflow jobs for a document."""
    try:
        jobs = get_jobs_for_document(UUID(document_id))
        failed_jobs = [j for j in jobs if j['status'] == 'failed']

        if not failed_jobs:
            click.echo("No failed jobs found")
            return

        click.echo(f"Found {len(failed_jobs)} failed jobs")
        # Implementation would re-enqueue failed jobs
        # This requires more complex logic to handle dependencies

    except Exception as e:
        click.echo(f"Error restarting workflow: {e}", err=True)
```

## Data Models

### API Response Models

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class JobStatusSchema(BaseModel):
    """Schema for individual job status."""
    job_id: str
    status: str  # queued, started, finished, failed, deferred
    workflow_step: Optional[str]
    document_id: Optional[UUID]
    reference: Optional[str]
    workspace_id: Optional[UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: int = 0
    error: Optional[str]
    result: Optional[dict]

class WorkflowStatusSchema(BaseModel):
    """Schema for complete workflow status."""
    document_id: UUID
    reference: Optional[str]
    status: str  # pending, running, completed, failed
    progress: float  # 0.0 to 1.0
    jobs: List[JobStatusSchema]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_jobs: int
    completed_jobs: int
    failed_jobs: int

class WorkflowGroupSchema(BaseModel):
    """Schema for RQ Group information."""
    group_id: str
    document_id: UUID
    reference: str
    workspace_id: UUID
    user_id: UUID
    created_at: datetime
    job_count: int
    completed_count: int
    failed_count: int
```

## Error Handling

### RQ Native Error Handling

1. **Job Failures**: RQ automatically moves failed jobs to FailedJobRegistry with exception details
2. **Dependency Failures**: RQ prevents dependent jobs from running when dependencies fail
3. **Retry Logic**: Use RQ's built-in retry mechanism with `@job(retry=Retry(max=3, interval=60))`
4. **Error Information**: Access failure details via `job.exc_info` and `job.meta`

### File Access and Resource Management

1. **Database Connections**: Use existing dependency injection for database sessions
2. **S3 Access**: Use existing S3 client and presigned URL patterns
3. **Temporary Files**: Clean up temporary files in job functions using try/finally blocks
4. **Resource Validation**: Validate document existence and permissions before processing

### Workflow Recovery

1. **Failed Job Identification**: Query FailedJobRegistry to find failed jobs by document
2. **Selective Restart**: Re-enqueue specific failed jobs while preserving completed work
3. **Dependency Resolution**: Ensure dependencies are satisfied when restarting jobs
4. **Idempotent Operations**: Design jobs to be safely re-runnable

## Testing Strategy

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch
from rq.job import Job
from extralit_server.jobs.pdf_workflow import analysis_job, get_jobs_for_document

def test_analysis_job_metadata():
    """Test that analysis job sets correct metadata."""
    with patch('extralit_server.jobs.pdf_workflow.get_current_job') as mock_job:
        mock_job_instance = Mock()
        mock_job_instance.meta = {}
        mock_job.return_value = mock_job_instance

        # Test job execution
        result = analysis_job(
            document_id=UUID('12345678-1234-1234-1234-123456789012'),
            reference='test-ref',
            workspace_id=UUID('87654321-4321-4321-4321-210987654321')
        )

        # Verify metadata was set
        assert mock_job_instance.meta['workflow_step'] == 'analysis'
        assert mock_job_instance.meta['document_id'] == '12345678-1234-1234-1234-123456789012'
        assert mock_job_instance.save_meta.called

def test_get_jobs_for_document():
    """Test querying jobs by document ID."""
    with patch('extralit_server.jobs.pdf_workflow.StartedJobRegistry') as mock_registry:
        mock_registry.return_value.get_job_ids.return_value = ['job1', 'job2']

        with patch('rq.job.Job.fetch') as mock_fetch:
            mock_job = Mock()
            mock_job.meta = {'document_id': 'test-doc-id', 'workflow_step': 'analysis'}
            mock_fetch.return_value = mock_job

            jobs = get_jobs_for_document('test-doc-id')
            assert len(jobs) > 0
```

### Integration Testing

```python
@pytest.mark.integration
def test_pdf_workflow_integration(test_db, redis_connection):
    """Test complete PDF workflow with real Redis and database."""
    # Create test document in database
    document = create_test_document(test_db)

    # Start workflow
    group_id = start_pdf_workflow(
        document.id,
        'test-ref',
        document.workspace_id,
        document.user_id
    )

    # Wait for jobs to complete (with timeout)
    wait_for_workflow_completion(group_id, timeout=60)

    # Verify all steps completed
    jobs = get_jobs_for_document(document.id)
    completed_steps = {j['workflow_step'] for j in jobs if j['status'] == 'finished'}
    expected_steps = {'analysis', 'preprocess', 'text_extraction', 'embedding'}
    assert expected_steps.issubset(completed_steps)

def test_cli_workflow_commands(cli_runner, test_db):
    """Test CLI workflow commands."""
    document = create_test_document(test_db)

    # Test start command
    result = cli_runner.invoke(workflow_start, [
        '--document-id', str(document.id),
        '--workspace-id', str(document.workspace_id),
        '--user-id', str(document.user_id)
    ])
    assert result.exit_code == 0
    assert 'Started workflow group' in result.output
```

### Performance Testing

1. **Concurrent Workflows**: Test multiple documents processing simultaneously
2. **Worker Scaling**: Verify performance with multiple CPU and GPU workers
3. **Queue Throughput**: Monitor Redis queue performance under load
4. **Memory Usage**: Track memory usage with large PDF files
5. **Database Performance**: Monitor database query performance during workflow execution

## Implementation Plan

### Phase 1: RQ Native Job Functions (Week 1)
1. Convert existing document jobs to use RQ @job decorator with type hints
2. Add job metadata tracking (document_id, reference, workflow_step)
3. Implement conditional job enqueueing in analysis_job
4. Set up separate GPU queue for table extraction
5. Test basic job chaining with dependencies

### Phase 2: Job Querying and API Enhancement (Week 2)
1. Implement job querying functions (by document_id, reference)
2. Extend existing /jobs API with filtering parameters
3. Add document workflow status endpoint
4. Implement RQ Group creation and management
5. Test job metadata querying across registries

### Phase 3: CLI and Workflow Management (Week 3)
1. Add CLI commands for starting workflows
2. Implement workflow status checking via CLI
3. Add job restart functionality for failed workflows
4. Test complete PDF processing pipeline
5. Add error handling and recovery mechanisms

### Phase 4: Production Readiness (Week 4)
1. Add comprehensive testing (unit, integration, performance)
2. Optimize queue configuration for multi-host deployment
3. Add monitoring and logging for workflow execution
4. Performance testing with multiple workers
5. Documentation and deployment guides

### Key Implementation Notes
- **Incremental Development**: Each phase builds on RQ native capabilities, only building Abstractions when necessary
- **Simple Recovery**: Use RQ registries and metadata for workflow recovery