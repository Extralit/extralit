# Implementation Plan

- [x] 1. Set up backend API structure and schemas
  - Create import analysis API handler with endpoint structure
  - Define Pydantic schemas for ImportAnalysisRequest, ImportAnalysisResponse, and related models
  - Add basic validation and error handling for the analysis endpoint
  - _Requirements: 1.1, 2.1_

- [x] 2. Implement import analysis logic
- [x] 2.1 Create import context service for document analysis
  - Write analyze_import_status() function to check existing documents by reference/DOI/PMID
  - Implement compare_file_sizes() function to determine if file updates are needed
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
  - Add import() function to extralit/src/argilla/cli/documents/add.py
  - Parse BibTeX file and match PDF files from folder using Python bibtexparser
  - Perform filename matching to create the analysis_request
  - Send ImportAnalysisRequest to argilla-server for testing import analysis functionality
  - Display analysis results (add/update/skip status) in CLI output
  - Enable easy testing of backend import analysis before building frontend
  - _Requirements: 1.1, 2.1, 2.2_

- [ ] 3. Create bulk document upload endpoint
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
  - Update CLI function `import` in `extralit/src/argilla/cli/documents/add.py` to test bulk upload
  - _Requirements: 3.1, 3.3, 3.4, 3.7_

- [x] 3.3 Implement ImportHistory database model
  - Create ImportHistory model in database.py with required fields, with the alembic upgrade path at `argilla-server/src/argilla_server/alembic/versions/7d6b33203390_create_import_history_table.py`
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

- [ ] 4. Implement frontend BibTeX parsing and file matching
- [x] 4.1 Create BibTeX parser component with generic dataframe conversion
  - Add JavaScript BibTeX parser library dependency (bibtex-parse-js or similar)
  - Implement BibTeX file parsing in ImportUpload.vue component
  - Convert BibTeX entries to generic dataframe format (preserve all fields)
  - Extract metadata (title, authors, year, DOI, PMID, Reference) for document creation
  - Add error handling for malformed BibTeX entries
  - Store parsed dataframe data for later submission to import history endpoint
  - _Requirements: 1.1, 5.1_

- [x] 4.2 Implement file-to-reference matching logic
  - Create file matching algorithm based on filepath or filename patterns
  - Implement exact match, partial match, and fuzzy matching strategies
  - Allow manual file-to-reference association by user
  - Add validation for PDF file types and sizes
  - _Requirements: 1.3, 1.6_

- [x] 5. Create home page integration and modal workflow
- [x] 5.1 Add Import Documents button to home page
  - Add "Import Documents" button above ImportFromHub and ImportFromPython components in pages/index.vue
  - Style button to match existing import section design
  - Connect button to open full-page import modal
  - _Requirements: 1.1, 4.3_

- [x] 5.2 Create ImportModal.vue full-page modal component
  - Implement full-page modal using existing base-modal component
  - Create multi-step workflow with navigation between steps
  - Add step indicators and progress tracking
  - Implement modal state management and step validation
  - _Requirements: 2.1, 4.3_

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

- [ ] 7. Create simple table component and analysis interface
- [x] 7.1 Implement BaseSimpleTable.vue component
  - Create new reusable table component using Tabulator library
  - Build simpler alternative to base-render-table for basic tabular display
  - Add support for custom column renderers and actions
  - Implement built-in sorting, filtering, and pagination
  - _Requirements: 2.1, 2.2_

- [x] 7.2 Create ImportAnalysisTable.vue component (Step 3)
  - Implement tabular display using BaseSimpleTable component
  - Add columns: Reference, Title, Authors, Year, Import Status
  - Create toggle functionality for Add/Update/Skip selection
  - Add status indicators with color coding (Add: green, Update: blue, Skip: gray, Failed: red)
  - Send ImportAnalysisRequest to backend and display results
  - _Requirements: 2.1, 2.2, 2.7_

- [ ] 8. Implement batch upload execution and progress tracking
- [ ] 8.1 Create sequential batch upload logic
  - Implement batch processing where next batch starts only when all jobs in previous batch have success or failed status
  - Send paginated bulk upload requests (10-20 references per batch)
  - Handle multiple files per reference in each batch request
  - Add batch completion detection and automatic progression to next batch
  - Add error handling for failed upload requests with per-file error tracking
  - _Requirements: 3.1, 3.2, 3.7_

- [ ] 8.2 Implement ImportBatchProgress.vue component (Step 4)
  - Create live reloading progress bar showing overall completion percentage
  - Display current batch status with detailed progress information
  - Implement real-time status updates using job status polling
  - Show batch-by-batch progress with individual file status
  - Add Cancel button to stop the upload process
  - Track progress at both batch and individual file levels
  - After all batches complete, send generic dataframe data to POST /import/history endpoint
  - _Requirements: 3.2, 3.3, 3.7_

- [ ] 9. Create import summary and history components
- [ ] 9.1 Implement ImportSummary.vue component (Step 5)
  - Display import metadata summary with statistics (total processed, successfully added, updated, skipped, failed)
  - Show detailed breakdown of results with error information
  - Create failed imports table with retry options
  - Add "View Import Log" button to access detailed history
  - Add "Return to Library" button for navigation back to workspace
  - _Requirements: 3.5, 4.3_

- [ ] 9.2 Create ImportHistoryList.vue component
  - Display list of all import operations with metadata table
  - Add columns: Import ID, Uploaded By, Date & Time, Source File Name, Total Papers, Success/Updated/Skipped/Failed counts
  - Implement "View Details" action for each import to display detailed data table
  - Add pagination and filtering for large import history
  - _Requirements: 3.5, 4.3_

- [ ] 9.3 Create ImportHistoryDetails.vue component
  - Implement detailed data table showing individual reference results
  - Add columns: Reference, Title, Authors, Year, Error Message, Actions
  - Add filter and search functionality
  - Implement export options for import results
  - _Requirements: 3.5, 4.3_

- [ ] 10. Integrate imported documents with workspace features
- [ ] 10.1 Integrate imported documents with workspace features for multi-file references
  - Ensure imported documents appear in workspace documents list with proper reference grouping
  - Verify document metadata is properly stored and displayed for multiple files per reference
  - Test compatibility with existing document processing features
  - Add proper metadata tags for collection and source tracking
  - Implement UI grouping of multiple files by Reference while maintaining individual document records
  - _Requirements: 4.1, 4.2, 4.4, 4.6, 4.7_

- [ ] 11. Add comprehensive error handling and validation
- [ ] 11.1 Implement robust error handling
  - Add specific error messages for BibTeX parsing failures
  - Handle corrupted PDF files with detailed error reporting
  - Implement retry mechanisms for network and storage failures
  - Add workspace storage quota validation
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 11.2 Add security and performance optimizations
  - Implement file type and size validation
  - Add rate limiting for bulk upload requests
  - Add cleanup of temporary files and partial uploads
  - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [ ] 12. Add modal workflow orchestration and state management
- [ ] 12.1 Implement modal workflow state management
  - Coordinate transitions between all 5 steps in the modal workflow
  - Implement proper state persistence during the import process
  - Add step validation and error recovery between steps
  - Handle modal close/cancel scenarios with proper cleanup
  - _Requirements: 5.6, 3.6_

- [ ] 12.2 Add workflow navigation and validation
  - Implement step-by-step navigation with back/next buttons
  - Add validation checks before allowing progression to next step
  - Handle workflow interruption and resume functionality
  - Add proper loading states and user feedback throughout workflow
  - _Requirements: 4.3, 4.4_

- [ ] 13. Add documentation and final validation
  - Document API endpoints and request/response schemas
  - Create user guide for import functionality
  - Add developer documentation for extending import features
  - Perform final end-to-end testing with real .bib files and PDFs
  - _Requirements: Complete feature validation_