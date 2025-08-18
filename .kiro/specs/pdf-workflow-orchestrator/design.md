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

```python
# Add to extralit_server/src/extralit_server/contexts/files.py

def download_file_content(client: Minio | LocalFileStorage, document_url: str) -> bytes:
    """
    Download file content from a document URL.

    Args:
        client: Minio or LocalFileStorage client
        document_url: URL in format "/api/v1/file/{bucket_name}/{object_path}"

    Returns:
        File content as bytes
    """
    # Parse URL to get bucket and object path
    if not document_url.startswith("/api/v1/file/"):
        raise ValueError(f"Invalid document URL format: {document_url}")

    url_parts = document_url.replace("/api/v1/file/", "").split("/", 1)
    if len(url_parts) != 2:
        raise ValueError(f"Invalid document URL format: {document_url}")

    bucket_name, object_path = url_parts

    file_response = get_object(client, bucket_name, object_path)
    return file_response.response.read()
```

### Refactoring process_bulk_upload()

The current implementation already handles file mapping correctly by creating a `file_mapping = {file.filename: file for file in files}` dictionary and validating that all referenced files exist. The key changes needed are:

```python
# Current implementation in contexts/imports.py
async def process_bulk_upload(
    bulk_create: DocumentsBulkCreate,
    files: list[UploadFile],
    user_id: str,
) -> DocumentsBulkResponse:
    # Current file mapping logic (KEEP THIS - it works correctly)
    file_mapping = {file.filename: file for file in files} if files else {}

    # Current validation logic (KEEP THIS - it works correctly)
    for doc in bulk_create.documents:
        for filename in doc.associated_files:
            if filename not in file_mapping:
                missing_files.append(filename)

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
    # KEEP existing file mapping and validation logic
    file_mapping = {file.filename: file for file in files} if files else {}
    # ... existing validation logic ...

    for reference, doc in reference_to_doc.items():
        # KEEP existing file processing logic that maps filenames to file objects
        file_data_list = []
        for filename in doc.associated_files:
            file = file_mapping[filename]  # This mapping works correctly
            file_content = await file.read()
            file_data_list.append((filename, file_content))

        # NEW: Upload files to storage immediately using existing file operations
        from extralit_server.contexts.files import get_minio_client, put_document_file, create_bucket

        client = await get_minio_client()
        workspace_name = str(doc.document_create.workspace_id)

        # Ensure workspace bucket exists
        create_bucket(client, workspace_name)

        # NEW: Create document records in database first to get document ID
        async with AsyncSessionLocal() as db:
            document = Document(**doc.document_create.model_dump())
            db.add(document)
            await db.commit()
            await db.refresh(document)

        # Upload files and collect S3 URLs
        s3_urls = []
        for filename, file_content in file_data_list:
            s3_url = put_document_file(
                client,
                workspace_name,
                document.id,
                file_content,
                filename,
                metadata={"reference": reference, "original_filename": filename}
            )
            if s3_url:
                s3_urls.append(s3_url)
            else:
                # File already exists with same hash, get existing URL
                from extralit_server.contexts.files import get_pdf_s3_object_path, get_proxy_document_url
                object_path = get_pdf_s3_object_path(document.id)
                s3_url = get_proxy_document_url(workspace_name, object_path)
                s3_urls.append(s3_url)

        # NEW: Start workflow with document ID and S3 URLs
        workflow_jobs = start_pdf_workflow(
            document_id=document.id,
            reference=reference,
            s3_urls=s3_urls,
            workspace_id=document.workspace_id,
            user_id=user_id
        )

        job_ids[reference] = workflow_jobs['workflow_id']

    return DocumentsBulkResponse(
        job_ids=job_ids,  # Workflow IDs for tracking
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

# NEW: Combined analysis and preprocessing job
from rq.decorators import job
from rq import get_current_job

from extralit_server.database import AsyncSessionLocal

@job(queue='default', timeout=600, result_ttl=3600)
def analysis_and_preprocess_job(document_id: UUID, s3_url: str, reference: str, workspace_id: UUID) -> dict:
    """Analyze PDF structure and content, then preprocess using existing modules."""
    from extralit_server.contexts.document.analysis import PDFOCRLayerDetector
    from extralit_server.contexts.document.margin import PDFAnalyzer
    from extralit_server.contexts.document.preprocessing import PDFPreprocessingSettings, PDFPreprocessor
    from extralit_server.contexts.files import get_minio_client, download_file_content, put_object
    from extralit_server.models.database import Document
    from extralit_server.api.schemas.v1.documents.metadata import DocumentProcessingMetadata

    current_job = get_current_job()
    current_job.meta.update({
        'document_id': str(document_id),
        'reference': reference,
        'workspace_id': str(workspace_id),
        'workflow_step': 'analysis_and_preprocess',
        'started_at': datetime.utcnow().isoformat()
    })
    current_job.save_meta()

    # Download original PDF from storage
    client = get_minio_client()
    pdf_data = download_file_content(client, s3_url)
    filename = s3_url.split('/')[-1]

    # Step 1: Analyze original PDF structure and content
    ocr_detector = PDFOCRLayerDetector()
    has_ocr_text_layer = ocr_detector.has_ocr_text_layer(pdf_data)
    ocr_quality = ocr_detector.analyze_character_quality(pdf_data)

    pdf_analyzer = PDFAnalyzer()
    layout_analysis = pdf_analyzer.analyze_pdf_layout(pdf_data, filename)

    analysis_result = {
        'document_id': str(document_id),
        'has_ocr_text_layer': has_ocr_text_layer,
        'ocr_quality_score': ocr_quality.get('ocr_quality_score', 0.0),
        'layout_analysis': layout_analysis,
        'needs_ocr': not has_ocr_text_layer or ocr_quality.get('ocr_quality_score', 0.0) < 0.7,
        'analysis_metadata': {
            'total_chars': ocr_quality.get('total_chars', 0),
            'ocr_artifacts': ocr_quality.get('ocr_artifacts', 0),
            'suspicious_patterns': ocr_quality.get('suspicious_patterns', 0),
            'ocr_quality_score': ocr_quality.get('ocr_quality_score', 0.0)
        }
    }

    # Step 2: Preprocess PDF (OCRmyPDF for page rotation, overwrites same S3 path)
    settings = PDFPreprocessingSettings(enable_analysis=False)  # Analysis already done
    preprocessor = PDFPreprocessor(settings)
    processing_response = preprocessor.preprocess(pdf_data, filename)

    # OCRmyPDF overwrites the same S3 object path, so we upload back to same location
    workspace_name = str(workspace_id)
    object_path = s3_url.replace(f"/api/v1/file/{workspace_name}/", "")

    put_object(
        client,
        workspace_name,
        object_path,
        processing_response.processed_data,
        len(processing_response.processed_data),
        content_type="application/pdf",
        metadata={"processing_applied": "ocrmypdf_rotation", "original_filename": filename}
    )

    # Combine results
    combined_result = {
        'document_id': str(document_id),
        'analysis_result': analysis_result,
        'preprocessing_result': {
            'processing_time': processing_response.metadata.processing_time,
            'ocr_applied': processing_response.metadata.ocr_applied,
            'preprocessing_metadata': processing_response.metadata.model_dump()
        },
        'needs_ocr': analysis_result['needs_ocr']
    }

    # Store combined results in document.metadata_
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document:
            # Initialize or update document metadata
            if document.metadata_ is None:
                document.metadata_ = DocumentProcessingMetadata(
                    workflow_started_at=datetime.utcnow()
                ).model_dump()

            metadata = DocumentProcessingMetadata(**document.metadata_)
            metadata.update_analysis_results(analysis_result)
            metadata.update_preprocessing_results(combined_result['preprocessing_result'])
            document.metadata_ = metadata.model_dump()
            await db.commit()

    # Store results for dependent jobs
    current_job.meta['needs_ocr'] = analysis_result['needs_ocr']
    current_job.meta['analysis_complete'] = True
    current_job.meta['preprocessing_complete'] = True
    current_job.meta['completed_at'] = datetime.utcnow().isoformat()
    current_job.save_meta()

    return combined_result
    }

    # Store preprocessing results in document.metadata_
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document and document.metadata_:
            metadata = DocumentProcessingMetadata(**document.metadata_)
            metadata.update_preprocessing_results(preprocess_result)
            document.metadata_ = metadata.model_dump()
            await db.commit()

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

### Workflow Orchestrator (Centralized Job Chaining)

```python
def start_pdf_workflow(document_id: UUID, s3_url: str, reference: str, workspace_id: UUID, user_id: UUID) -> dict:
    """Start complete PDF workflow using centralized orchestration with RQ dependencies."""
    from extralit_server.models.database import DocumentWorkflow, Document
    from extralit_server.api.schemas.v1.documents.metadata import DocumentProcessingMetadata

    # Step 1: Initialize document metadata
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document:
            # Initialize document metadata for workflow tracking
            initial_metadata = DocumentProcessingMetadata(
                workflow_started_at=datetime.utcnow(),
                workflow_status="running"
            )
            document.metadata_ = initial_metadata.model_dump()
            await db.commit()

    # Step 2: Create workflow record in database
    workflow = DocumentWorkflow.create(
        document_id=document_id,
        workflow_type="pdf_processing",
        status="queued",
        job_ids={}
    )

    # Step 3: Enqueue combined analysis and preprocessing job
    analysis_preprocess_job = DEFAULT_QUEUE.enqueue(
        'pdf_analysis_and_preprocess_job',
        document_id, s3_url, reference, workspace_id,
        job_id=f"analysis_preprocess_{document_id}",
        meta={'document_id': str(document_id), 'workflow_step': 'analysis_and_preprocess', 'workflow_id': workflow.id}
    )

    # Step 4: Chain dependent jobs using RQ's depends_on
    text_job = DEFAULT_QUEUE.enqueue(
        'pdf_text_extraction_job',
        document_id, s3_url, reference, workspace_id,
        depends_on=[analysis_preprocess_job],
        job_id=f"text_{document_id}",
        meta={'document_id': str(document_id), 'workflow_step': 'text_extraction', 'workflow_id': workflow.id}
    )

    table_job = GPU_QUEUE.enqueue(
        'pdf_table_extraction_job',
        document_id, s3_url, reference, workspace_id,
        depends_on=[analysis_preprocess_job],  # Depends on combined job
        job_id=f"table_{document_id}",
        meta={'document_id': str(document_id), 'workflow_step': 'table_extraction', 'workflow_id': workflow.id}
    )

    embed_job = DEFAULT_QUEUE.enqueue(
        'pdf_embedding_job',
        document_id, reference, workspace_id,
        depends_on=[text_job, table_job],
        job_id=f"embed_{document_id}",
        meta={'document_id': str(document_id), 'workflow_step': 'embedding', 'workflow_id': workflow.id}
    )

    # Step 5: Update workflow with job IDs and metadata
    workflow.job_ids = {
        'analysis_and_preprocess': analysis_preprocess_job.id,
        'text_extraction': text_job.id,
        'table_extraction': table_job.id,
        'embedding': embed_job.id
    }
    workflow.status = "running"
    workflow.save()

    # Step 6: Update document metadata with workflow ID
    async with AsyncSessionLocal() as db:
        document = await db.get(Document, document_id)
        if document and document.metadata_:
            metadata = DocumentProcessingMetadata(**document.metadata_)
            metadata.workflow_id = workflow.id
            document.metadata_ = metadata.model_dump()
            await db.commit()

    return {
        'workflow_id': workflow.id,
        'job_ids': workflow.job_ids
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

### Efficient Job Querying Using Database Index

```python
def get_jobs_for_document(db: AsyncSession, document_id: UUID) -> list[dict]:
    """Get jobs for document using database index (much faster than registry scanning)."""
    workflow = DocumentWorkflow.get_by_document_id(db, document_id)
    if not workflow:
        return []

    jobs = []
    for step_name, job_id in workflow.job_ids.items():
        try:
            job = Job.fetch(job_id, connection=REDIS_CONNECTION)  # Single job fetch
            job_info = {
                'job_id': job_id,
                'workflow_step': step_name,
                'status': job.get_status(),
                'document_id': str(document_id),
                'workflow_id': workflow.id,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                'error': str(job.exc_info) if job.is_failed else None,
                'result': job.result if job.is_finished else None
            }
            jobs.append(job_info)
        except Exception as e:
            # Job might have expired, but we still have the workflow record
            jobs.append({
                'job_id': job_id,
                'workflow_step': step_name,
                'status': 'expired',
                'document_id': str(document_id),
                'workflow_id': workflow.id,
                'error': f'Job expired or not found: {e}'
            })

    return jobs

def get_jobs_by_reference(db: AsyncSession, reference: str) -> list[dict]:
    """Get jobs by reference using document lookup."""
    # First find documents with this reference
    documents = db.query(Document).filter(Document.reference == reference).all()

    all_jobs = []
    for doc in documents:
        jobs = get_jobs_for_document(db, doc.id)
        all_jobs.extend(jobs)

    return sorted(all_jobs, key=lambda x: x.get('started_at', ''))

def get_workflow_status(db: AsyncSession, document_id: UUID) -> dict:
    """Get complete workflow status for a document."""
    workflow = DocumentWorkflow.get_by_document_id(db, document_id)
    if not workflow:
        return {'status': 'not_found', 'jobs': []}

    jobs = get_jobs_for_document(db, document_id)

    # Calculate progress
    total_steps = len(workflow.job_ids)
    completed_steps = len([j for j in jobs if j['status'] == 'finished'])
    progress = completed_steps / total_steps if total_steps > 0 else 0

    return {
        'workflow_id': workflow.id,
        'document_id': document_id,
        'status': workflow.status,
        'progress': progress,
        'total_jobs': total_steps,
        'completed_jobs': completed_steps,
        'failed_jobs': len([j for j in jobs if j['status'] == 'failed']),
        'jobs': jobs,
        'created_at': workflow.created_at.isoformat(),
        'updated_at': workflow.updated_at.isoformat()
    }
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
# extralit_server/src/extralit_server/api/schemas/v1/documents/metadata.py
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
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
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