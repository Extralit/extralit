# Design Document

## Overview

The Papers Library Importer feature enables researchers to import their existing reference libraries from .bib files and PDF folders into Extralit workspaces. The system leverages the existing document upload endpoint (`POST /documents`) and job queue system to process bibliographic metadata from .bib files, match PDF files to references, and provide a user-friendly interface for reviewing and confirming imports before executing bulk operations.

The design follows Extralit's existing patterns: context-based backend architecture, FastAPI endpoints with proper authorization, Vue.js frontend components, and the existing RQ-based asynchronous job processing system for bulk operations.

## Architecture

### High-Level Flow

1. **Upload Phase**: User uploads .bib file and PDF folder through frontend interface
2. **Processing Phase**: Backend parses .bib entries, matches PDFs, and analyzes import status
3. **Preview Phase**: Frontend displays import preview with add/update/skip/failed status for each document
4. **Import Phase**: User confirms import, backend creates individual document upload jobs using existing job queue
5. **Results Phase**: Frontend tracks job progress and displays import results

### Component Interaction

```mermaid
graph TD
    A[Frontend Upload Component] --> B[Backend Import API]
    B --> C[BibTeX Parser Service]
    B --> D[PDF Matching Service]
    C --> E[Import Analysis Service]
    D --> E
    E --> F[Import Preview Response]
    F --> G[Frontend Preview Component]
    G --> H[User Confirmation]
    H --> I[Bulk Document Upload Endpoint]
    I --> J[RQ Job Queue System]
    J --> K[Individual Document Upload Jobs]
    K --> L[Existing File Storage Service]
    K --> M[Existing Database Updates]
    J --> N[Job Status Tracking via /jobs/{job_id}]
    L --> O[S3 Storage]
    M --> O
    N --> P[Import Results]
    O --> P
```

## Components and Interfaces

### Backend Components

#### 1. Import API Handler (`argilla-server/src/argilla_server/api/handlers/v1/imports.py`)

**Endpoints:**
- `POST /api/v1/imports/analyze` - Upload and analyze .bib + PDFs, returns analysis with temporary storage
- `POST /api/v1/imports/execute` - Execute confirmed import using bulk document upload endpoint

**Key Functions:**
```python
async def analyze_import(
    bib_file: UploadFile,
    pdf_files: List[UploadFile],
    collection_tag: str,
    workspace_id: UUID,
    current_user: User
) -> ImportAnalysisResponse

async def execute_import(
    import_request: ImportExecuteRequest,
    current_user: User
) -> List[str]  # Returns list of job_ids for tracking
```

#### 2. Bulk Document Upload Handler (`argilla-server/src/argilla_server/api/handlers/v1/documents.py`)

**New Endpoint:**
- `POST /documents/bulk` - Asynchronous bulk document upload with job queue

**Multi-File Upload Support:**
```python
async def bulk_upload_documents(
    *,
    documents_metadata: str = Form(...),  # JSON string of List[DocumentCreate]
    files: List[UploadFile] = File(...),  # Multiple PDF files
    current_user: User = Security(auth.get_current_user)
) -> BulkUploadResponse
```

**Request Structure:**
- Uses `multipart/form-data` to support multiple file uploads
- `documents_metadata`: JSON string containing document metadata and file associations
- `files`: List of PDF files uploaded simultaneously
- File matching handled by filename-to-reference-key mapping in metadata

**Response:**
```python
class BulkUploadResponse(BaseModel):
    job_ids: List[str]  # List of job IDs for tracking individual uploads
    total_documents: int
    upload_session_id: str  # For tracking overall bulk upload progress
```

**Benefits:**
- **Multi-file support**: Handles multiple PDF uploads in single request using FastAPI's `List[UploadFile]`
- **Reliable file association**: Metadata includes filename-to-reference mapping from BibTeX analysis
- **Asynchronous processing**: Each document becomes individual job for parallel processing
- **Progress tracking**: Both individual job status and overall session progress
- **Fault tolerance**: Failed individual uploads don't affect others

#### 3. Import Context (`argilla-server/src/argilla_server/contexts/imports.py`)

**Core Services:**
- `parse_bibtex_file()` - Parse .bib file and extract metadata
- `match_pdfs_to_references()` - Match PDF files to bibliographic entries
- `analyze_import_status()` - Determine add/update/skip/failed status by checking existing documents
- `prepare_bulk_upload_data()` - Prepare DocumentCreate objects and file data for bulk upload endpoint

#### 3. BibTeX Parser Service

**Dependencies:** `bibtexparser` Python package
**Functions:**
- Parse .bib file entries
- Extract metadata (title, authors, year, DOI, PMID, reference key)
- Handle malformed entries gracefully
- Sanitize input for security

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
- Collection tag input
- Upload progress indicators
- File validation

**Dependencies:** `vue-dropzone` or similar for file uploads

#### 3. Preview Component (`argilla-frontend/components/features/import/ImportPreview.vue`)

**Features:**
- Tabular display of documents to import
- Status indicators (add/update/skip/failed)
- Document metadata display (title, authors, year)
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
    bib_file: UploadFile
    pdf_files: List[UploadFile]
    collection_tag: str
    workspace_id: UUID
```

#### Import Analysis Response
```python
class ImportAnalysisResponse(BaseModel):
    import_id: UUID
    documents: List[ImportDocumentPreview]
    summary: ImportSummary

class ImportDocumentPreview(BaseModel):
    reference_key: str
    title: str
    authors: List[str]
    year: Optional[int]
    doi: Optional[str]
    pmid: Optional[str]
    files: List[ImportFileInfo]
    status: ImportStatus  # add, update, skip, failed
    existing_document_id: Optional[UUID]

class ImportFileInfo(BaseModel):
    filename: str
    size: int
    matched: bool

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