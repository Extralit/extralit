# PDF Workflow Orchestrator Requirements

## Introduction

The PDF Workflow Orchestrator leverages RQ's native job chaining capabilities to process PDFs through a series of steps: analysis, preprocessing, OCR, text extraction, table extraction, and embedding. The system uses RQ's built-in features like job dependencies, job groups, job metadata, and job registries to provide workflow execution and tracking without custom abstractions.

## Requirements

### Requirement 1: RQ Native Job Dependencies

**User Story:** As a developer, I want to use RQ's `depends_on` parameter to chain jobs together, so that jobs execute in the correct order without custom workflow abstractions.

#### Acceptance Criteria

1. WHEN enqueueing jobs THEN the system SHALL use RQ's `depends_on` parameter to define job dependencies
2. WHEN a dependency job fails THEN RQ SHALL automatically prevent dependent jobs from running
3. WHEN jobs have multiple dependencies THEN RQ SHALL wait for all dependencies to complete successfully
4. WHEN conditional logic is needed THEN jobs SHALL enqueue their own dependent jobs based on results
5. WHEN parallel jobs are needed THEN the system SHALL enqueue multiple jobs without dependencies

### Requirement 2: RQ Job Metadata for Document Tracking

**User Story:** As a developer, I want to use RQ's job metadata to track document processing, so that I can query job status by document ID or reference using RQ's built-in capabilities.

#### Acceptance Criteria

1. WHEN enqueueing jobs THEN the system SHALL store document_id, reference, workspace_id, and workflow_step in job.meta
2. WHEN querying jobs THEN the system SHALL scan RQ job registries to find jobs by metadata
3. WHEN jobs are running THEN the system SHALL update job.meta with progress information
4. WHEN jobs complete THEN the system SHALL store results in job.meta or job.result
5. WHEN tracking workflows THEN the system SHALL use job metadata to reconstruct workflow state

### Requirement 3: RQ Job Groups for Document Workflows

**User Story:** As a developer, I want to use RQ's job groups to track related jobs for a document, so that I can monitor complete document processing workflows.

#### Acceptance Criteria

1. WHEN starting document processing THEN the system SHALL create an RQ Group for the document
2. WHEN enqueueing jobs THEN the system SHALL add jobs to the document's group
3. WHEN querying workflow status THEN the system SHALL use group.get_jobs() to retrieve all related jobs
4. WHEN jobs fan-out THEN multiple jobs SHALL be added to the same group
5. WHEN groups expire THEN RQ SHALL automatically clean up completed groups

### Requirement 4: Enhanced Job Functions with Type Hints

**User Story:** As a developer, I want to define job functions with clear type hints and use RQ's @job decorator, so that job definitions are maintainable and compatible with RQ's serialization.

#### Acceptance Criteria

1. WHEN defining job functions THEN developers SHALL use type hints for all parameters and return values
2. WHEN using RQ decorators THEN the system SHALL use RQ's @job decorator with queue, timeout, and retry parameters
3. WHEN jobs need conditional logic THEN they SHALL enqueue dependent jobs within the function
4. WHEN jobs process files THEN they SHALL accept database IDs or S3 URLs instead of raw file data
5. WHEN jobs complete THEN they SHALL return serializable results that can be passed to dependent jobs

### Requirement 5: Database and S3 File References

**User Story:** As a system operator, I want jobs to use SQLAlchemy database connections and S3 presigned URLs to access files, so that large files don't clog up the Redis queue.

#### Acceptance Criteria

1. WHEN jobs need database access THEN they SHALL use the existing get_async_db dependency injection
2. WHEN jobs need file access THEN they SHALL use presigned S3 URLs or direct S3 client access
3. WHEN passing data between jobs THEN the system SHALL pass document IDs and file references, not raw data
4. WHEN jobs create temporary files THEN they SHALL clean up resources after processing
5. WHEN jobs store results THEN they SHALL use existing database models and S3 storage patterns

### Requirement 6: Enhanced Job API for Document Workflows

**User Story:** As a developer, I want to query jobs by document ID, reference, or workflow step through the existing jobs API, so that I can track document processing progress.

#### Acceptance Criteria

1. WHEN querying jobs THEN the API SHALL support filtering by document_id, reference, and workflow_step
2. WHEN returning job status THEN the API SHALL include job metadata and group information
3. WHEN jobs fail THEN the API SHALL return error details and failure information
4. WHEN restarting workflows THEN the system SHALL provide CLI commands to re-enqueue failed jobs
5. WHEN monitoring progress THEN the API SHALL show the current workflow step and overall progress

### Requirement 7: Multi-Queue Worker Support

**User Story:** As a system operator, I want to run workers on different queues for CPU and GPU tasks, so that I can scale processing based on resource requirements.

#### Acceptance Criteria

1. WHEN running CPU workers THEN they SHALL process jobs from default and high priority queues
2. WHEN running GPU workers THEN they SHALL process jobs from dedicated GPU queues
3. WHEN scaling workers THEN the system SHALL support multiple workers per queue type
4. WHEN jobs require specific resources THEN they SHALL be enqueued to appropriate queues
5. WHEN workers are distributed THEN RQ SHALL handle job distribution and coordination automatically

### Requirement 8: PDF Processing Workflow Implementation

**User Story:** As a system user, I want to process PDFs through a complete workflow of analysis, preprocessing, OCR, text extraction, table extraction, and embedding, so that I can extract structured data from documents.

#### Acceptance Criteria

1. When enqueing PDF jobs, THEN they should ordered such that documents within reference are processed in FIFO order
2. WHEN starting PDF processing THEN the system SHALL enqueue analysis and preprocess jobs in parallel
3. WHEN analysis completes THEN the system SHALL conditionally enqueue OCR job if needed
4. WHEN analysis completes THEN the system SHALL enqueue text extraction job
5. WHEN OCR and analysis complete THEN the system SHALL enqueue table extraction job on GPU queue
6. WHEN text and table extraction complete THEN the system SHALL enqueue embedding job