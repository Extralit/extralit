# Implementation Plan

## Important Update: RQ Groups Integration Required

Based on the design requirements, the current implementation needs to be updated to use **RQ Groups** for workflow tracking instead of the custom DocumentWorkflow.job_ids approach. RQ Groups provide native support for:

- Grouping related jobs together for a document workflow
- Querying all jobs in a group with `group.get_jobs()`
- Tracking group-level status and progress
- Built-in group expiration and cleanup
- Resumable workflows using group-based job identification

**Key Changes Required:**
1. Replace `DocumentWorkflow.job_ids` dictionary with `group_id` field
2. Use RQ Groups to create and manage document processing workflows
3. Update all job querying functions to use `Group.get_jobs()` instead of individual job fetches
4. Implement group-based workflow restart and resumability
5. Update API endpoints to work with RQ Groups

**Note:** If RQ Groups are not available in the current RQ version, we may need to implement a custom Group wrapper or upgrade RQ version.

## Phase 1: RQ Groups Integration and Job Chaining

- [ ] 1. Implement RQ Groups for workflow tracking
  - Replace custom DocumentWorkflow.job_ids tracking with RQ Groups
  - Update workflow orchestrator to create and manage RQ Groups for document workflows
  - Modify job querying functions to use RQ Group.get_jobs() instead of individual job fetches
  - Update DocumentWorkflow model to store group_id instead of job_ids dictionary
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

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

- [ ] 1.3 Update DocumentWorkflow model for RQ Groups
  - Remove job_ids field and add group_id field to DocumentWorkflow model
  - Add status field to track overall workflow status
  - Create database migration to update existing workflows table
  - Add methods to interact with RQ Groups (get_workflow_status, is_resumable, restart_failed_jobs)
  - Update relationships and queries to work with RQ Groups
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 1.4 Refactor workflow orchestrator to use RQ Groups
  - Update create_document_workflow() to create RQ Group for each document workflow
  - Add all workflow jobs to the same RQ Group using group parameter
  - Use RQ's depends_on parameter for job dependencies within the group
  - Store group_id in DocumentWorkflow record instead of individual job_ids
  - Handle conditional OCR logic in orchestrator using group-aware job enqueueing
  - _Requirements: 1.1, 1.3, 1.4, 3.1, 8.1_
  - Handle conditional OCR logic in orchestrator, not in individual jobs
  - Update workflow to use single analysis_and_preprocess_job instead of separate jobs
  - _Requirements: 1.1, 1.3, 1.4, 8.1_

- [x] 1.5 Set up queue routing for GPU tasks
  - Add GPU_QUEUE to existing queue configuration
  - Route table extraction jobs to GPU queue in workflow orchestrator
  - Test queue routing with existing worker setup
  - _Requirements: 7.1, 7.4, 8.4_

- [ ] 1.6 Update process_bulk_upload function for RQ Groups
  - Move file upload to S3 into process_bulk_upload (before job enqueueing)
  - Create document records in database before enqueueing jobs
  - Replace upload_and_preprocess_documents_job with RQ Groups-based workflow
  - Update DocumentsBulkResponse to return workflow_id and group_id
  - Maintain backward compatibility with existing API contracts
  - _Requirements: 5.1, 5.2, 3.1_

## Phase 2: Job Querying and API Enhancement

- [x] 2. Create Pydantic schemas for job input/output
  - Create api/schemas/v1/document/metadata.py with DocumentProcessingMetadata schema for documents.metadata_ field
  - Add WorkflowJobResult schema to api/schemas/v1/jobs.py
  - Ensure all schemas have proper type hints and validation
  - _Requirements: 4.1, 4.2_

- [ ] 2.1 Implement RQ Groups-based job querying
  - Update `get_jobs_for_document(db, document_id)` to use RQ Group.get_jobs() via group_id
  - Update `get_jobs_by_reference(db, reference)` to query multiple groups
  - Update `get_workflow_status(db, document_id)` to use RQ Group status methods
  - Replace individual job fetches with group-based operations
  - Handle group expiration and missing groups gracefully
  - _Requirements: 2.2, 2.5, 3.2, 3.3_

- [ ] 2.2 Update jobs API endpoint for RQ Groups
  - Update GET /jobs/ to use RQ Groups-based job querying functions
  - Add group_id parameter for direct group querying
  - Modify WorkflowJobResult schema to include group information
  - Return group metadata in API responses including group status and progress
  - _Requirements: 6.1, 6.2, 3.2_

- [ ] 2.3 Update document workflow status endpoint for RQ Groups
  - Update GET /documents/{document_id}/workflow-status to use RQ Group status
  - Calculate workflow progress using RQ Group.get_jobs() and job statuses
  - Return overall workflow status derived from RQ Group state
  - _Requirements: 6.5, 8.1, 3.2_

- [ ] 2.4 Add RQ Groups-based workflow status monitoring
  - Implement workflow status updates using RQ Group callbacks
  - Add group status change monitoring to update DocumentWorkflow
  - Create workflow progress calculation based on RQ Group job states
  - Add workflow cleanup for expired/completed groups
  - _Requirements: 2.1, 2.4, 6.5, 3.3_

## Phase 3: CLI

- [ ] 3. Add CLI workflow management commands
- [ ] 3.1 Create FastAPI workflow endpoints
  - Create `extralit-server/src/extralit_server/api/handlers/v1/workflows.py` with workflow router
  - Add Pydantic schemas in `extralit-server/src/extralit_server/api/schemas/v1/workflows.py`
  - Implement `POST /workflows/start` endpoint for starting workflows
  - Implement `GET /workflows/status` endpoint for querying workflow status
  - Implement `POST /workflows/restart` endpoint for restarting failed workflows
  - Implement `GET /workflows/` endpoint for listing workflows with filters
  - _Requirements: 6.4_

- [ ] 3.2 Extend WorkflowContext for RQ Groups API operations
  - Update `get_workflow_status()` method to use RQ Group status and job information
  - Update `get_workflows_by_reference()` method to work with group-based tracking
  - Update `list_workflows()` method to include RQ Group information
  - Implement efficient database queries using group_id indexing
  - Add error handling for missing groups and RQ connection issues
  - _Requirements: 6.4, 3.2, 3.3_

- [ ] 3.3 Implement RQ Groups-based workflow restart functionality
  - Create `restart_failed_workflow()` function using RQ Group failed job identification
  - Add logic to identify failed jobs using RQ Group.get_jobs() with status filtering
  - Implement job re-enqueueing within the same RQ Group with proper dependencies
  - Update DocumentWorkflow records with new group state information
  - Add support for partial vs full workflow restart using RQ Group capabilities
  - _Requirements: 6.4, 3.4, 3.5_

- [ ] 3.4 Create CLI module structure and integration
  - Create `extralit/src/extralit/cli/workflows.py` with typer app
  - Add workflow_app to main CLI using `app.add_typer(workflow_app, name="workflow")`
  - Import Rich library components for formatted output (Console, Table, Progress)
  - Set up HTTP client communication pattern following `import_bib.py` example
  - Set up error handling patterns with typer.Exit and console.print
  - _Requirements: 6.4_

- [ ] 3.5 Implement CLI workflow start command
  - Create `workflow start` command with document_id, workspace_name, reference, force, and verbose options
  - Use `client.api.http_client.post()` to call `/workflows/start` endpoint
  - Add validation and error handling for HTTP responses
  - Add confirmation prompts and detailed output formatting
  - Handle errors gracefully with user-friendly messages
  - _Requirements: 6.4_

- [ ] 3.6 Implement CLI workflow status command
  - Create `workflow status` command with document_id, reference, workspace_name, watch, and json_output options
  - Use `client.api.http_client.get()` to call `/workflows/status` endpoint
  - Implement `_display_workflow_status_table()` helper function using Rich Table
  - Add real-time status watching with `--watch` flag and periodic updates
  - Support JSON output format for scripting and automation
  - Calculate and display progress percentages and duration information
  - _Requirements: 6.4_

- [ ] 3.7 Implement CLI workflow restart command
  - Create `workflow restart` command with document_id, reference, failed_only, and confirm options
  - Use `client.api.http_client.post()` to call `/workflows/restart` endpoint
  - Add confirmation prompts before restarting workflows
  - Implement selective restart logic (failed jobs only vs full workflow)
  - Display progress and results of restart operations
  - _Requirements: 6.4_

- [ ] 3.8 Implement CLI workflow list command
  - Create `workflow list` command with workspace_name, status_filter, limit, and json_output options
  - Use `client.api.http_client.get()` to call `/workflows/` endpoint
  - Add filtering capabilities by workspace and status
  - Implement pagination with configurable limits
  - Support both table and JSON output formats
  - Display comprehensive workflow information in formatted table
  - _Requirements: 6.4_

## Phase 4: RQ Groups Implementation Details

- [ ] 4.1 Research and implement RQ Groups integration
  - Research RQ Groups API and capabilities (may need to use RQ-Scheduler or custom implementation)
  - Implement Group class wrapper if RQ Groups are not available in current RQ version
  - Create group management utilities (create_group, add_job_to_group, get_group_status)
  - Add group-based job lifecycle management (group creation, job addition, status tracking)
  - Test RQ Groups functionality with Redis backend
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 4.2 Create RQ Groups database migration
  - Create Alembic migration to add group_id field to workflows table
  - Create migration to remove job_ids field from workflows table
  - Add status field to workflows table for caching group status
  - Create indexes on group_id for efficient querying
  - Handle data migration for existing workflows (if any)
  - _Requirements: 3.1_

- [ ] 4.3 Update workflow error handling for RQ Groups
  - Use RQ Groups' built-in job failure tracking
  - Store error details in group metadata
  - Implement group-based job restart logic for failed workflows
  - Add group-level retry mechanisms
  - Handle group expiration and cleanup
  - _Requirements: 6.3, 3.4, 3.5_

## Phase 5: Tests and workflow handling
- [ ] 5.1 Add comprehensive RQ Groups testing
  - Unit tests for RQ Groups integration functions
  - Integration tests for complete workflow using RQ Groups
  - Test group-based job querying and status functions
  - Test CLI commands with RQ Groups
  - Test group failure and restart scenarios
  - _Requirements: All requirements validation, 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 5.2 Performance optimization for RQ Groups
  - Test with multiple concurrent workflows using RQ Groups
  - Optimize group-based job querying performance
  - Add monitoring for group and queue performance
  - Test worker scaling with group-aware job distribution
  - Benchmark RQ Groups vs individual job tracking performance
  - _Requirements: 7.2, 7.3, 7.5, 3.2_

- [ ] 5.3 RQ Groups documentation and examples
  - Document RQ Groups integration patterns
  - Create examples of group-based workflow management
  - Document group-based job restart procedures
  - Add troubleshooting guide for RQ Groups issues
  - Document performance characteristics and limitations
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_