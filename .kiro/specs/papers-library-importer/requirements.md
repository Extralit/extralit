# Requirements Document

## Introduction

The Papers Library Importer feature enables users to import their existing reference libraries from exported .bib files and PDF folders into Extralit workspaces. This feature addresses the critical need for researchers to seamlessly transition their existing document collections from reference management tools (Zotero, Mendeley, etc.) into Extralit for extraction and annotation workflows.

The feature consists of two main components: a backend import service that processes .bib files and PDF folders to create documents with proper metadata, and a frontend import UI that guides users through the upload process and displays import results with options to add, update, or skip documents.

## Requirements

### Requirement 1

**User Story:** As a researcher, I want to upload a .bib file and folder of PDFs to import my reference library into an Extralit workspace, so that I can use my existing document collection for extraction workflows and reference the documents in during the annotation process.

#### Acceptance Criteria

1. WHEN I upload a .bib file THEN the system SHALL parse the bibliographic entries and extract metadata (title, authors, venue, year, DOI, PMID, reference key)
2. WHEN I upload a folder of PDF files THEN the system SHALL process each PDF and attempt to match it with bibliographic entries
3. WHEN a PDF filename matches a .bib entry reference key THEN the system SHALL associate the PDF with that bibliographic entry
4. WHEN I provide a collection tag THEN the system SHALL add this tag to all imported documents' metadata
5. WHEN documents are processed THEN the system SHALL store the reference key as the unique identifier for deduplication
6. IF a PDF cannot be matched to a .bib entry THEN the system SHALL mark it as "failed" and provide error details

### Requirement 2

**User Story:** As a researcher, I want to see a preview of all documents to be imported with their import status, so that I can review and confirm the import before committing changes.

#### Acceptance Criteria

1. WHEN the import process completes analysis THEN the system SHALL display a list of all documents with their import status
2. WHEN viewing the import preview THEN the system SHALL show reference key, title, authors, venue, year, and associated files for each document
3. WHEN a document has a new reference key THEN the system SHALL mark it as "add"
4. WHEN a document has an existing reference key but new/updated files THEN the system SHALL mark it as "update"
5. WHEN a document already exists with no changes THEN the system SHALL mark it as "skip"
6. WHEN a .bib entry has no matching PDF files THEN the system SHALL mark it as "failed"
7. WHEN I review the preview THEN the system SHALL allow me to change the action for individual documents (add/update/skip)

### Requirement 3

**User Story:** As a researcher, I want to execute the bulk import operation and track its progress, so that I can monitor the success of my document imports.

#### Acceptance Criteria

1. WHEN I confirm the import THEN the system SHALL execute the bulk upsert operation asynchronously with one job per reference
2. WHEN the import is running THEN the system SHALL display real-time progress indicators showing completed/total references and files
3. WHEN references with multiple files are being processed THEN the system SHALL upload all associated PDF files to S3 storage and create separate database records
4. WHEN a reference already exists THEN the system SHALL update existing records rather than create duplicates based on reference key
5. WHEN the import completes THEN the system SHALL display a summary of successfully added, updated, skipped, and failed references and files
6. IF individual files fail during import THEN the system SHALL continue processing remaining files and report specific errors with reference context
7. WHEN processing references with multiple files THEN the system SHALL track progress at both reference and file levels

### Requirement 4

**User Story:** As a researcher, I want imported documents to handle multiple files per reference and integrate with existing workspace features, so that I can immediately use them for extraction workflows.

#### Acceptance Criteria

1. WHEN a reference has multiple associated files THEN the system SHALL create separate document records for each file while maintaining the reference relationship
2. WHEN documents are imported THEN the system SHALL store bibliographic metadata in a structured format
3. WHEN documents are imported THEN the system SHALL add collection and source metadata (e.g., `{"collections": ["NetRecalibration/ITN"], "source": "bib_import"}`)
4. WHEN documents are imported THEN the system SHALL make them available in the workspace documents list
5. WHEN I view imported documents THEN the system SHALL display them alongside manually uploaded documents with proper metadata
6. WHEN documents have multiple files per reference THEN the system SHALL group them by reference key in the UI while maintaining individual document records
7. WHEN I select imported documents THEN the system SHALL support all existing document processing features (extraction, annotation, etc.)

### Requirement 5

**User Story:** As a researcher, I want the import process to handle errors gracefully and provide clear feedback, so that I can troubleshoot issues and retry failed imports.

#### Acceptance Criteria

1. WHEN .bib file parsing fails THEN the system SHALL provide specific error messages about malformed entries
2. WHEN PDF files are corrupted or unreadable THEN the system SHALL mark them as failed with detailed error information
3. WHEN file uploads fail due to size or network issues THEN the system SHALL provide retry mechanisms
4. WHEN duplicate reference keys exist in the .bib file THEN the system SHALL handle them appropriately and warn the user
5. WHEN the workspace storage quota is exceeded THEN the system SHALL provide clear error messages and stop the import
6. IF the import process is interrupted THEN the system SHALL allow users to resume or restart the import

### Requirement 6

**User Story:** As a system administrator, I want the import process to be secure and efficient, so that it doesn't compromise system performance or security.

#### Acceptance Criteria$$

1. WHEN users upload files THEN the system SHALL validate file types and sizes before processing
2. WHEN processing large batches THEN the system SHALL implement appropriate rate limiting and batch processing
3. WHEN storing files THEN the system SHALL use the existing secure S3 storage infrastructure
4. WHEN parsing .bib files THEN the system SHALL sanitize input to prevent injection attacks
5. WHEN handling file uploads THEN the system SHALL implement proper virus scanning and validation
6. WHEN processing fails THEN the system SHALL clean up temporary files and partial uploads$$