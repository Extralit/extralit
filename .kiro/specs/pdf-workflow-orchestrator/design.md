# Workflow Orchestrator Design

## Overview

The Workflow Orchestrator extends extralit-server's existing RQ job infrastructure to provide simple, flexible job chaining capabilities. The design focuses on minimal complexity while enabling powerful workflow patterns through decorators, type hints, and efficient resource management.

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Workflow      │    │   Job Registry  │    │   Tracking      │
│   Decorators    │────│   & Metadata    │────│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RQ Jobs       │    │   Redis Queue   │    │   CLI Commands  │
│   (Enhanced)    │────│   (Existing)    │────│   (New)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Integration with Existing Infrastructure

The orchestrator builds on existing extralit-server components:
- **RQ Jobs**: Extends current job system with workflow capabilities
- **SQLAlchemy Models**: Adds workflow tracking tables
- **Redis**: Uses existing Redis connection for job queues
- **S3/MinIO**: Leverages existing file storage for efficient file handling
- **FastAPI**: Extends existing job API endpoints

## Components and Interfaces

### 1. Workflow Decorators

```python
from typing import TypeVar, Callable, Any
from extralit_server.workflows import workflow_job, WorkflowContext

T = TypeVar('T')

@workflow_job(
    queue="default",
    timeout=300,
    retry_max=3,
    next_jobs=["ocr_job"]  # Optional: specify next jobs in chain
)
async def analysis_job(
    ctx: WorkflowContext,
    document_id: UUID,
    workspace_id: UUID
) -> AnalysisResult:
    """Analyze PDF structure and content."""
    # Job implementation
    pass

@workflow_job(
    queue="gpu",  # Different queue for GPU workers
    timeout=600,
    depends_on=["analysis_job", "ocr_job"]  # Wait for multiple jobs
)
async def table_extraction_job(
    ctx: WorkflowContext,
    document_id: UUID,
    analysis_result: AnalysisResult,
    ocr_result: OCRResult
) -> TableExtractionResult:
    """Extract tables using GPU resources."""
    # Job implementation
    pass
```

### 2. WorkflowContext

```python
@dataclass
class WorkflowContext:
    """Context passed to all workflow jobs."""
    workflow_id: UUID
    document_id: UUID
    reference: str
    user_id: UUID
    workspace_id: UUID

    # Database and storage access
    db_session: AsyncSession
    s3_client: MinioClient

    # Job management
    def enqueue_next(self, job_name: str, **kwargs) -> str:
        """Enqueue the next job in the workflow."""
        pass

    def enqueue_multiple(self, jobs: list[tuple[str, dict]]) -> list[str]:
        """Enqueue multiple jobs (fan-out pattern)."""
        pass

    def get_file_url(self, file_path: str) -> str:
        """Get presigned URL for file access."""
        pass

    def store_result(self, result: Any, key: str) -> None:
        """Store intermediate results for later jobs."""
        pass

    def get_result(self, key: str) -> Any:
        """Retrieve results from previous jobs."""
        pass
```

### 3. Job Registry and Metadata

```python
class WorkflowJobRegistry:
    """Registry for workflow jobs and their metadata."""

    def __init__(self):
        self._jobs: dict[str, WorkflowJobMetadata] = {}
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register_job(self, name: str, func: Callable, metadata: WorkflowJobMetadata):
        """Register a workflow job."""
        pass

    def register_workflow(self, name: str, definition: WorkflowDefinition):
        """Register a complete workflow definition."""
        pass

    def get_job(self, name: str) -> WorkflowJobMetadata:
        """Get job metadata by name."""
        pass

    def get_workflow(self, name: str) -> WorkflowDefinition:
        """Get workflow definition by name."""
        pass

@dataclass
class WorkflowJobMetadata:
    name: str
    function: Callable
    queue: str
    timeout: int
    retry_max: int
    next_jobs: list[str]
    depends_on: list[str]
    input_types: dict[str, type]
    output_type: type
```

### 4. Workflow Tracking Database Models

```python
class WorkflowExecution(Base):
    """Track workflow execution for documents."""
    __tablename__ = "workflow_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="running")  # running, completed, failed
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="workflow_executions")
    job_executions: Mapped[list["WorkflowJobExecution"]] = relationship("WorkflowJobExecution", back_populates="workflow")

class WorkflowJobExecution(Base):
    """Track individual job execution within workflows."""
    __tablename__ = "workflow_job_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_executions.id"), nullable=False)
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rq_job_id: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, running, completed, failed
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Store job results as JSON for intermediate data passing
    result_data: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Relationships
    workflow: Mapped["WorkflowExecution"] = relationship("WorkflowExecution", back_populates="job_executions")
```

### 5. Enhanced Job API

```python
# Extend existing job API with workflow-specific endpoints
@router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user)
):
    """Get complete workflow status including all job steps."""
    pass

@router.get("/documents/{document_id}/workflows", response_model=list[WorkflowStatusResponse])
async def get_document_workflows(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user)
):
    """Get all workflows for a specific document."""
    pass

@router.get("/workflows/reference/{reference}", response_model=list[WorkflowStatusResponse])
async def get_workflows_by_reference(
    reference: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user)
):
    """Get workflows by document reference."""
    pass
```

### 6. CLI Commands

```python
# Add to extralit-server CLI
@cli.group()
def workflow():
    """Workflow management commands."""
    pass

@workflow.command()
@click.option("--document-id", required=True, help="Document UUID to process")
@click.option("--workflow", default="pdf-processing", help="Workflow name to execute")
@click.option("--user-id", required=True, help="User ID for the workflow")
def enqueue(document_id: str, workflow: str, user_id: str):
    """Enqueue a complete workflow for a document."""
    pass

@workflow.command()
@click.option("--workflow-id", required=True, help="Workflow ID to check")
def status(workflow_id: str):
    """Check workflow status."""
    pass

@workflow.command()
def list_workflows():
    """List all registered workflows."""
    pass
```

## Data Models

### Workflow Definition

```python
@dataclass
class WorkflowDefinition:
    """Define a complete workflow with job dependencies."""
    name: str
    description: str
    jobs: list[WorkflowJobMetadata]
    entry_point: str  # Name of the first job to run

    def validate(self) -> list[str]:
        """Validate workflow definition for circular dependencies, etc."""
        pass

    def get_execution_order(self) -> list[str]:
        """Get topological order of job execution."""
        pass

# Example workflow definition
PDF_PROCESSING_WORKFLOW = WorkflowDefinition(
    name="pdf-processing",
    description="Complete PDF processing pipeline",
    jobs=[
        # Jobs are registered via decorators, this just defines the workflow
    ],
    entry_point="analysis_job"
)
```

### API Response Models

```python
@dataclass
class WorkflowJobStatus:
    job_name: str
    rq_job_id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

@dataclass
class WorkflowStatusResponse:
    workflow_id: UUID
    workflow_name: str
    document_id: UUID
    reference: str | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    jobs: list[WorkflowJobStatus]
    progress: float  # Percentage complete (0.0 to 1.0)
```

## Error Handling

### Job Failure Handling

1. **Individual Job Failures**: When a job fails, the workflow stops and the error is recorded
2. **Retry Logic**: Jobs can specify retry policies via decorator parameters
3. **Error Propagation**: Errors are captured and stored in the database for debugging
4. **Workflow Recovery**: CLI commands allow restarting workflows from any point

### File Access Errors

1. **Validation**: Check file existence and permissions before job execution
2. **Fallback**: Provide alternative file access methods (direct S3 vs presigned URLs)
3. **Cleanup**: Ensure temporary files are cleaned up even on failure

### Database Consistency

1. **Transactions**: Use database transactions for workflow state updates
2. **Rollback**: Implement rollback mechanisms for partial workflow failures
3. **Idempotency**: Design jobs to be idempotent where possible

## Testing Strategy

### Unit Testing

```python
# Test workflow job registration
def test_workflow_job_registration():
    registry = WorkflowJobRegistry()

    @workflow_job(queue="test", timeout=60)
    async def test_job(ctx: WorkflowContext, input_data: str) -> str:
        return f"processed: {input_data}"

    assert "test_job" in registry._jobs
    assert registry.get_job("test_job").timeout == 60

# Test workflow execution
async def test_workflow_execution():
    # Mock database and Redis
    # Test complete workflow execution
    # Verify job chaining and data passing
    pass
```

### Integration Testing

```python
# Test with real Redis and database
async def test_pdf_processing_workflow():
    # Create test document
    # Enqueue workflow
    # Wait for completion
    # Verify results at each step
    pass

# Test CLI commands
def test_cli_workflow_enqueue():
    # Test CLI command execution
    # Verify workflow is enqueued
    # Check database state
    pass
```

### Performance Testing

1. **Load Testing**: Test with multiple concurrent workflows
2. **Scalability**: Verify performance with multiple workers
3. **Memory Usage**: Monitor memory usage with large files
4. **Queue Performance**: Test Redis queue performance under load

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create workflow decorators and registry
2. Implement WorkflowContext and basic job chaining
3. Add database models and migrations
4. Create basic CLI commands

### Phase 2: Job Tracking and API
1. Implement workflow tracking in database
2. Extend job API with workflow endpoints
3. Add comprehensive error handling
4. Create workflow status queries

### Phase 3: Advanced Features
1. Implement fan-out job creation
2. Add workflow recovery mechanisms
3. Optimize file handling and references
4. Add comprehensive testing

### Phase 4: PDF Processing Integration
1. Convert existing document jobs to workflow jobs
2. Define PDF processing workflow
3. Test complete pipeline
4. Performance optimization and monitoring