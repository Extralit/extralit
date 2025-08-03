# Design Document

## Overview

The Papers Library Importer feature enables researchers to import their existing reference libraries from .bib files and PDF folders into Extralit workspaces. The system leverages the existing document upload endpoint (`POST /documents`) and job queue system to process bibliographic metadata from .bib files, match PDF files to references, and provide a user-friendly interface for reviewing and confirming imports before executing bulk operations.

**Generalized Tabular Import Support**: The import system is designed to handle tabular data beyond just BibTeX files. The core functionality supports CSV imports and other structured data formats by storing imported data as dataframes with schema information. This enables future expansion to support various research data import formats while maintaining consistent processing workflows.

The design follows Extralit's existing patterns: context-based backend architecture, FastAPI endpoints with proper authorization, Vue.js frontend components, and the existing RQ-based asynchronous job processing system for bulk operations.

## Architecture

### High-Level Flow

1. **Frontend Processing Phase**: User uploads .bib file and PDFs to frontend, which parses BibTeX entries into generic dataframe format and matches files to references
2. **Analysis Phase**: Frontend sends file metadata (not file contents) to backend for add/update/skip status analysis
3. **Preview Phase**: Frontend displays import preview with status for each document based on server analysis
4. **Bulk Upload Phase**: User confirms import, frontend sends paginated requests to bulk upload endpoint with actual file contents
5. **Progress Tracking Phase**: Frontend polls job status endpoints to track upload progress
6. **Import History Phase**: After all bulk upload batches complete, frontend sends parsed dataframe data to POST `/import/history` endpoint to store complete import record

### Component Interaction

```mermaid
graph TD
    A[Frontend Upload Component] --> B[Frontend BibTeX Parser]
    A --> C[Frontend File Matcher]
    B --> D[File Metadata Analysis Request]
    B --> E[Generic Dataframe Conversion]
    C --> D
    D --> F[Backend Import Analysis API]
    F --> G[Existing Document Check]
    G --> H[Import Analysis Response]
    H --> I[Frontend Preview Component]
    I --> J[User Confirmation]
    J --> K[Paginated Bulk Upload Requests]
    K --> L[Backend Bulk Upload Endpoint]
    L --> M[RQ Job Queue System]
    M --> N[Individual Document Upload Jobs]
    N --> O[Existing File Storage & DB Logic]
    M --> P[Job Status Tracking via /jobs/{job_id}]
    O --> Q[S3 Storage & Database]
    P --> R[Frontend Progress Tracking]
    Q --> R
    R --> S[All Batches Complete]
    S --> T[POST /import/history with Dataframe]
    E --> T
    T --> U[Import History Storage]
```

## Components and Interfaces

### Backend Components

#### 1. Import Analysis API Handler (`argilla-server/src/argilla_server/api/handlers/v1/imports.py`)

**Endpoints:**
- `POST /api/v1/imports/analyze` - Analyze file metadata to determine add/update/skip status
- `POST /api/v1/imports/history` - Store import history with generic dataframe data after bulk upload completion

**Key Functions:**
```python
async def analyze_import(
    analysis_request: ImportAnalysisRequest,
    current_user: User
) -> ImportAnalysisResponse
```

**Functionality:**
- Receives file metadata (not file contents) from frontend
- Only raises exceptions for ill-formed analysis_request, not for ill-formed documents
- Checks existing documents by reference, DOI, PMID to determine status (add/update/skip/failed)
- Compares file sizes to determine if updates are needed
- Returns status analysis for frontend preview without blocking on document validation errors

#### 2. Bulk Document Upload Handler (`argilla-server/src/argilla_server/api/handlers/v1/documents.py`)

**New Endpoint:**
- `POST /documents/bulk` - Asynchronous bulk document upload with job queue

**Multi-File Upload Support:**
```python
async def bulk_upload_documents(
    *,
    documents_metadata: str = Form(...),  # JSON string of DocumentsBulkCreate
    files: List[UploadFile] = File(...),  # Multiple PDF files
    current_user: User = Security(auth.get_current_user)
) -> DocumentsBulkResponse
```

**Job Processing Strategy:**
- Each reference creates one job that processes all associated files for that reference
- Job handles multiple file uploads and creates separate document records for each file
- All files for a reference share the same bibliographic metadata but have unique file paths

#### 3. Import Context (`argilla-server/src/argilla_server/contexts/imports.py`)

**Core Services:**
- `analyze_import_status()` - Uses existing `check_existing_document()` function from documents handler to determine add/update/skip status
- `validate_document_metadata()` - Validate DocumentMetadata objects (not just DocumentCreate) from frontend

#### 4. Document Upload Job (`argilla-server/src/argilla_server/jobs/document_jobs.py`)

**Async Job Functions:**
```python
@job(DEFAULT_QUEUE, timeout=JOB_TIMEOUT_DISABLED, retry=Retry(max=3))
async def upload_reference_documents_job(
    reference: str,
    document_data: DocumentCreate,
    file_data_list: List[Tuple[str, bytes]],  # List of (filename, file_data) tuples
    user_id: UUID
) -> dict  # Returns upload results with document_ids or errors for each file
```

**Job Implementation:**
- Processes multiple files for a single reference in one job
- Creates separate document records for each file while maintaining reference relationship
- Reuses existing document upload logic from `POST /documents` endpoint
- Leverages existing document deduplication logic (pmid, doi, reference matching)
- Handles file storage to S3 and database record creation for each file
- Returns success/failure status with detailed error information for each file
- Automatic retry on transient failures (network, storage issues)
- Maintains transaction consistency across multiple file uploads per reference

### Frontend Components

**Architecture Pattern:**
- **Backend API Types**: Located in `argilla-frontend/v1/domain/entities/import/ImportAnalysis.ts` - contains data structures that map directly to backend API schemas (ImportAnalysisRequest, ImportAnalysisResponse, DocumentImportAnalysis, etc.)
- **Frontend Component Types**: Located in `argilla-frontend/components/features/import/types.ts` - contains UI-specific types (AnalysisTableRow, TableColumn, ImportConfirmationData, etc.) and re-exports backend types for convenience
- **Use Cases**: Located in `argilla-frontend/v1/domain/usecases/get-import-analysis-use-case.ts` - handles API communication with ImportAnalysisUseCase class for POST /api/v1/imports/analyze requests

Note to reuse existing styles in argilla-frontend/assets/scss/base/base.scss, argilla-frontend/assets/scss/abstract/variables/_variables.scss and existing components in `components/base` where possible to keep similar the design system and code reuse and best practices.

- `argilla-frontend/components/base`:
    base-action-tooltip, base-badge, base-banner, base-brand-icon, base-breadcrumbs, base-button, base-card, base-checkbox, base-code, base-collpasable-panel, base-date, base-documentation-viewer, base-dropdown, base-feedback, base-icon, base-input, base-loading, base-modal, base-pdf-viewer, base-progress, base-radio-button, base-range, base-render-html, base-render-markdown, base-render-table, base-resizable, base-scroll, base-search-bar, base-separator, base-shapes, base-slider, base-spinner, base-switch, base-tabs, base-tag, base-toast, base-tooltip, base-topbar-brand


#### 1. Home Page Integration (`argilla-frontend/pages/index.vue`)

**Import Documents Button:**
- Add "Import Documents" button above existing ImportFromHub and ImportFromPython components
- Button opens full-page modal for import workflow
- Positioned prominently in the import section of the home page

**Workspace Selection Integration:**
- Modify WorkspacesFilter component to support single workspace selection instead of multi-select
- Pass selected workspace ID to ImportModal component for import analysis
- Ensure workspace context is maintained throughout the import workflow

#### 2. FlowModal Base Component (`argilla-frontend/components/base/base-flow-modal/BaseFlowModal.vue`)

**New full-screen modal component designed for multi-step workflows:**

**Design Principles:**
- Full-screen overlay that cannot be closed by clicking outside (prevents accidental data loss)
- Built-in step navigation with progress indicator
- Consistent header with title and close button (with confirmation if needed)
- Flexible content area that adapts to different step requirements
- Built-in navigation controls (Previous, Next, Cancel, Finish)
- Support for step validation before allowing navigation
- Responsive design that works on all screen sizes

**Key Features:**
- **Step Management**: Automatic step tracking with progress visualization
- **Navigation Control**: Configurable navigation buttons with validation hooks
- **Data Persistence**: Maintains step data across navigation
- **Confirmation Dialogs**: Built-in confirmation for destructive actions (close, cancel)
- **Accessibility**: Full keyboard navigation and screen reader support
- **Theming**: Consistent with existing design system

**Props Interface:**
```typescript
interface FlowModalProps {
  visible: boolean;
  title: string;
  steps: Array<{
    id: string;
    title: string;
    component: string;
    optional?: boolean;
  }>;
  currentStep: number;
  canGoBack?: boolean;
  canGoNext?: boolean;
  canClose?: boolean;
  confirmClose?: boolean;
  loading?: boolean;
}
```

**Events:**
- `@step-change` - Emitted when user navigates between steps
- `@close` - Emitted when user closes the modal
- `@cancel` - Emitted when user cancels the workflow
- `@complete` - Emitted when user completes the workflow
- `@validate-step` - Emitted to validate current step before navigation

**Styling:**
- Uses existing SCSS variables and design tokens
- Full-screen overlay with proper z-index management
- Consistent spacing and typography with the design system
- Smooth transitions between steps
- Loading states and disabled button styling

#### 3. Import Modal Workflow (`argilla-frontend/components/features/import/ImportModal.vue`)

**Full-page modal using new BaseFlowModal component with multi-step workflow:**
- Step 1: Upload Bibliography File (.bib file upload)
- Step 2: Upload Full-Text PDFs (multiple PDF file upload)
- Step 3: Import Analysis & Selection (table with toggle functionality)
- Step 4: Batch Upload Progress (live progress tracking)
- Step 5: Import Summary & History (results and navigation)

**Workspace Context:**
- Receives selected workspace ID as prop from home page
- Passes workspace ID to ImportAnalysisTable for backend analysis requests
- Maintains workspace context throughout the import workflow

#### 3. Upload Steps Components

**Step 1: Bibliography Upload (`argilla-frontend/components/features/import/ImportBibUpload.vue`)**
- Single .bib file upload with drag-and-drop or file picker
- Support for ";"-separated values (especially the `file` attribute in zotero_export.bib)
- Parsing preview of dataframe columns parsed from the .bib file,
- Display upload status and reference count

**Step 2: PDF Upload (`argilla-frontend/components/features/import/ImportPdfUpload.vue`)**
- Multiple PDF file upload with drag-and-drop or folder selection
- File path matching preview with bibliography entries
- Upload progress and file validation
- Summary status showing matched/unmatched files

**Dependencies:**
- `vue-dropzone` or similar for file uploads
- JavaScript BibTeX parser library (e.g., `bibtex-parse-js` or `@retorquere/bibtex-parser`)

Example BibTeX files:

```zotero_export.bib
@misc{lal_decoding_2024,
	title = {Decoding sequence determinants of gene expression in diverse cellular and disease states},
	copyright = {http://creativecommons.org/licenses/by-nc/4.0/},
	url = {http://biorxiv.org/lookup/doi/10.1101/2024.10.09.617507},
	doi = {10.1101/2024.10.09.617507},
	abstract = {...},
	language = {en},
	urldate = {2025-04-23},
	publisher = {Genomics},
	author = {Lal, Avantika and Karollus, Alexander and Gunsalus, Laura and Garfield, David and Nair, Surag and Tseng, Alex M and Gordon, M Grace and Blischak, John D and Van De Geijn, Bryce and Bhangale, Tushar and Collier, Jenna L and Diamant, Nathaniel and Biancalani, Tommaso and Corrada Bravo, Hector and Scalia, Gabriele and Eraslan, Gokcen},
	month = oct,
	year = {2024},
	file = {PDF:files/2/Lal et al. - 2024 - Decoding sequence determinants of gene expression in diverse cellular and disease states.pdf:application/pdf},
}

@article{linder_predicting_2025,
	title = {Predicting {RNA}-seq coverage from {DNA} sequence as a unifying model of gene regulation},
	volume = {57},
	issn = {1061-4036, 1546-1718},
	url = {https://www.nature.com/articles/s41588-024-02053-6},
	doi = {10.1038/s41588-024-02053-6},
    abstract = {...},
	language = {en},
	number = {4},
	urldate = {2025-04-23},
	journal = {Nature Genetics},
	author = {Linder, Johannes and Srivastava, Divyanshi and Yuan, Han and Agarwal, Vikram and Kelley, David R.},
	month = apr,
	year = {2025},
	pages = {949--961},
	file = {PDF:files/4/Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf:application/pdf;Suppl. Material:files/3/Linder et al. - 2025 - Predicting RNA-seq coverage from DNA sequence as a unifying model of gene regulation.pdf:application/pdf},
}
```

```mendeley_export.bib
@article{Hawley2003a,
   author = {William A Hawley and Penelope A Phillips-Howard and Feiko O ter  Kuile and Dianne J Terlouw and John M Vulule and Maurice Ombok and Bernard L Nahlen and John E Gimnig and Simon K Kariuki and Margarette S Kolczak and Allen W Hightower},
   city = {Division of Parasitic Diseases, National Center for Infectious Diseases, Centers for Disease Control and Prevention, Atlanta, Georgia 30341, USA.},
   issue = {4 Suppl},
   abstract = {...},
   journal = {The American Journal of Tropical Medicine and Hygiene},
   keywords = {malaria},
   month = {4},
   pages = {121-127},
   publisher = {The American Society of Tropical Medicine and Hygiene},
   title = {Community-wide effects of permethrin-treated bed nets on child mortality and malaria morbidity in western Kenya.},
   volume = {68},
   url = {http://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&id=12749495&retmode=ref&cmd=prlinks papers3://publication/uuid/5A812181-A7D6-4C84-B9E3-D9CCDE93C497},
   year = {2003}
}

@techReport{PMI2019,
   author = {PMI},
   institution = {PMI},
   title = {Durability Monitoring of LLINs in Zanzibar, Tanzania},
   url = {https://www.pmi.gov/docs/default-source/default-document-library/pmi-reports/durability-monitoring-of-llin-in-zanzibar-final-report-after-36-months-follow-up-2019.pdf?sfvrsn=4},
   year = {2019}
}
```

#### 4. Import Analysis Table (`argilla-frontend/components/features/import/ImportAnalysisTable.vue`)

**Features using new simple table component:**
- Uses `GetImportAnalysisUseCase` from `~/v1/domain/usecases/get-import-analysis-use-case.ts` for backend communication
- Uses `useImportAnalysisViewModel` for reactive state management and API integration
- Imports backend API types from `~/v1/domain/entities/import/ImportAnalysis.ts`
- Imports UI component types from `./types.ts` for table configuration and component state
- Tabular display with columns: Reference (first column freeze), and Files, Import Status (last column freeze), while the rest of the columns imported from are sorted Title, Authors, Year, to the rest of the table
- Toggle functionality for each reference to select Add/Update/Skip
- User can toggle from Add or Update to Ignore, or back
- Status indicators with color coding (Add: green, Update: blue, Skip: gray, Ignore: gray, Failed: red)
- Filterable columns on the status indicator
- Sends POST requests to `/api/v1/imports/analyze` with `ImportAnalysisRequest` to prepopulate Import Status column
- Receives workspace ID as prop and passes it to the analysis use case
- Automatically triggers analysis when dataframe data is available and workspace ID is provided

**Table Component (`argilla-frontend/components/base/base-simple-table/BaseSimpleTable.vue`)**
- New reusable table component built on Tabulator
- Simpler than base-render-table, focused on basic tabular display using the `/dist/css/tabulator_semanticui.min.css` theme
- Support for custom column renderers and actions
- Built-in sorting, filtering, and pagination

#### 5. Batch Upload Progress (`argilla-frontend/components/features/import/ImportBatchProgress.vue`)

**Features:**
- Files uploaded in batches with sequential batch processing
- Next batch starts only when all jobs in previous batch have success or failed status
- Live reloading progress bar showing overall completion percentage
- Real-time status updates for each batch and individual files
- Current batch status display with detailed progress information
- Cancel button to stop the upload process
- Error reporting for failed uploads with retry options

#### 6. Import Summary & History Components

**Import Summary (`argilla-frontend/components/features/import/ImportSummary.vue`)**
- Import metadata summary with statistics (total processed, successfully added, updated, skipped, failed)
- Detailed breakdown of results with error information
- Failed imports table with retry options
- "View Import Log" button to access detailed history
- "Return to Library" button for navigation

**Import History List (`argilla-frontend/components/features/import/ImportHistoryList.vue`)**
- Display list of all import operations with metadata
- Columns: Import ID, Uploaded By, Date & Time, Source File Name, Total Papers, Success/Updated/Skipped/Failed counts
- "View Details" action for each import to display detailed data table
- Pagination and filtering for large import history

**Import History Details (`argilla-frontend/components/features/import/ImportHistoryDetails.vue`)**
- Detailed data table showing individual reference results
- Columns: Reference, Title, Authors, Year, Error Message, Actions
- Filter and search functionality
- Export options for import results

### API Schemas

#### Import Analysis Request
```python
class FileInfo(BaseModel):
    """Information about a file to be imported."""
    filename: str = Field(..., description="Name of the file")
    size: int = Field(..., description="File size in bytes for comparison")

class DocumentMetadata(BaseModel):
    """Metadata information for a document to be imported."""
    document_create: DocumentCreate = Field(..., description="Document creation data")
    associated_files: List[FileInfo] = Field(default_factory=list, description="PDF file metadata (not contents)")

class ImportAnalysisRequest(BaseModel):
    """Request schema for import analysis."""
    workspace_id: UUID = Field(..., description="Target workspace ID")
    documents: Dict[str, DocumentMetadata] = Field(..., description="Reference to file metadata mapping")
```

#### Import Analysis Response
```python
class ImportStatus(str, Enum):
    """Status of a document in the import process."""
    ADD = "add"
    UPDATE = "update"
    SKIP = "skip"
    FAILED = "failed"

class DocumentImportAnalysis(BaseModel):
    """Information about a document in the import analysis response."""
    document_create: DocumentCreate = Field(..., description="Document creation data")
    associated_files: List[str] = Field(default_factory=list, description="PDF filenames matched to this reference")
    status: ImportStatus = Field(..., description="Import status (add, update, skip, failed)")
    validation_errors: Optional[List[str]] = Field(default_factory=list, description="Validation error messages if any")

class ImportSummary(BaseModel):
    """Summary statistics for import analysis."""
    total_documents: int = Field(..., description="Total number of documents analyzed")
    add_count: int = Field(..., description="Number of documents to be added")
    update_count: int = Field(..., description="Number of documents to be updated")
    skip_count: int = Field(..., description="Number of documents to be skipped")
    failed_count: int = Field(..., description="Number of documents that failed analysis")

class ImportAnalysisResponse(BaseModel):
    """Response schema for import analysis."""
    documents: Dict[str, DocumentImportAnalysis] = Field(..., description="Reference to document info mapping")
    summary: ImportSummary = Field(..., description="Import analysis summary")
```

#### Bulk Upload Request/Response
```python
class BulkDocumentInfo(BaseModel):
    """Information about a document in the bulk upload request."""
    reference: str = Field(..., description="BibTeX Reference for job tracking")
    document_create: DocumentCreate = Field(..., description="Document creation data")
    associated_files: List[str] = Field(..., description="Multiple PDF filenames for this reference")

class DocumentsBulkCreate(BaseModel):
    """Metadata for bulk document upload."""
    documents: List[BulkDocumentInfo] = Field(..., description="List of documents to upload")

class DocumentsBulkResponse(BaseModel):
    """Response schema for bulk document upload."""
    job_ids: Dict[str, str] = Field(..., description="Reference to job_id mapping for frontend tracking")
    total_documents: int = Field(..., description="Total number of documents in the request")
    failed_validations: List[str] = Field(default_factory=list, description="Files that failed validation")
```


#### Import History Request/Response
```python
class ImportHistoryCreate(BaseModel):
    """Request schema for creating import history record."""
    workspace_id: UUID = Field(..., description="Target workspace ID")
    filename: str = Field(..., description="Import filename (.bib, .csv, etc.)")
    data: Dict = Field(..., description="Generic tabular dataframe data converted from source format")
    metadata: Optional[Dict] = Field(None, description="Import metadata with status and files (in list and detailed view)")

class ImportHistoryResponse(BaseModel):
    """Response schema for import history creation and retrieval."""
    id: UUID = Field(..., description="Import history record ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    user_id: UUID = Field(..., description="User ID who created the import")
    filename: str = Field(..., description="Import filename")
    created_at: datetime = Field(..., description="Creation timestamp")
    data: Optional[Dict] = Field(None, description="Tabular dataframe data (only in detailed view)")
    metadata: Optional[Dict] = Field(None, description="Import metadata with status and files (in list and detailed view)")
```

**Pagination Strategy:**
- Frontend sends multiple paginated requests (10-20 references each) to avoid large payload failures
- Each reference may have multiple associated PDF files processed in a single job
- Multiple files for the same reference are processed together to maintain consistency
- Response includes `job_ids` indexed by Reference for easy frontend tracking
- Job processing handles multiple files per reference efficiently

#### Dataframe Structure for Import History Storage

The `data` field in `ImportHistory` follows this structure for generic tabular data representation:

```json
{
    "schema": {
        "fields": [
            {
                "name": "reference",
                "type": "string"
            },
            ...
        ],
        "primaryKey": ["reference"]
    },
    "data": [
        {
            "reference": "Hawley2003a",
            ...
        }
    ]
}
```

This structure enables:
- **Generic Field Support**: Preserves all original BibTeX fields without predefined mapping
- **Type Safety**: Explicit type information for each column
- **Extensibility**: Support for different import formats (BibTeX, CSV, etc.)
- **Querying**: Efficient database indexing on primary key fields
- **Analysis**: Structured data for import history and analytics

## Data Models

### Import History Database Schema

**New Model: ImportHistory**
```python
class ImportHistory(DatabaseModel):
    __tablename__ = "import_history"

    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON()), nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", MutableDict.as_mutable(JSON()), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")

    # Index on reference field within the JSONB data column for efficient querying
    __table_args__ = (
        Index('ix_import_history_data_reference', text("(data->'data'->0->>'reference')")),
    )
```

**Purpose:**
- Records complete import history after all bulk upload batches are finished
- Stores generic tabular dataframe data (converted from BibTeX, CSV, etc.) in the `data` field
- Created via POST `/import/history` endpoint after bulk upload completion
- Provides audit trail and enables analysis of imported data regardless of source format
- Enables querying and analysis of imported tabular data across different import types (.bib, .csv, etc.)
- No predefined field mapping - preserves all original fields from source data

### Document Field Mapping
The import process maps BibTeX entries to existing Document model fields:

```python
# Existing Document model fields used:
- reference: str  # BibTeX Reference (e.g., "Hawley2003a")
- file_name: str  # Original PDF filename
- doi: str       # DOI from BibTeX entry
- pmid: str      # PMID from BibTeX entry
- url: str       # S3 URL after upload
- workspace_id: UUID  # Target workspace
```

### BibTeX Entry Processing
- **Reference**: Maps to `Document.reference` field for deduplication
- **Title**: Used for display in preview, not stored in Document model
- **Authors**: Used for display in preview, not stored in Document model
- **Year**: Used for display in preview, not stored in Document model
- **DOI/PMID**: Maps to `Document.doi` and `Document.pmid` fields
- **File Matching**: Associates PDF files with References for upload

### Generalized Tabular Data Processing
The import system processes tabular data (BibTeX, CSV, etc.) into a standardized dataframe format:

**BibTeX to Generic Dataframe Conversion:**
- Frontend parses BibTeX entries and converts all available fields to dataframe format
- No predefined field mapping - preserves all BibTeX fields as-is (title, author, journal, year, doi, pmid, etc.)
- Reference (ID field) serves as primary key
- Type inference applied automatically (string, integer, float)
- Schema generated dynamically based on available fields

**Future CSV Support:**
- First column as primary key (configurable)
- Column headers map to dataframe field names
- Type inference for string, integer, float fields
- Flexible schema definition for different data sources

**Import History Storage:**
- Complete dataframe stored in `import_history.data` field after bulk upload completion
- Enables analysis and querying of imported data regardless of original format
- Preserves all original metadata without field-specific mapping requirements

### PDF-to-Reference Matching Logic
1. **Exact Match**: PDF filename matches Reference exactly
2. **Partial Match**: PDF filename contains Reference
3. **Fuzzy Match**: Use string similarity for close matches
4. **Manual Association**: Allow user to manually associate files

## Error Handling

### BibTeX Parsing Errors
- Malformed entries: Skip and report specific line/entry errors
- Encoding issues: Attempt multiple encodings, report failures
- Duplicate References: Append suffix or prompt user resolution

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

## Testing Strategy (Don't write tests until all tasks have finished)

### Unit Tests
- BibTeX parser with various .bib file formats
- PDF matching algorithms with different filename patterns
- Import status analysis logic

### Integration Tests
- End-to-end import workflow
- File upload and processing pipeline
- Async job execution and status tracking
- Frontend-backend API integration

### Performance Tests
- Large .bib file processing (1000+ entries)
- Bulk PDF upload handling
- Concurrent import operations

### Security Tests
- File upload validation and sanitization
- BibTeX input sanitization
- Authorization checks for workspace access

## Implementation Structure

### File Organization
```
argilla-frontend/
├── v1/domain/
│   ├── entities/import/
│   │   └── ImportAnalysis.ts          # Backend API data structures
│   └── usecases/
│       └── get-import-analysis-use-case.ts # API communication logic
├── components/features/home/dataset-list/workspaces-filter/
│   ├── WorkspacesFilter.vue           # Modified for single workspace selection
│   └── WorkspaceSelector.vue          # Modified for single workspace selection
└── components/features/import/
    ├── types.ts                       # UI component types + re-exports
    ├── ImportModal.vue                # Main workflow modal (receives workspace ID)
    ├── ImportFileUpload.vue           # Step 1 & 2: File uploads
    ├── ImportAnalysisTable.vue        # Step 3: Analysis & selection (uses workspace ID)
    ├── useImportAnalysisViewModel.ts  # View model that calls get-import-analysis-use-case.ts
    └── ImportBatchProgress.vue        # Step 4: Upload progress
```

### Type Import Pattern
Components should import:
- Backend API types from `~/v1/domain/entities/import/ImportAnalysis`
- UI component types from `./types` (local to component directory)
- Use cases from `~/v1/domain/usecases/`

## Implementation Considerations

Some best practices are:
- No need to create README files for new components unless asked

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