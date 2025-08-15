# Workflow Orchestrator Requirements

## Introduction

The Workflow Orchestrator is a simple, flexible system for chaining jobs together within extralit-server. The system builds upon the existing RQ job infrastructure to provide basic workflow execution, job tracking, and efficient resource utilization. The initial implementation focuses on core workflow capabilities that can be extended over time.

## Requirements

### Requirement 1: Basic Job Chaining

**User Story:** As a developer, I want to chain jobs together in sequence, so that one job can automatically trigger the next job when it completes successfully.

#### Acceptance Criteria

1. WHEN a job completes successfully THEN the system SHALL automatically enqueue its next job in the chain
2. WHEN a job fails THEN the system SHALL stop the workflow chain for that document
3. WHEN defining job chains THEN developers SHALL specify the next job to run after completion
4. WHEN jobs are chained THEN the system SHALL pass relevant data from one job to the next
5. WHEN a workflow starts THEN the system SHALL track the document through each step

### Requirement 2: Document-Centric Job Tracking

**User Story:** As a developer, I want to query job status by document ID or reference, so that I can see the progress of document processing workflows.

#### Acceptance Criteria

1. WHEN querying job status THEN the system SHALL return status information grouped by document ID or reference
2. WHEN a document is being processed THEN the system SHALL show which workflow step is currently running
3. WHEN querying via API THEN the system SHALL return job IDs, status, and basic error information
4. WHEN jobs complete or fail THEN the system SHALL update the document's workflow status
5. WHEN multiple jobs exist for a document THEN the system SHALL show the complete workflow progress

### Requirement 3: Fan-out Job Creation

**User Story:** As a workflow designer, I want a job to create multiple downstream jobs, so that I can implement parallel processing patterns.

#### Acceptance Criteria

1. WHEN a job completes THEN it SHALL be able to enqueue multiple follow-up jobs
2. WHEN creating multiple jobs THEN each SHALL receive appropriate input parameters
3. WHEN fan-out occurs THEN the system SHALL track the relationship between parent and child jobs
4. WHEN multiple downstream jobs are created THEN they SHALL be able to run in parallel
5. WHEN fan-out is used THEN the system SHALL maintain the document context across all jobs

### Requirement 4: Simple Job Configuration

**User Story:** As a developer, I want to configure workflow jobs using decorators and type hints, so that job definitions are clear and maintainable.

#### Acceptance Criteria

1. WHEN defining workflow jobs THEN developers SHALL use decorators to specify job metadata
2. WHEN job functions are defined THEN they SHALL use type hints for parameters and return values
3. WHEN jobs are configured THEN the system SHALL support basic serialization of common data types
4. WHEN job definitions are invalid THEN the system SHALL provide clear error messages
5. WHEN jobs are registered THEN the system SHALL validate basic type compatibility

### Requirement 5: Efficient File References

**User Story:** As a system operator, I want jobs to pass file references instead of file data, so that large files don't clog up the Redis queue.

#### Acceptance Criteria

1. WHEN processing files THEN jobs SHALL pass database IDs or S3 URLs instead of raw file data
2. WHEN jobs need file access THEN they SHALL retrieve files using the provided references
3. WHEN file references are used THEN the system SHALL validate that files are accessible
4. WHEN temporary files are created THEN jobs SHALL clean up after themselves
5. WHEN files are stored THEN the system SHALL use existing S3/MinIO infrastructure

### Requirement 6: CLI Workflow Management

**User Story:** As a developer, I want to enqueue complete workflow chains for documents via CLI, so that I can easily rerun processing when code changes or recover from failures.

#### Acceptance Criteria

1. WHEN using CLI THEN developers SHALL be able to enqueue an entire workflow chain for a specific reference
2. WHEN enqueueing a workflow THEN the system SHALL start from the first step and run through all configured steps
3. WHEN rerunning workflows THEN the system SHALL allow reprocessing of documents with updated code
4. WHEN specifying a document THEN the CLI SHALL validate that the document exists and is accessible
5. WHEN workflow is enqueued THEN the system SHALL log the action and return the initial job ID

### Requirement 7: Multi-Worker Support

**User Story:** As a system operator, I want to run multiple workers to increase throughput, so that the system can process more documents simultaneously.

#### Acceptance Criteria

1. WHEN multiple workers are running THEN they SHALL process jobs from the same queues
2. WHEN workers are scaled up THEN job processing throughput SHALL increase
3. WHEN workers are added or removed THEN the system SHALL continue operating normally
4. WHEN jobs are distributed THEN workers SHALL coordinate to avoid duplicate processing
5. WHEN scaling occurs THEN the system SHALL maintain job execution order where required