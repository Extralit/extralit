# Implementation Plan

## Phase 1: Basic RQ Job Chaining (Week 1)

- [x] 1. Refactor existing document upload job
  - Split `upload_and_preprocess_documents_job` into separate chained jobs
  - Move file upload to S3 into the API endpoint (process_bulk_upload)
  - Pass document IDs and S3 URLs to jobs instead of raw file data
  - _Requirements: 1.1, 1.2, 5.1, 5.3_

- [x] 1.1 Create combined PDF processing job function
  - Create `analysis_and_preprocess_job(document_id, s3_url, reference, workspace_id)` combining PDFOCRLayerDetector, PDFAnalyzer, and PDFPreprocessor
  - Analysis runs on original PDF, then OCRmyPDF preprocessing overwrites same S3 path for page rotation
  - Add job metadata tracking (document_id, reference, workflow_step, started_at, completed_at)
  - Use type hints for all parameters and return values
  - Integrate with existing file download/upload functions from contexts/files.py
  - Store combined results in documents.metadata_ using DocumentProcessingMetadata schema
  - _Requirements: 1.1, 2.1, 4.1, 4.5_

- [x] 1.2 Create DocumentWorkflow database model
  - Add DocumentWorkflow model to models/database.py for efficient job tracking
  - Create database migration for document_workflows table
  - Add relationship to Document model
  - Include methods for job status updates and workflow queries
  - _Requirements: 2.2, 2.5, 6.1_

- [x] 1.3 Create centralized workflow orchestrator
  - Create start_pdf_workflow() function that manages entire job chain
  - Use RQ's depends_on parameter for job dependencies (no jobs enqueueing other jobs)
  - Create DocumentWorkflow record and store job IDs for efficient querying
  - Handle conditional OCR logic in orchestrator, not in individual jobs
  - Update workflow to use single analysis_and_preprocess_job instead of separate jobs
  - _Requirements: 1.1, 1.3, 1.4, 8.1_

- [x] 1.4 Set up queue routing for GPU tasks
  - Add GPU_QUEUE to existing queue configuration
  - Route table extraction jobs to GPU queue in workflow orchestrator
  - Test queue routing with existing worker setup
  - _Requirements: 7.1, 7.4, 8.4_

- [x] 1.5 Update process_bulk_upload function
  - Move file upload to S3 into process_bulk_upload (before job enqueueing)
  - Create document records in database before enqueueing jobs
  - Replace upload_and_preprocess_documents_job with start_pdf_workflow() call
  - Update DocumentsBulkResponse to return workflow_id and job_ids
  - Maintain backward compatibility with existing API contracts
  - _Requirements: 5.1, 5.2_

## Phase 2: Job Querying and API Enhancement (Week 2)

- [x] 2. Create Pydantic schemas for job input/output
  - Create api/schemas/v1/document/metadata.py with DocumentProcessingMetadata schema for documents.metadata_ field
  - Add WorkflowJobResult schema to api/schemas/v1/jobs.py
  - Ensure all schemas have proper type hints and validation
  - _Requirements: 4.1, 4.2_

- [x] 2.1 Implement efficient job querying using database
  - Create `get_jobs_for_document(db, document_id)` using DocumentWorkflow lookup
  - Create `get_jobs_by_reference(db, reference)` using document lookup
  - Create `get_workflow_status(db, document_id)` for complete workflow status
  - Replace expensive registry scanning with single job fetches
  - Handle job expiration and missing jobs gracefully
  - _Requirements: 2.2, 2.5_

- [x] 2.2 Extend existing jobs API endpoint
  - Add query parameters to GET /jobs/ (document_id, reference, workflow_step) in api/handlers/v1/jobs.py
  - Use WorkflowJobResult schema created in task 2
  - Modify existing JobSchema to include workflow metadata from job.meta
  - Return job metadata in API responses including workflow_step and progress
  - _Requirements: 6.1, 6.2_

- [x] 2.3 Add document workflow status endpoint
  - Create GET /documents/{document_id}/workflow-status endpoint
  - Calculate workflow progress based on completed steps
  - Return overall workflow status (pending, running, completed, failed)
  - _Requirements: 6.5, 8.1_

- [x] 2.4 Add workflow status monitoring
  - Implement workflow status updates when jobs complete/fail
  - Add job status change callbacks to update DocumentWorkflow
  - Create workflow progress calculation based on completed steps
  - Add workflow cleanup for expired/completed workflows
  - _Requirements: 2.1, 2.4, 6.5_

## Phase 3: CLI and Error Handling (Week 3)

- [ ] 4. Add CLI workflow management commands
  - Create `workflow start` command using typer
  - Create `workflow status` command to check document progress
  - Create `workflow restart` command for failed jobs
  - _Requirements: 6.4_

- [ ] 4.1 Implement workflow error handling
  - Use RQ's built-in retry mechanism for transient failures
  - Store error details in job metadata
  - Implement job restart logic for failed workflows
  - _Requirements: 6.3_

- [ ] 4.2 Add comprehensive testing
  - Unit tests for individual job functions
  - Integration tests for complete workflow
  - Test job metadata querying functions
  - Test CLI commands
  - _Requirements: All requirements validation_

- [ ] 4.3 Performance optimization
  - Test with multiple concurrent workflows
  - Optimize job metadata querying performance
  - Add monitoring for queue performance
  - Test worker scaling (CPU + GPU workers)
  - _Requirements: 7.2, 7.3, 7.5_