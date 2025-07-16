# Design Document

## Overview

The Papers Library Importer feature enables researchers to import their existing reference libraries from .bib files and PDF folders into Extralit workspaces. The system leverages the existing document upload endpoint (`POST /documents`) and job queue system to process bibliographic metadata from .bib files, match PDF files to references, and provide a user-friendly interface for reviewing and confirming imports before executing bulk operations.

The design follows Extralit's existing patterns: context-based backend architecture, FastAPI endpoints with proper authorization, Vue.js frontend components, and the existing RQ-based asynchronous job processing system for bulk operations.

## Architecture

### High-Level Flow

1. **Frontend Processing Phase**: User uploads .bib file and PDFs to frontend, which parses BibTeX entries and matches files to references
2. **Analysis Phase**: Frontend sends file metadata (not file contents) to backend for add/update/skip status analysis
3. **Preview Phase**: Frontend displays import preview with status for each document based on server analysis
4. **Bulk Upload Phase**: User confirms import, frontend sends paginated requests to bulk upload endpoint with actual file contents
5. **Progress Tracking Phase**: Frontend polls job status endpoints to track upload progress

### Component Interaction

```mermaid
graph TD
    A[Frontend Upload Component] --> B[Frontend BibTeX Parser]
    A --> C[Frontend File Matcher]
    B --> D[File Metadata Analysis Request]
    C --> D
    D --> E[Backend Import Analysis API]
    E --> F[Existing Document Check]
    F --> G[Import Analysis Response]
    G --> H[Frontend Preview Component]
    H --> I[User Confirmation]
    I --> J[Paginated Bulk Upload Requests]
    J --> K[Backend Bulk Upload Endpoint]
    K --> L[RQ Job Queue System]
    L --> M[Individual Document Upload Jobs]
    M --> N[Existing File Storage & DB Logic]
    L --> O[Job Status Tracking via /jobs/{job_id}]
    N --> P[S3 Storage & Database]
    O --> Q[Frontend Progress Tracking]
    P --> Q
```

## Components and Interfaces

### Backend Components

#### 1. Import Analysis API Handler (`argilla-server/src/argilla_server/api/handlers/v1/imports.py`)

**Endpoints:**
- `POST /api/v1/imports/analyze` - Analyze file metadata to determine add/update/skip status

**Key Functions:**
```python
async def analyze_import(
    analysis_request: ImportAnalysisRequest,
    current_user: User
) -> ImportAnalysisResponse
```

**Functionality:**
- Receives file metadata (not file contents) from frontend
- Checks existing documents by reference, DOI, PMID to determine status
- Compares file sizes to determine if updates are needed
- Returns status analysis for frontend preview

#### 2. Bulk Document Upload Handler (`argilla-server/src/argilla_server/api/handlers/v1/documents.py`)

**New Endpoint:**
- `POST /documents/bulk` - Asynchronous bulk document upload with job queue

**Multi-File Upload Support:**
```python
async def bulk_upload_documents(
    *,
    documents_metadata: str = Form(...),  # JSON string of BulkUploadMetadata
    files: List[UploadFile] = File(...),  # Multiple PDF files
    current_user: User = Security(auth.get_current_user)
) -> BulkUploadResponse
```

#### 3. Import Context (`argilla-server/src/argilla_server/contexts/imports.py`)

**Core Services:**
- `analyze_import_status()` - Uses existing `check_existing_document()` function from documents handler to determine add/update/skip status
- `compare_file_sizes()` - Compare existing file sizes with new files to determine if updates are needed
- `validate_document_metadata()` - Validate DocumentCreate objects from frontend

#### 4. Document Upload Job (`argilla-server/src/argilla_server/jobs/document_jobs.py`)

**Async Job Functions:**
```python
@job(DEFAULT_QUEUE, timeout=JOB_TIMEOUT_DISABLED, retry=Retry(max=3))
async def upload_document_job(
    document_data: DocumentCreate,
    file_data: bytes,
    user_id: UUID
) -> dict  # Returns upload result with document_id or error
```

**Job Implementation:**
- Reuses existing document upload logic from `POST /documents` endpoint
- Leverages existing document deduplication logic (pmid, doi, reference matching)
- Handles file storage to S3 and database record creation
- Returns success/failure status with detailed error information
- Automatic retry on transient failures (network, storage issues)

### Frontend Components

#### 1. Import Page (`argilla-frontend/pages/workspace/_id/import.vue`)

**Main import workflow page with:**
- File upload interface
- Import preview display
- Progress tracking
- Results summary

#### 2. Upload Component (`argilla-frontend/components/features/import/ImportUpload.vue`)

**Features:**
- Drag-and-drop .bib file upload
- Folder/multiple PDF file upload
- **Frontend BibTeX parsing** using JavaScript BibTeX parser library
- **Frontend file-to-reference matching** by filename patterns
- Collection tag input
- File validation and metadata extraction
- Sends file metadata (not contents) to backend for analysis

**Dependencies:**
- `vue-dropzone` or similar for file uploads
- JavaScript BibTeX parser library (e.g., `bibtex-parse-js` or `@retorquere/bibtex-parser`)

#### 3. Preview Component (`argilla-frontend/components/features/import/ImportPreview.vue`)

**Features:**
- Tabular display of documents to import
- Status indicators (add/update/skip/failed)
- Document metadata display (title, authors, venue, year)
- Associated files listing
- Action selection (allow user to change add/update/skip)
- Bulk confirmation interface

#### 4. Progress Component (`argilla-frontend/components/features/import/ImportProgress.vue`)

**Features:**
- Real-time progress tracking
- Document-by-document status updates
- Error reporting
- Cancellation support

#### 5. Results Component (`argilla-frontend/components/features/import/ImportResults.vue`)

**Features:**
- Import summary statistics
- Success/failure breakdown
- Error details for failed imports
- Navigation to workspace documents

### API Schemas

#### Import Analysis Request
```python
class ImportAnalysisRequest(BaseModel):
    workspace_id: UUID
    documents: Dict[str, FileMetadataInfo]  # reference_key -> file metadata

class FileMetadataInfo(BaseModel):
    document_create: DocumentCreate  # Contains reference, doi, pmid, etc.
    title: str  # For display
    authors: List[str]  # For display
    venue: Optional[str]  # Journal, publisher, or institution from BibTeX
    year: Optional[int]  # For display
    associated_files: List[FileInfo]  # PDF file metadata (not contents)

class FileInfo(BaseModel):
    filename: str
    size: int  # File size in bytes for comparison
```

#### Import Analysis Response
```python
class ImportAnalysisResponse(BaseModel):
    documents: Dict[str, ImportDocumentInfo]  # reference_key -> document info
    summary: ImportSummary

class ImportDocumentInfo(BaseModel):
    document_create: DocumentCreate  # Reuse existing schema
    title: str  # For display only
    authors: List[str]  # For display only
    venue: Optional[str]  # Journal, publisher, or institution from BibTeX
    year: Optional[int]  # For display only
    associated_files: List[str]  # PDF filenames matched to this reference
    status: ImportStatus  # add, update, skip, failed
    existing_document_id: Optional[UUID]

class ImportSummary(BaseModel):
    total_documents: int
    add_count: int
    update_count: int
    skip_count: int
    failed_count: int
```

#### Import Execute Request
```python
class ImportExecuteRequest(BaseModel):
    import_id: UUID
    document_actions: Dict[str, ImportAction]  # reference_key -> action

class ImportAction(BaseModel):
    action: str  # add, update, skip
    files_to_import: List[str]
```

#### Bulk Upload Request/Response
```python
# Multipart form data structure (paginated by 20-50 PDFs):
# - documents_metadata: str (JSON string of BulkUploadMetadata)
# - files: List[UploadFile] (Multiple PDF files, max 20-50 per request)

class BulkUploadMetadata(BaseModel):
    documents: List[BulkDocumentInfo]  # List of documents to upload

class BulkDocumentInfo(BaseModel):
    reference_key: str  # BibTeX reference key for job tracking
    document_create: DocumentCreate  # Each document has one associated PDF file
    associated_file: str  # Single PDF filename (one file per DocumentCreate)

class BulkUploadResponse(BaseModel):
    job_ids: Dict[str, str]  # reference_key -> job_id mapping for frontend tracking
    total_documents: int
    failed_validations: List[str]  # Files that failed validation
```

**Pagination Strategy:**
- Frontend sends multiple paginated requests (20-50 PDFs each) to avoid large payload failures
- Each `DocumentCreate` is associated with exactly one PDF file
- Multiple documents may share the same BibTeX reference but have different files
- Response includes `job_ids` indexed by reference key for easy frontend tracking

## Data Models

### Document Field Mapping
The import process maps BibTeX entries to existing Document model fields:

```python
# Existing Document model fields used:
- reference: str  # BibTeX reference key (e.g., "Hawley2003a")
- file_name: str  # Original PDF filename
- doi: str       # DOI from BibTeX entry
- pmid: str      # PMID from BibTeX entry
- url: str       # S3 URL after upload
- workspace_id: UUID  # Target workspace
```

### BibTeX Entry Processing
- **Reference Key**: Maps to `Document.reference` field for deduplication
- **Title**: Used for display in preview, not stored in Document model
- **Authors**: Used for display in preview, not stored in Document model
- **Year**: Used for display in preview, not stored in Document model
- **DOI/PMID**: Maps to `Document.doi` and `Document.pmid` fields
- **File Matching**: Associates PDF files with reference keys for upload

### PDF-to-Reference Matching Logic
1. **Exact Match**: PDF filename matches reference key exactly
2. **Partial Match**: PDF filename contains reference key
3. **Fuzzy Match**: Use string similarity for close matches
4. **Manual Association**: Allow user to manually associate files

## Error Handling

### BibTeX Parsing Errors
- Malformed entries: Skip and report specific line/entry errors
- Encoding issues: Attempt multiple encodings, report failures
- Duplicate reference keys: Append suffix or prompt user resolution

### PDF Processing Errors
- Corrupted files: Skip and report file-specific errors
- Size limits: Enforce file size limits, report oversized files
- Format validation: Ensure files are valid PDFs

### Import Execution Errors
- Storage failures: Retry with exponential backoff
- Database conflicts: Handle race conditions gracefully
- Partial failures: Continue processing, report individual failures

### User Experience
- Clear error messages with actionable guidance
- Ability to retry failed operations
- Progress preservation across browser sessions

## Testing Strategy

### Unit Tests
- BibTeX parser with various .bib file formats
- PDF matching algorithms with different filename patterns
- Import status analysis logic
- Database operations and model validations

### Integration Tests
- End-to-end import workflow
- File upload and processing pipeline
- Async job execution and status tracking
- Frontend-backend API integration

### Performance Tests
- Large .bib file processing (1000+ entries)
- Bulk PDF upload handling
- Concurrent import operations
- Database performance with large document sets

### Security Tests
- File upload validation and sanitization
- BibTeX input sanitization
- Authorization checks for workspace access
- S3 storage security and access controls

## Implementation Considerations

### File Upload Handling
- Use multipart form uploads for large files
- Implement chunked upload for very large PDF collections
- Temporary storage for processing before final S3 upload
- Cleanup of temporary files after processing

### Performance Optimization
- Stream processing for large .bib files
- Parallel PDF processing where possible
- Database batch operations for bulk inserts
- Caching of analysis results during preview phase

### User Experience
- Real-time progress updates via WebSocket or polling
- Ability to pause/resume import operations
- Preview before commit to avoid unwanted changes
- Clear visual feedback for each import stage

### Scalability
- Queue-based processing for large imports
- Rate limiting to prevent system overload
- Horizontal scaling support for job processing
- Monitoring and alerting for import operations