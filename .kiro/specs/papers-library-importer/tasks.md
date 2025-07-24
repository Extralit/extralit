# Implementation Plan

- [x] 1. Set up backend API structure and schemas
  - Create import analysis API handler with endpoint structure
  - Define Pydantic schemas for ImportAnalysisRequest, ImportAnalysisResponse, and related models
  - Add basic validation and error handling for the analysis endpoint
  - _Requirements: 1.1, 2.1_

- [ ] 2. Implement import analysis logic
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

- [x] 2.3 Create CLI import analysis testing function
  - Add import_bibtex() function to extralit/src/argilla/cli/documents/add.py
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
  - Update CLI function `import_bibtex` in `extralit/src/argilla/cli/documents/add.py` to test bulk upload
  - _Requirements: 3.1, 3.3, 3.4, 3.7_

- [x] 3.3 Implement ImportHistory database model
  - Create ImportHistory model in database.py with required fields
  - Add relationships to Workspace and User models
  - Create migration script for the new table
  - _Requirements: 3.5, 4.1_

- [ ] 3.4 Integrate bulk upload with job queue and history logging for multi-file references
  - Connect bulk upload endpoint to reference-based document upload jobs
  - Implement `reference_key` indexed job_id response mapping
  - Create import history record for each bulk import with complete reference and file information
  - Store ImportAnalysisResponse data in the metadata JSON field including multi-file associations
  - Add proper cleanup of temporary files after job completion
  - Handle multiple files per reference in job processing and error reporting
  - _Requirements: 3.2, 3.5, 4.1, 4.6_

- [ ] 4. Implement frontend BibTeX parsing and file matching
- [ ] 4.1 Create BibTeX parser component
  - Add JavaScript BibTeX parser library dependency (bibtex-parse-js or similar)
  - Implement BibTeX file parsing in ImportUpload.vue component
  - Extract metadata (title, authors, year, DOI, PMID, reference key)
  - Add error handling for malformed BibTeX entries
  - _Requirements: 1.1, 5.1_

- [ ] 4.2 Implement file-to-reference matching logic
  - Create file matching algorithm based on filename patterns
  - Implement exact match, partial match, and fuzzy matching strategies
  - Allow manual file-to-reference association by user
  - Add validation for PDF file types and sizes
  - _Requirements: 1.3, 1.6_

- [ ] 5. Create import upload and preview components
- [ ] 5.1 Implement ImportUpload.vue component
  - Create drag-and-drop interface for .bib file and PDF folder uploads
  - Integrate BibTeX parsing and file matching functionality
  - Add collection tag input and file validation
  - Implement progress indicators for file processing
  - Send ImportAnalysisRequest to backend (metadata only, not file contents)
  - _Requirements: 1.1, 1.2, 1.4_

- [ ] 5.2 Create ImportPreview.vue component
  - Display tabular view of documents with add/update/skip/failed status
  - Show document metadata (title, authors, year) and associated files
  - Allow user to modify actions for individual documents
  - Implement bulk confirmation interface
  - Add validation before proceeding to upload phase
  - _Requirements: 2.1, 2.2, 2.7_

- [ ] 6. Implement bulk upload execution and progress tracking
- [ ] 6.1 Create bulk upload execution logic for multi-file references
  - Implement paginated bulk upload requests (10-20 references per batch)
  - Send DocumentImportExecuteRequest with actual file contents to POST /documents/bulk
  - Handle multiple files per reference in each batch request
  - Handle multiple paginated requests for large document sets
  - Add error handling for failed upload requests with per-file error tracking
  - _Requirements: 3.1, 3.2, 3.7_

- [ ] 6.2 Implement ImportProgress.vue component for multi-file tracking
  - Create real-time progress tracking using job status polling
  - Display reference-by-reference upload status with file-level details
  - Show overall progress across all paginated requests and files
  - Implement error reporting for failed uploads with reference and file context
  - Add cancellation support for ongoing uploads
  - Track progress at both reference and individual file levels
  - _Requirements: 3.2, 3.3, 3.7_

- [ ] 7. Create import results and workspace integration
- [ ] 7.1 Implement ImportResults.vue component
  - Display import summary statistics (added, updated, skipped, failed)
  - Show detailed error information for failed imports
  - Provide navigation to workspace documents list
  - Add option to retry failed imports
  - _Requirements: 3.5, 4.3_

- [ ] 7.2 Integrate imported documents with workspace features for multi-file references
  - Ensure imported documents appear in workspace documents list with proper reference grouping
  - Verify document metadata is properly stored and displayed for multiple files per reference
  - Test compatibility with existing document processing features
  - Add proper metadata tags for collection and source tracking
  - Implement UI grouping of multiple files by reference key while maintaining individual document records
  - _Requirements: 4.1, 4.2, 4.4, 4.6, 4.7_

- [ ] 8. Add comprehensive error handling and validation
- [ ] 8.1 Implement robust error handling
  - Add specific error messages for BibTeX parsing failures
  - Handle corrupted PDF files with detailed error reporting
  - Implement retry mechanisms for network and storage failures
  - Add workspace storage quota validation
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 8.2 Add security and performance optimizations
  - Implement file type and size validation
  - Add rate limiting for bulk upload requests
  - Add cleanup of temporary files and partial uploads
  - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [ ] 9. Create import page and routing
- [ ] 9.1 Implement main import page
  - Create import.vue page in argilla-frontend/pages/workspace/_id/
  - Integrate all import components (upload, preview, progress, results)
  - Add proper routing and navigation
  - Implement state management for import workflow
  - _Requirements: 4.3, 4.4_

- [ ] 9.2 Add import workflow orchestration
  - Coordinate transitions between upload, preview, and execution phases
  - Implement proper state persistence across browser sessions
  - Add workflow validation and error recovery
  - _Requirements: 5.6, 3.6_

- [ ] 10. Add documentation and final validation
  - Document API endpoints and request/response schemas
  - Create user guide for import functionality
  - Add developer documentation for extending import features
  - Perform final end-to-end testing with real .bib files and PDFs
  - _Requirements: Complete feature validation_