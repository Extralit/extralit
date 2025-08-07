# Requirements Document

## Introduction

The Papers Library Importer feature enables users to import their existing reference libraries from exported .bib files and PDF folders into Extralit workspaces. This feature addresses the critical need for researchers to seamlessly transition their existing document collections from reference management tools (Zotero, Mendeley, etc.) into Extralit for extraction and annotation workflows.

The feature consists of two main components: a backend import service that processes .bib files and PDF folders to create documents with proper metadata, and a frontend import UI that guides users through the upload process and displays import results with options to add, update, or skip documents.

## Requirements

### Requirement 1

**User Story:** As a researcher, I want to upload a bibliography file (.bib or .csv) and folder of PDFs to import my reference library into an Extralit workspace, so that I can use my existing document collection for extraction workflows and reference the documents in during the annotation process.

#### Acceptance Criteria

1. WHEN I upload a .bib file THEN the system SHALL parse the bibliographic entries and extract metadata (title, authors, venue, year, DOI, PMID, reference)
2. WHEN I upload a .csv file THEN the system SHALL parse the tabular data and allow me to select the reference column and files column for PDF matching
3. WHEN I upload a folder of PDF files THEN the system SHALL process each PDF and attempt to match it with bibliographic entries using maximum prefix path matching
4. WHEN a PDF file path has a maximum prefix match with a bibliography entry file path THEN the system SHALL associate the PDF with that bibliographic entry
5. WHEN I provide a collection tag THEN the system SHALL add this tag to all imported documents' metadata
6. WHEN documents are processed THEN the system SHALL store the reference as the unique identifier for deduplication
7. WHEN I upload files in any order (bibliography first or PDFs first) THEN the system SHALL allow me to proceed to the next step
8. IF a PDF cannot be matched to a bibliography entry THEN the system SHALL mark it as unmatched but still allow import

### Requirement 2

**User Story:** As a researcher, I want to see a preview of all documents to be imported with their import status and choose whether to import references without PDFs, so that I can review and confirm the import before committing changes.

#### Acceptance Criteria

1. WHEN the import process completes analysis THEN the system SHALL display a list of all documents with their import status
2. WHEN viewing the import preview THEN the system SHALL show reference, title, authors, venue, year, and associated files for each document
3. WHEN a document has a new reference THEN the system SHALL mark it as "add"
4. WHEN a document has an existing reference but new/updated files THEN the system SHALL mark it as "update"
5. WHEN a document already exists with no changes THEN the system SHALL mark it as "skip"
6. WHEN a bibliography entry has no matching PDF files THEN the system SHALL mark it as "no files" but still allow import
7. WHEN I review the preview THEN the system SHALL allow me to change the action for individual documents (add/update/skip/ignore)
8. WHEN I review the preview THEN the system SHALL provide an option to import only references with matched PDFs or import all references including those without PDFs
9. WHEN I select "only with PDFs" THEN the system SHALL automatically set references without PDFs to "ignore" status

### Requirement 3

**User Story:** As a researcher, I want to execute the bulk import operation and track its progress, so that I can monitor the success of my document imports.

#### Acceptance Criteria

1. WHEN I confirm the import THEN the system SHALL execute the bulk upsert operation asynchronously with one job per reference
2. WHEN the import is running THEN the system SHALL display real-time progress indicators showing completed/total references and files
3. WHEN references with multiple files are being processed THEN the system SHALL upload all associated PDF files to S3 storage and create separate database records
4. WHEN a reference already exists THEN the system SHALL update existing records rather than create duplicates based on reference
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
6. WHEN documents have multiple files per reference THEN the system SHALL group them by reference in the UI while maintaining individual document records
7. WHEN I select imported documents THEN the system SHALL support all existing document processing features (extraction, annotation, etc.)

### Requirement 5

**User Story:** As a researcher, I want the import process to handle errors gracefully and provide clear feedback, so that I can troubleshoot issues and retry failed imports.

#### Acceptance Criteria

1. WHEN .bib file parsing fails THEN the system SHALL provide specific error messages about malformed entries
2. WHEN .csv file parsing fails THEN the system SHALL provide specific error messages about malformed data and allow column selection
3. WHEN PDF files are corrupted or unreadable THEN the system SHALL mark them as failed with detailed error information
4. WHEN file upload jobs fail due to size or network issues THEN the system SHALL provide retry mechanisms
5. WHEN duplicate references exist in the bibliography file THEN the system SHALL handle them appropriately and warn the user
6. WHEN the workspace storage quota is exceeded THEN the system SHALL provide clear error messages and stop the import
7. IF the import process is interrupted THEN the system SHALL allow users to resume or restart the import

### Requirement 6

**User Story:** As a system administrator, I want the import process to be secure and efficient, so that it doesn't compromise system performance or security.

#### Acceptance Criteria$$

1. WHEN users upload files THEN the system SHALL validate file types and sizes before processing
2. WHEN processing large batches THEN the system SHALL implement appropriate rate limiting and batch processing
3. WHEN storing files THEN the system SHALL use the existing secure S3 storage infrastructure
4. WHEN parsing .bib files THEN the system SHALL sanitize input to prevent injection attacks
5. WHEN handling file uploads THEN the system SHALL implement proper virus scanning and validation
6. WHEN processing fails THEN the system SHALL clean up temporary files and partial uploads$$

### Requirement 7

**User Story:** As a researcher, I want the import modal to have proper flow control and not require confirmation to close after successful completion, so that I have a smooth user experience.

#### Acceptance Criteria

1. WHEN the import process is in progress THEN the system SHALL require confirmation before allowing me to close the modal
2. WHEN the import process has completed successfully THEN the system SHALL not require confirmation to close the modal
3. WHEN I navigate between steps during the import process THEN the system SHALL preserve my uploaded data
4. WHEN I return to a previous step THEN the system SHALL show my previously uploaded files and selections5. W
HEN I close the import modal after successful completion THEN the system SHALL refresh the recent import list on the home screen