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
POST /documents/bulk → process_bulk_upload() → Upload files to S3 + Create DB records → analysis_and_preprocess_job(document_id, s3_url) → conditional_ocr_job (if needed) → text_extraction_job
```

### Key Changes from Current Implementation

1. **File Upload Moved to API**: Files uploaded to S3 in `process_bulk_upload()` before job enqueueing
2. **Job Splitting**: `upload_and_preprocess_documents_job` split into chained jobs with combined analysis+preprocessing
3. **S3 URLs Instead of File Data**: Jobs receive document IDs and S3 URLs, not raw file bytes
4. **RQ Dependencies**: Use `depends_on` parameter for job chaining
5. **Job Metadata**: Track workflow progress using `job.meta`
6. **In-Place Processing**: OCRmyPDF overwrites the same S3 object path for page rotation

## Integration with Existing Code

### File Operations Integration

The design uses existing file operations from `contexts/files.py` but requires some helper functions to be added:


## CLI Commands Architecture

### Overview

The CLI workflow management system integrates with the existing Extralit CLI using Typer's sub-application pattern. It communicates with the server through FastAPI endpoints using the HTTP client, following the same pattern as the existing `import_bib.py` command.

**Key Architecture Principles:**
- CLI located in `extralit/src/extralit/cli/` (client-side)
- Server endpoints in `extralit-server/src/extralit_server/api/handlers/v1/` (server-side)
- Communication via `client.api.http_client.post/get()` calls
- No direct imports between CLI and server modules

### Required FastAPI Endpoints

Before implementing the CLI, we need these server endpoints:

```python
# extralit-server/src/extralit_server/api/handlers/v1/workflows.py
from fastapi import APIRouter, HTTPException, Query, Security
from typing import Optional, List
from uuid import UUID
from extralit_server.api.schemas.v1.workflows import (
    StartWorkflowRequest, StartWorkflowResponse,
    WorkflowStatusResponse, RestartWorkflowRequest
)

router = APIRouter(tags=["workflows"])

@router.post("/workflows/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest) -> StartWorkflowResponse:
    """Start PDF processing workflow for a document."""
    # Implementation calls start_document_workflow() function
    pass

@router.get("/workflows/status", response_model=List[WorkflowStatusResponse])
async def get_workflow_status(
    document_id: Optional[UUID] = Query(None),
    reference: Optional[str] = Query(None),
    workspace_name: Optional[str] = Query(None)
) -> List[WorkflowStatusResponse]:
    """Get workflow status for documents."""
    # Implementation calls WorkflowContext methods
    pass

@router.post("/workflows/restart", response_model=StartWorkflowResponse)
async def restart_workflow(request: RestartWorkflowRequest) -> StartWorkflowResponse:
    """Restart failed workflow jobs using DAG-based resumability."""
    try:
        # Get current workflow state
        workflow = await DocumentWorkflow.get_by_document_id(db, request.document_id)
        if not workflow:
            raise HTTPException(404, "Workflow not found")

        if not workflow.is_resumable():
            raise HTTPException(400, "Workflow is not in a resumable state")

        # Get workflow context for resumption
        current_context = workflow.get_workflow_context()

        updated_context = resume_workflow(
            request.document_id,
            current_context
        )

        # Update workflow record
        workflow.update_workflow_context(updated_context)
        await db.commit()

        return StartWorkflowResponse(
            workflow_id=str(workflow.id),
            document_id=str(request.document_id),
            group_id=workflow.group_id,
            status="running",
            restarted_jobs=workflow.get_failed_jobs()
        )

    except Exception as e:
        raise HTTPException(500, f"Failed to restart workflow: {str(e)}")
    pass

@router.get("/workflows/", response_model=List[WorkflowStatusResponse])
async def list_workflows(
    workspace_name: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50)
) -> List[WorkflowStatusResponse]:
    """List workflows with optional filtering."""
    # Implementation calls WorkflowContext.list_workflows()
    pass
```

### CLI Implementation

```python
# extralit/src/extralit/cli/workflows.py
import typer
from typing import Optional
from uuid import UUID
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from extralit.client import Extralit

console = Console()
workflow_app = typer.Typer(help="Manage PDF processing workflows")

@workflow_app.command()
def start(
    document_id: str = typer.Option(..., help="Document UUID to process"),
    workspace_name: str = typer.Option(..., help="Workspace name"),
    reference: str = typer.Option(None, help="Document reference for tracking"),
    force: bool = typer.Option(False, help="Force restart if workflow already exists"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed output")
):
    """Start PDF processing workflow for a document."""
    try:
        client = Extralit.from_credentials()

        # Call server endpoint
        response = client.api.http_client.post(
            f"{client.api_url}/api/v1/workflows/start",
            json={
                "document_id": document_id,
                "workspace_name": workspace_name,
                "reference": reference or f"doc_{document_id[:8]}",
                "force": force
            }
        )

        if response.status_code != 200:
            error_detail = response.json().get("detail", str(response.text))
            raise ValueError(f"Error starting workflow: {error_detail}")

        result = response.json()
        console.print(f"[green]✓ Started workflow {result['workflow_id']}[/green]")

        if verbose:
            console.print(f"Document ID: {result['document_id']}")
            console.print(f"Reference: {result['reference']}")
            console.print(f"Group ID: {result['group_id']}")

        console.print(f"Track progress with: [bold]extralit workflow status --document-id {document_id}[/bold]")

    except Exception as e:
        console.print(f"[red]Error starting workflow: {e}[/red]")
        raise typer.Exit(1)

@workflow_app.command()
def status(
    document_id: str = typer.Option(None, help="Document UUID to check"),
    reference: str = typer.Option(None, help="Document reference to check"),
    workspace_name: str = typer.Option(None, help="Filter by workspace name"),
    watch: bool = typer.Option(False, "-w", "--watch", help="Watch status updates in real-time"),
    json_output: bool = typer.Option(False, "--json", help="Output status as JSON")
):
    """Check workflow status for documents."""
    try:
        if not document_id and not reference:
            console.print("[red]Must specify either --document-id or --reference[/red]")
            raise typer.Exit(1)

        client = Extralit.from_credentials()

        # Call server endpoint
        params = {}
        if document_id:
            params["document_id"] = document_id
        if reference:
            params["reference"] = reference
        if workspace_name:
            params["workspace_name"] = workspace_name

        response = client.api.http_client.get(
            f"{client.api_url}/api/v1/workflows/status",
            params=params
        )

        if response.status_code != 200:
            error_detail = response.json().get("detail", str(response.text))
            raise ValueError(f"Error checking status: {error_detail}")

        workflows = response.json()

        if not workflows:
            console.print("[yellow]No workflows found[/yellow]")
            return

        if json_output:
            import json
            console.print(json.dumps(workflows, indent=2))
            return

        # Display status table
        _display_workflow_status_table(workflows, watch)

    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")
        raise typer.Exit(1)

@workflow_app.command()
def restart(
    document_id: str = typer.Option(None, help="Document UUID to restart"),
    reference: str = typer.Option(None, help="Document reference to restart"),
    workspace_name: str = typer.Option(None, help="Filter by workspace name"),
    failed_only: bool = typer.Option(True, help="Only restart failed jobs"),
    confirm: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Restart failed workflow jobs for documents."""
    try:
        if not document_id and not reference:
            console.print("[red]Must specify either --document-id or --reference[/red]")
            raise typer.Exit(1)

        client = Extralit.from_credentials()

        # First get workflows to restart
        params = {}
        if document_id:
            params["document_id"] = document_id
        if reference:
            params["reference"] = reference
        if workspace_name:
            params["workspace_name"] = workspace_name

        status_response = client.api.http_client.get(
            f"{client.api_url}/api/v1/workflows/status",
            params=params
        )

        if status_response.status_code != 200:
            raise ValueError("Failed to get workflow status")

        workflows = status_response.json()
        failed_workflows = [w for w in workflows if w['status'] == 'failed']

        if not failed_workflows:
            console.print("[yellow]No failed workflows found[/yellow]")
            return

        # Confirmation prompt
        if not confirm:
            workflow_count = len(failed_workflows)
            if not typer.confirm(f"Restart {workflow_count} failed workflow(s)?"):
                console.print("Cancelled")
                return

        # Restart workflows
        restarted_count = 0
        for workflow in failed_workflows:
            try:
                restart_response = client.api.http_client.post(
                    f"{client.api_url}/api/v1/workflows/restart",
                    json={
                        "document_id": workflow['document_id'],
                        "failed_only": failed_only
                    }
                )

                if restart_response.status_code == 200:
                    console.print(f"[green]✓ Restarted workflow for document {workflow['document_id']}[/green]")
                    restarted_count += 1
                else:
                    error_detail = restart_response.json().get("detail", "Unknown error")
                    console.print(f"[red]✗ Failed to restart workflow for document {workflow['document_id']}: {error_detail}[/red]")

            except Exception as e:
                console.print(f"[red]✗ Failed to restart workflow for document {workflow['document_id']}: {e}[/red]")

        console.print(f"[blue]Restarted {restarted_count} of {len(failed_workflows)} workflows[/blue]")

    except Exception as e:
        console.print(f"[red]Error restarting workflows: {e}[/red]")
        raise typer.Exit(1)

@workflow_app.command()
def list(
    workspace_name: str = typer.Option(None, help="Filter by workspace name"),
    status_filter: str = typer.Option(None, help="Filter by status (running, completed, failed)"),
    limit: int = typer.Option(50, help="Maximum number of workflows to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List recent workflows."""
    try:
        client = Extralit.from_credentials()

        params = {"limit": limit}
        if workspace_name:
            params["workspace_name"] = workspace_name
        if status_filter:
            params["status_filter"] = status_filter

        response = client.api.http_client.get(
            f"{client.api_url}/api/v1/workflows/",
            params=params
        )

        if response.status_code != 200:
            error_detail = response.json().get("detail", str(response.text))
            raise ValueError(f"Error listing workflows: {error_detail}")

        workflows = response.json()

        if not workflows:
            console.print("[yellow]No workflows found[/yellow]")
            return

        if json_output:
            import json
            console.print(json.dumps(workflows, indent=2, default=str))
            return

        _display_workflow_status_table(workflows, watch=False)

    except Exception as e:
        console.print(f"[red]Error listing workflows: {e}[/red]")
        raise typer.Exit(1)

def _display_workflow_status_table(workflows: list, watch: bool = False):
    """Display workflow status in a formatted table."""
    def create_table():
        table = Table(title="PDF Processing Workflows")
        table.add_column("Document ID", style="cyan", no_wrap=True)
        table.add_column("Reference", style="magenta")
        table.add_column("Workspace", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Started", style="dim")
        table.add_column("Duration", style="dim")

        for workflow in workflows:
            # Calculate progress percentage from RQ Group
            total_jobs = workflow.get('total_jobs', 0)
            completed_jobs = workflow.get('completed_jobs', 0)
            progress = f"{completed_jobs}/{total_jobs} ({int(completed_jobs/total_jobs*100) if total_jobs > 0 else 0}%)"

            # Format status with color
            status = workflow['status']
            if status == 'completed':
                status = f"[green]{status}[/green]"
            elif status == 'failed':
                status = f"[red]{status}[/red]"
            elif status == 'running':
                status = f"[yellow]{status}[/yellow]"

            # Calculate duration
            import datetime
            started = workflow.get('inserted_at')
            if started:
                if isinstance(started, str):
                    started = datetime.datetime.fromisoformat(started.replace('Z', '+00:00'))
                duration = str(datetime.datetime.utcnow() - started.replace(tzinfo=None)).split('.')[0]
            else:
                duration = "Unknown"

            table.add_row(
                workflow['document_id'][:8] + "...",
                workflow.get('reference', 'N/A'),
                workflow.get('workspace_name', 'N/A'),
                status,
                progress,
                started.strftime('%Y-%m-%d %H:%M') if started else 'N/A',
                duration
            )

        return table

    if watch:
        import time
        try:
            while True:
                console.clear()
                console.print(create_table())
                console.print("\n[dim]Press Ctrl+C to stop watching[/dim]")
                time.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped watching[/yellow]")
    else:
        console.print(create_table())

# Add to main CLI app
# In extralit/src/extralit/cli/__init__.py
# app.add_typer(workflow_app, name="workflow")
```

### CLI Usage Examples

```bash
# Start workflow for a specific document
extralit workflow start --document-id 123e4567-e89b-12d3-a456-426614174000 --workspace-name "research-papers"

# Check status of a specific document
extralit workflow status --document-id 123e4567-e89b-12d3-a456-426614174000

# Check status of all documents in a reference batch
extralit workflow status --reference "batch_2024_01_15" --workspace-name "research-papers"

# Watch status updates in real-time
extralit workflow status --document-id 123e4567-e89b-12d3-a456-426614174000 --watch

# List recent workflows
extralit workflow list --workspace-name "research-papers" --status-filter "failed"

# Restart failed workflows
extralit workflow restart --reference "batch_2024_01_15" --failed-only

# Get status as JSON for scripting
extralit workflow status --document-id 123e4567-e89b-12d3-a456-426614174000 --json
```

## Data Models

### Document Metadata Schema

The `documents.metadata_` field uses the existing structured schema in `extralit_server/src/extralit_server/api/schemas/v1/document/metadata.py` to store analysis and preprocessing results. This schema includes:

- **DocumentProcessingMetadata**: Complete workflow metadata with analysis and preprocessing results
- **AnalysisMetadata**: PDF analysis results (OCR quality, layout analysis)
- **PreprocessingMetadata**: Processing results and timing information
- **OCRQualityMetadata**: OCR quality metrics and scores
- **LayoutAnalysisMetadata**: PDF layout analysis results

### Database Model Using RQ Groups

The existing `DocumentWorkflow` model in `extralit_server/src/extralit_server/models/database.py` needs to be updated to support RQ Groups:

**Key Changes Required:**
- Replace `job_ids` dictionary field with `group_id` string field
- Add `status` field for caching workflow status
- Add methods to interact with RQ Groups (`get_workflow_status`, `is_resumable`, `restart_failed_jobs`)
- Update database migration to support the new schema

**RQ Groups Integration:**
- Each document workflow gets a unique RQ Group ID
- All jobs for a document are added to the same group
- Group status becomes the source of truth for workflow state
- Database model provides efficient querying and caching layer

### Job Schemas for RQ Groups Integration

The existing `WorkflowJobResult` schema in `extralit_server/src/extralit_server/api/schemas/v1/jobs.py` needs to be extended to support RQ Groups:

**Required Updates:**
- Add `group_id` field to track which RQ Group the job belongs to
- Add `group_status` field for overall group status information
- Extend job metadata to include group-level progress information

**New Schema Fields:**
- `group_id`: RQ Group identifier for the workflow
- `group_progress`: Overall progress of the group (0.0-1.0)
- `group_status`: Status of the entire group (running, completed, failed)
- `workflow_step`: Current step in the workflow process

## RQ-Native Workflow Design

### Leveraging RQ Groups and Dependencies

Instead of building custom workflow orchestration, we use RQ's native Groups and job dependencies for resumable workflows:

### Job Properties for Resumability

Each job must have these properties to enable resumability:

1. **Idempotency**: Jobs can be safely re-run without side effects
2. **Artifact Management**: Clear definition of what artifacts are produced/consumed
3. **Context Awareness**: Jobs receive and update workflow context
4. **Dependency Declaration**: Explicit dependencies in the DAG definition
5. **Conditional Logic**: Ability to skip jobs based on workflow state

### RQ Groups Job Implementation Pattern

Jobs will be implemented using RQ Groups for workflow coordination:

**Key Implementation Requirements:**
- Jobs are added to RQ Groups during enqueueing
- Job metadata includes group_id and workflow context
- Jobs use `depends_on` parameter for dependency management
- Group status is queried using RQ Groups API
- Failed jobs can be restarted within the same group

**Integration Points:**
- `extralit_server/src/extralit_server/jobs/document_jobs.py`: Update existing job functions
- `extralit_server/src/extralit_server/workflows/documents.py`: Update workflow orchestrator
- `extralit_server/src/extralit_server/contexts/workflows.py`: Update job querying functions

### Integration with Existing Code Structure

The design leverages existing modules while adding resumability:

1. **Analysis Job**: Uses `PDFOCRLayerDetector` from `analysis.py` and `PDFAnalyzer` from `margin.py`
2. **Preprocess Job**: Uses `PDFPreprocessor` from `preprocessing.py` with analysis disabled
3. **File Handling**: Uses existing `download_file_from_s3()` and `upload_file_to_s3()` from `files.py`
4. **Schemas**: Extends existing `PDFMetadata` from `preprocessing.py`
5. **Workflow State**: Stored in enhanced `DocumentWorkflow` model with artifact tracking

This approach minimizes code duplication and leverages the existing, well-tested PDF processing logic while adding comprehensive resumability.

## Implementation Strategy

### Phase 1: Minimal Viable Workflow
1. **Refactor Existing Job**: Split `upload_and_preprocess_documents_job` into `analysis_job` and `preprocess_job`
2. **Move File Upload**: Upload files to S3 in `process_bulk_upload()` before job enqueueing
3. **Add Job Metadata**: Track workflow progress using `job.meta`
4. **Test Basic Chaining**: Verify jobs can enqueue dependent jobs

### Phase 2: Complete Workflow
2. **RQ Dependencies**: Use `depends_on` parameter for job chaining
4. **API Extensions**: Add document workflow status endpoint

### Phase 3: Management and Recovery
1. **CLI Commands**: Add workflow start/status commands using typer
2. **Error Handling**: Implement job restart for failed workflows
3. **Testing**: Add comprehensive tests for workflow execution
4. **Performance**: Optimize for multiple concurrent workflows

### Key Principles
- **Incremental Refactoring**: Modify existing code gradually
- **Simple Recovery**: Use RQ registries and metadata for workflow state

## Testing Strategy

### End-to-End Workflow Tests

**Complete PDF Processing Workflow:**
- Test PDF workflow from upload through analysis, preprocessing, and conditional OCR completion with all jobs succeeding

**Conditional OCR Logic:**
- Test workflow skips OCR job when analysis determines PDF has good OCR text layer
- Test workflow enqueues OCR job when analysis determines PDF needs OCR processing

**Workflow State Tracking:**
- Test document metadata is updated correctly at each workflow step completion
- Test workflow status progresses from "queued" to "running" to "completed" appropriately

### API Integration Tests

**Bulk Upload Integration:**
- Test POST /documents/bulk creates RQ Groups with proper job dependencies after S3 upload
- Test API returns workflow group_id and initial status for tracking purposes

**Job Status Querying:**
- Test GET /jobs API filters jobs by document_id, reference, and workflow_step parameters
- Test API returns job metadata including RQ Group information and progress
- Test API shows error details and failure information when jobs fail
- Test API correctly queries RQ Groups for job status instead of individual job fetches

**Workflow Progress Monitoring:**
- Test API shows current workflow step and overall progress percentage for active workflows
- Test API correctly identifies completed workflows versus failed or stalled ones

### CLI Workflow Management Tests

**Workflow Status Commands:**
- Test `workflow status --document-id` command shows all jobs for a specific document
- Test `workflow status --reference` command shows jobs for all documents in a reference batch

**Failed Job Restart:**
- Test CLI can identify failed jobs using RQ Group status for a given document_id
- Test CLI restart command re-enqueues failed jobs within the same RQ Group with proper dependencies
- Test restarted workflow continues from the failed step without re-running completed jobs
- Test RQ Group-based resumability maintains workflow integrity

**Error Handling:**
- Test CLI commands provide clear error messages for invalid document IDs or missing workflows
- Test CLI gracefully handles Redis connection issues and RQ Groups access problems
- Test CLI handles RQ Group expiration and cleanup scenarios