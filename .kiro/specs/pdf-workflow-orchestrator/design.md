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
POST /documents/bulk → process_bulk_upload() → Upload files to S3 + Create DB records → analysis_and_preprocess_job(document_id, s3_url) → conditional_ocr_job (if needed) → text_extraction_job + table_extraction_job (parallel) → embedding_job
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


## CLI Commands (Using Typer)

```python
# Add to existing CLI using typer
import typer
from extralit_server.jobs.pdf import start_pdf_workflow, get_jobs_for_document

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

class TextExtractionMetadata(BaseModel):
    """Text extraction job results."""
    extracted_text_length: int = Field(..., description="Length of extracted text")
    extraction_method: str = Field(..., description="Method used for extraction")
    text_extraction_completed_at: datetime = Field(..., description="When text extraction was completed")

class TableExtractionMetadata(BaseModel):
    """Table extraction job results."""
    tables_found: int = Field(..., description="Number of tables extracted")
    extraction_method: str = Field(..., description="Method used for table extraction")
    table_extraction_completed_at: datetime = Field(..., description="When table extraction was completed")

class EmbeddingMetadata(BaseModel):
    """Embedding job results."""
    embedding_model: str = Field(..., description="Model used for embeddings")
    embedding_dimensions: int = Field(..., description="Dimensionality of embeddings")
    embedding_completed_at: datetime = Field(..., description="When embedding was completed")

class DocumentProcessingMetadata(BaseModel):
    """Complete document processing metadata stored in documents.metadata_."""
    workflow_id: Optional[str] = Field(None, description="Workflow ID for tracking")
    analysis_metadata: Optional[AnalysisMetadata] = Field(None, description="Analysis results")
    preprocessing_metadata: Optional[PreprocessingMetadata] = Field(None, description="Preprocessing results")
    text_extraction_metadata: Optional[TextExtractionMetadata] = Field(None, description="Text extraction results")
    table_extraction_metadata: Optional[TableExtractionMetadata] = Field(None, description="Table extraction results")
    embedding_metadata: Optional[EmbeddingMetadata] = Field(None, description="Embedding results")
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
            self.text_extraction_metadata is not None,
            self.table_extraction_metadata is not None,
            self.embedding_metadata is not None
        ])
```

### Database Model for Workflow Tracking

```python
# extralit_server/src/extralit_server/models/database.py (add to existing models)
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime

class DocumentWorkflow(Base):
    """Track document processing workflows for efficient job querying."""
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    workflow_type: Mapped[str] = mapped_column(String(50), default="pdf_processing")
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, running, completed, failed
    job_ids: Mapped[dict] = mapped_column(JSON, default=dict)  # Map of step_name -> job_id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="workflows")

    @classmethod
    def get_by_document_id(cls, db: AsyncSession, document_id: UUID) -> Optional["DocumentWorkflow"]:
        """Get workflow by document ID."""
        return db.query(cls).filter(cls.document_id == document_id).first()

    def update_job_status(self, db: AsyncSession, step_name: str, job_id: str, status: str):
        """Update individual job status and overall workflow status."""
        if step_name not in self.job_ids:
            self.job_ids[step_name] = job_id

        # Update overall workflow status based on job statuses
        if status == "failed":
            self.status = "failed"
        elif all(self._get_job_status(job_id) == "finished" for job_id in self.job_ids.values()):
            self.status = "completed"
        elif any(self._get_job_status(job_id) in ["started", "queued"] for job_id in self.job_ids.values()):
            self.status = "running"

        self.updated_at = datetime.utcnow()
        db.commit()

    def _get_job_status(self, job_id: str) -> str:
        """Helper to get job status from RQ."""
        try:
            job = Job.fetch(job_id, connection=REDIS_CONNECTION)
            return job.get_status()
        except:
            return "unknown"
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

### Integration with Existing Code Structure

The design leverages existing modules:

1. **Analysis Job**: Uses `PDFOCRLayerDetector` from `analysis.py` and `PDFAnalyzer` from `margin.py`
2. **Preprocess Job**: Uses `PDFPreprocessor` from `preprocessing.py` with analysis disabled
3. **File Handling**: Uses existing `download_file_from_s3()` and `upload_file_to_s3()` from `files.py`
4. **Schemas**: Extends existing `PDFMetadata` from `preprocessing.py`

This approach minimizes code duplication and leverages the existing, well-tested PDF processing logic.

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
- **Incremental Refactoring**: Modify existing code gradually
- **Simple Recovery**: Use RQ registries and metadata for workflow state