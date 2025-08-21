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
    # Implementation calls start_pdf_workflow() function
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
            job_ids=updated_context["job_ids"],
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
            console.print(f"Job IDs: {result['job_ids']}")

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
            # Calculate progress percentage
            total_jobs = len(workflow.get('job_ids', {}))
            completed_jobs = sum(1 for job in workflow.get('jobs', []) if job['status'] == 'finished')
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

The `documents.metadata_` field needs a structured schema to store analysis and preprocessing results:

```python
# extralit_server/src/extralit_server/api/schemas/v1/document/metadata.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class OCRQualityMetadata(BaseModel):
    """OCR quality analysis metadata."""
    total_chars: int = Field(..., description="Total characters analyzed")
    ocr_artifacts: int = Field(..., description="Number of OCR artifacts detected")
    suspicious_patterns: int = Field(..., description="Number of suspicious patterns found")
    ocr_quality_score: float = Field(..., description="Overall OCR quality score (0.0-1.0)")

class LayoutAnalysisMetadata(BaseModel):
    """PDF layout analysis metadata."""
    page_count: int = Field(..., description="Number of pages in PDF")
    has_tables: bool = Field(..., description="Whether tables were detected")
    has_figures: bool = Field(..., description="Whether figures were detected")
    text_regions: int = Field(..., description="Number of text regions detected")
    margin_analysis: Dict[str, Any] = Field(default_factory=dict, description="Margin analysis results")

class AnalysisMetadata(BaseModel):
    """Analysis job results stored in documents.metadata_."""
    has_ocr_text_layer: bool = Field(..., description="Whether PDF has OCR text layer")
    needs_ocr: bool = Field(..., description="Whether additional OCR processing is needed")
    ocr_quality: OCRQualityMetadata = Field(..., description="OCR quality analysis")
    layout_analysis: LayoutAnalysisMetadata = Field(..., description="Layout analysis results")
    analysis_completed_at: datetime = Field(..., description="When analysis was completed")

class PreprocessingMetadata(BaseModel):
    """Preprocessing job results stored in documents.metadata_."""
    processing_time: float = Field(..., description="Processing time in seconds")
    ocr_applied: bool = Field(..., description="Whether OCR was applied during preprocessing")
    processed_s3_url: Optional[str] = Field(None, description="S3 URL of processed PDF")
    preprocessing_completed_at: datetime = Field(..., description="When preprocessing was completed")

class DocumentProcessingMetadata(BaseModel):
    """Complete document processing metadata stored in documents.metadata_."""
    workflow_id: Optional[str] = Field(None, description="Workflow ID for tracking")
    analysis_metadata: Optional[AnalysisMetadata] = Field(None, description="Analysis results")
    preprocessing_metadata: Optional[PreprocessingMetadata] = Field(None, description="Preprocessing results")
    workflow_started_at: datetime = Field(..., description="When workflow was started")
    workflow_completed_at: Optional[datetime] = Field(None, description="When workflow was completed")
    workflow_status: str = Field(default="running", description="Overall workflow status")

    def update_analysis_results(self, analysis_result: dict) -> None:
        """Update analysis metadata from job result."""
        self.analysis_metadata = AnalysisMetadata(
            has_ocr_text_layer=analysis_result['has_ocr_text_layer'],
            needs_ocr=analysis_result['needs_ocr'],
            ocr_quality=OCRQualityMetadata(**analysis_result['analysis_metadata']),
            layout_analysis=LayoutAnalysisMetadata(**analysis_result['layout_analysis']),
            analysis_completed_at=datetime.utcnow()
        )

    def update_preprocessing_results(self, preprocess_result: dict) -> None:
        """Update preprocessing metadata from job result."""
        self.preprocessing_metadata = PreprocessingMetadata(
            processing_time=preprocess_result['processing_time'],
            ocr_applied=preprocess_result.get('ocr_applied', False),
            processed_s3_url=preprocess_result.get('processed_s3_url'),
            preprocessing_completed_at=datetime.utcnow()
        )

    def is_workflow_complete(self) -> bool:
        """Check if all workflow steps are complete."""
        return all([
            self.analysis_metadata is not None,
            self.preprocessing_metadata is not None,
        ])
```

### Simplified Database Model Using RQ Groups

```python
# extralit_server/src/extralit_server/models/database.py (simplified for RQ Groups)
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from typing import Optional

class DocumentWorkflow(Base):
    """Simplified workflow tracking using RQ Groups as source of truth."""
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_type: Mapped[str] = mapped_column(String(50))
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(255), nullable=True, index=True)  # For batch tracking

    # RQ Group integration
    group_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # RQ Group ID

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="workflows")
    workspace: Mapped["Workspace"] = relationship("Workspace")

    @classmethod
    async def get_by_document_id(cls, db: AsyncSession, document_id: UUID) -> Optional["DocumentWorkflow"]:
        """Get workflow by document ID."""
        result = await db.execute(select(cls).where(cls.document_id == document_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_group_id(cls, db: AsyncSession, group_id: str) -> Optional["DocumentWorkflow"]:
        """Get workflow by RQ Group ID."""
        result = await db.execute(select(cls).where(cls.group_id == group_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_reference(cls, db: AsyncSession, reference: str, workspace_id: str = None) -> list["DocumentWorkflow"]:
        """Get workflows by reference (batch tracking)."""
        query = select(cls).where(cls.reference == reference)
        if workspace_id:
            query = query.where(cls.workspace_id == workspace_id)
        result = await db.execute(query)
        return result.scalars().all()

    def get_workflow_status(self) -> dict:
        """Get workflow status from RQ Group (source of truth)."""

    def is_resumable(self) -> bool:
        """Check if workflow can be resumed using RQ Group status."""
        status = self.get_workflow_status()
        if status.get("error"):
            return False

        failed_jobs = status.get("failed_jobs", 0)
        completed_jobs = status.get("completed_jobs", 0)
        return failed_jobs > 0 and completed_jobs > 0

    def restart_failed_jobs(self) -> dict:
        """Restart failed jobs using RQ Group orchestrator."""
```

### New Pydantic Schemas for Job Input/Output

```python
# extralit_server/src/extralit_server/api/schemas/v1/documents/analysis.py
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class AnalysisJobInput(BaseModel):
    """Input for PDF analysis job"""
    document_id: UUID
    s3_url: str
    filename: str
    reference: str
    workspace_id: UUID

class AnalysisJobOutput(BaseModel):
    """Output from PDF analysis job"""
    document_id: UUID
    has_ocr_text_layer: bool
    ocr_quality_score: float
    needs_ocr: bool
    analysis_metadata: dict

# extralit_server/src/extralit_server/api/schemas/v1/documents/preprocessing.py (extend existing)
class PreprocessJobInput(BaseModel):
    """Input for PDF preprocessing job"""
    document_id: UUID
    s3_url: str
    filename: str
    reference: str
    workspace_id: UUID

class PreprocessJobOutput(BaseModel):
    """Output from PDF preprocessing job"""
    document_id: UUID
    original_s3_url: str
    processed_s3_url: str
    processing_time: float
    preprocessing_metadata: dict

# extralit_server/src/extralit_server/api/schemas/v1/jobs.py (extend existing)
class WorkflowJobResult(BaseModel):
    """Generic job result wrapper for workflow jobs"""
    job_id: str
    document_id: UUID
    job_type: str  # 'analysis', 'preprocess', 'ocr', 'text_extraction', 'table_extraction', 'embedding'
    status: str    # 'queued', 'started', 'finished', 'failed', 'deferred'
    result_data: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

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

### RQ-Native Job Implementation Pattern

```python
# extralit_server/src/extralit_server/jobs/pdf.py
from rq import get_current_job
from rq.job import Job

```

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
- Test POST /documents/bulk creates workflow jobs with proper RQ dependencies after S3 upload
- Test API returns workflow job IDs and initial status for tracking purposes

**Job Status Querying:**
- Test GET /jobs API filters jobs by document_id, reference, and workflow_step parameters
- Test API returns job metadata including workflow progress and RQ group information
- Test API shows error details and failure information when jobs fail

**Workflow Progress Monitoring:**
- Test API shows current workflow step and overall progress percentage for active workflows
- Test API correctly identifies completed workflows versus failed or stalled ones

### CLI Workflow Management Tests

**Workflow Status Commands:**
- Test `workflow status --document-id` command shows all jobs for a specific document
- Test `workflow status --reference` command shows jobs for all documents in a reference batch

**Failed Job Restart:**
- Test CLI can identify failed jobs in a workflow chain for a given document_id
- Test CLI restart command re-enqueues failed jobs with proper dependencies restored
- Test restarted workflow continues from the failed step without re-running completed jobs

**Error Handling:**
- Test CLI commands provide clear error messages for invalid document IDs or missing workflows
- Test CLI gracefully handles Redis connection issues and RQ registry access problems