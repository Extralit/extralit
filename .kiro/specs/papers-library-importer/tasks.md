# Implementation Plan

- [x] 1. Set up backend API structure and schemas
  - Create import analysis API handler with endpoint structure
  - Define Pydantic schemas for ImportAnalysisRequest, ImportAnalysisResponse, and related models
  - Add basic validation and error handling for the analysis endpoint
  - _Requirements: 1.1, 2.1_

- [x] 2. Implement import analysis logic
- [x] 2.1 Create import context service for document analysis
  - Write analyze_import_status() function to check existing documents by reference/DOI/PMID
  - Create validate_document_metadata() function for DocumentMetadata validation
  - _Requirements: 2.3, 2.4, 2.5_

- [x] 2.2 Implement import analysis API endpoint
  - Code POST /api/v1/imports/analyze endpoint handler
  - Integrate with import context service for status determination
  - Add proper error handling and validation
  - _Requirements: 2.1, 2.2_

- [x] 2.4 Add POST /import/history endpoint for storing generic dataframe data
  - Create POST /api/v1/imports/history endpoint in imports.py handler
  - Add ImportHistoryCreate and ImportHistoryResponse schemas
  - Implement endpoint to store generic tabular dataframe data after bulk upload completion
  - _Requirements: 2.1, 2.2_

- [x] 2.3 Create CLI import analysis testing function
  - Add import() function to extralit/src/extralit/cli/documents/add.py
  - Parse BibTeX file and match PDF files from folder using Python bibtexparser
  - Perform filename matching to create the analysis_request
  - Send ImportAnalysisRequest to extralit-server for testing import analysis functionality
  - Display analysis results (add/update/skip status) in CLI output
  - Enable easy testing of backend import analysis before building frontend
  - _Requirements: 1.1, 2.1, 2.2_

- [x] 3. Create bulk document upload endpoint
- [x] 3.1 Implement bulk upload API handler
  - Create POST /documents/bulk endpoint in documents.py handler
  - Handle multipart form data with documents_metadata and files
  - Implement pagination support for 20-50 PDFs per request
  - Add file validation and error handling
  - _Requirements: 3.1, 3.2_

- [x] 3.2 Create document upload job system for multiple files per reference
  - Write upload_reference_documents_job() function in jobs/document_jobs.py to handle multiple files per reference
  - Reuse existing document upload logic from POST /documents endpoint for each file
  - Implement job creation and queuing for reference-based document uploads (one job per reference)
  - Add retry logic and error handling for failed uploads with per-file error tracking
  - Update CLI function `import` in `extralit/src/extralit/cli/documents/add.py` to test bulk upload
  - _Requirements: 3.1, 3.3, 3.4, 3.7_

- [x] 3.3 Implement ImportHistory database model
  - Create ImportHistory model in database.py with required fields, with the alembic upgrade path at `extralit-server/src/extralit_server/alembic/versions/7d6b33203390_create_import_history_table.py`
  - Add relationships to Workspace and User models
  - Create migration script for the new table
  - _Requirements: 3.5, 4.1_

- [x] 3.4 Integrate bulk upload with job queue and progress tracking for multi-file references
  - Connect bulk upload endpoint to reference-based document upload jobs
  - Implement `reference` indexed job_id response mapping for frontend tracking
  - Add proper cleanup of temporary files after job completion
  - Handle multiple files per reference in job processing and error reporting
  - Remove import history creation from bulk upload (moved to separate endpoint)
  - _Requirements: 3.2, 3.5, 4.1, 4.6_

- [x] 4. Create frontend domain architecture and implement BibTeX parsing
- [x] 4.0 Create frontend domain entities and use cases
  - Create ImportAnalysis.ts in ~/v1/domain/entities/import/ with backend API data structures
  - Create get-import-analysis-use-case.ts in ~/v1/domain/usecases/ for API communication
  - Update components/features/import/types.ts to contain only UI-specific component types
  - Implement GetImportAnalysisUseCase with axios integration for POST /api/v1/imports/analyze
  - _Requirements: 2.1, 2.2, 4.3_
- [x] 4.1 Create BibTeX parser component with generic dataframe conversion
  - Add JavaScript BibTeX parser library dependency (bibtex-parse-js or similar)
  - Implement BibTeX file parsing in ImportFileUpload.vue component
  - Convert BibTeX entries to generic dataframe format (preserve all fields)
  - Extract metadata (title, authors, year, DOI, PMID, Reference) for document creation
  - Add error handling for malformed BibTeX entries
  - Store parsed dataframe data for later submission to import history endpoint
  - Use DataframeData type from ~/v1/domain/entities/import/ImportAnalysis.ts
  - _Requirements: 1.1, 5.1_

- [x] 4.1.1 Add CSV parser component with column selection
  - Add performant CSV parser library dependency (papaparse or similar)
  - Implement CSV file parsing in ImportFileUpload.vue component
  - Allow user to select reference column and files column for PDF matching
  - Convert CSV entries to generic dataframe format (preserve all columns)
  - Add validation for required columns and data types
  - Handle CSV parsing errors gracefully with user feedback
  - _Requirements: 1.2, 5.2_

- [x] 4.2 Implement file-to-reference matching logic
  - Create file matching algorithm based on filepath or filename patterns
  - Implement exact match, partial match, and fuzzy matching strategies
  - Allow manual file-to-reference association by user
  - Add validation for PDF file types and sizes
  - _Requirements: 1.3, 1.6_

- [x] 4.2.1 Enhance PDF matching with maximum prefix path matching
  - Implement maximum prefix path matching algorithm for better file association
  - Improve matching to handle multiple PDFs per reference correctly
  - Add progressive file addition with proper deduplication
  - Clean up redundant matching information and improve matching accuracy
  - Ensure correct handling when reference matches multiple PDF files
  - _Requirements: 1.4, 1.8_

- [x] 5. Create home page integration and modal workflow
- [x] 5.1 Add Import Documents button to home page and modify workspace selection
  - Add "Import Documents" button above ImportFromHub and ImportFromPython components in pages/index.vue
  - Style button to match existing import section design
  - Connect button to open full-page import modal
  - Modify WorkspacesFilter and WorkspaceSelector components to support single workspace selection instead of multi-select
  - Pass selected workspace ID to ImportModal component
  - Update DatasetList.vue to handle single workspace selection and pass workspace ID to import modal
  - _Requirements: 1.1, 4.3_

- [x] 5.2 Create ImportModal.vue full-page modal component with workspace context
  - Implement full-page modal using existing base-modal component
  - Create multi-step workflow with navigation between steps
  - Add step indicators and progress tracking
  - Implement modal state management and step validation
  - Accept workspace ID as prop from home page
  - Pass workspace ID to ImportAnalysisTable component
  - _Requirements: 2.1, 4.3_

- [x] 5.2.1 Improve modal flow control and closing behavior
  - Update ImportModal.vue to disable confirm-close after successful completion
  - Ensure confirm-close is only active during import process, not after completion
  - Allow flexible upload order (bibliography first or PDFs first)
  - Improve step navigation to preserve data when moving between steps
  - Add event emission to refresh recent import list on home screen after modal closes
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 6. Implement upload step components
- [x] 6.1 Create ImportBibUpload.vue component (Step 1)
  - Implement .bib file upload with drag-and-drop interface
  - Add file validation and BibTeX parsing preview
  - Display upload status and reference count after parsing
  - Show supported file formats (Zotero, EndNote, Mendeley exports)
  - _Requirements: 1.1, 5.1, 4.2_

- [x] 6.2 Create ImportPdfUpload.vue component (Step 2)
  - Implement multiple PDF file upload with drag-and-drop or folder selection
  - Add file matching preview with bibliography entries
  - Display upload progress and file validation results
  - Show summary status with matched/unmatched files count
  - _Requirements: 1.2, 1.3, 4.2_

- [x] 6.3 Update workspace selection for single workspace mode
  - Modify WorkspacesFilter.vue to support single workspace selection instead of multi-select
  - Update WorkspaceSelector.vue to use radio buttons instead of checkboxes for single selection
  - Update DatasetList.vue to handle single workspace selection and emit workspace ID
  - Update useHomeViewModel.ts to track selected workspace ID and pass it to ImportModal
  - Ensure workspace context is maintained and passed to import components
  - _Requirements: 1.1, 4.3_

- [ ] 7. Create simple table component and analysis interface
- [x] 7.1 Implement BaseSimpleTable.vue component
  - Create new reusable table component using Tabulator library
  - Build simpler alternative to base-render-table for basic tabular display
  - Add support for custom column renderers and actions
  - Implement built-in sorting, filtering, and pagination
  - _Requirements: 2.1, 2.2_

- [x] 7.2 Create ImportAnalysisTable.vue component (Step 3) with workspace integration
  - Create toggle functionality for Add/Update/Skip selection
  - Send ImportAnalysisRequest to backend and display results using GetImportAnalysisUseCase
  - Import backend API types from ~/v1/domain/entities/import/ImportAnalysis.ts
  - Use useImportAnalysisViewModel for reactive state management and API integration
  - Accept workspace ID as prop and pass it to the analysis use case
  - Fix workspaceId reference in useImportAnalysisViewModel.ts to properly access workspace from parent component
  - _Requirements: 2.1, 2.2, 2.7_

- [ ] 7.2.1 Add option to import references without PDFs
  - Add toggle option to import entire table including references without matched PDFs
  - Add toggle option to import only references with at least one matched PDF file
  - Update table filtering to show/hide references without PDFs based on user selection
  - Modify import confirmation logic to respect user's choice about references without PDFs
  - _Requirements: 2.6, 2.8, 2.9_

- [x] 7.3 Fix ImportModal step navigation and data persistence
  - Update ImportFileUpload.vue to accept initialBibData and initialPdfData props
  - Add initializeWithExistingData() method to restore component state when navigating back
  - Update ImportModal.vue to pass existing data to ImportFileUpload component
  - Ensure proper data persistence across step navigation without losing uploaded files
  - Fix component lifecycle management to show uploaded files when returning to step 0
  - _Requirements: 2.1, 2.2, 4.3_
- [ ] 8. Implement batch upload execution and progress tracking
- [x] 8.1 Create sequential batch upload logic
  - Implement batch processing where next batch starts only when all jobs in previous batch have success or failed status
  - Send paginated bulk upload requests (10-20 references per batch)
  - Handle multiple files per reference in each batch request
  - Add batch completion detection and automatic progression to next batch
  - Add error handling for failed upload requests with per-file error tracking
  - _Requirements: 3.1, 3.2, 3.7_

- [x] 8.2 Implement ImportBatchProgress.vue component (Step 4)
  - Create live reloading progress bar showing overall completion percentage
  - Display current batch status with detailed progress information
  - Implement real-time status updates using job status polling
  - Show batch-by-batch progress with individual file status
  - Add Cancel button to stop the upload process
  - Track progress at both batch and individual reference (which contains multiple files) levels
  - After all batches complete, send generic dataframe data to POST /import/history endpoint
  - _Requirements: 3.2, 3.3, 3.7_

- [x] 9. Create import summary and history components
- [x] 9.1 Implement ImportSummary.vue component (Step 5)
  - Display import metadata summary with statistics (total processed, successfully added, updated, skipped, failed)
  - Show detailed breakdown of results with error information
  - Create failed imports table with retry options
  - Add "View Import Log" button to access detailed history
  - Add "Return to Library" button for navigation back to workspace
  - _Requirements: 3.5, 4.3_

- [x] 9.2 Create ImportHistoryList.vue component
  - Display list of all import operations with metadata table
  - Add columns: Import ID, Uploaded By, Date & Time, Source File Name, Total Papers, Success/Updated/Skipped/Failed counts
  - Implement "View Details" action for each import to display detailed data table
  - Add pagination and filtering for large import history
  - _Requirements: 3.5, 4.3_

- [x] 9.3 Create ImportHistoryDetails.vue component
  - Implement detailed data table showing individual reference results
  - Add columns: Reference, Title, Authors, Year, Error Message, Actions
  - Add filter and search functionality
  - Implement export options for import results
  - _Requirements: 3.5, 4.3_

- [x] 10. Integrate imported documents with workspace features
- [x] 10.1 Integrate imported documents with workspace features for multi-file references
  - Ensure imported documents appear in workspace documents list with proper reference grouping
  - Verify document metadata is properly stored and displayed for multiple files per reference
  - Test compatibility with existing document processing features
  - Add proper metadata tags for collection and source tracking
  - Implement UI grouping of multiple files by Reference while maintaining individual document records
  - _Requirements: 4.1, 4.2, 4.4, 4.6, 4.7_

- [ ] 11. Add comprehensive error handling and validation
- [ ] 11.1 Implement robust error handling
  - Implement retry mechanisms for network and storage failures
  - Add workspace storage quota validation
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 11.2 Add security and performance optimizations
  - Add rate limiting for bulk upload requests
  - Add cleanup of temporary files and partial uploads
  - _Requirements: 6.1, 6.2, 6.5, 6.6_

