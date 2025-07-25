# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Dict, List, Optional

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select

from argilla_server.models.database import Document
from argilla_server.api.schemas.v1.documents import DocumentCreate
from argilla_server.api.schemas.v1.imports import (
    FileInfo,
    DocumentMetadata,
    ImportAnalysisRequest,
    ImportAnalysisResponse,
    DocumentImportAnalysis,
    ImportStatus,
    ImportSummary,
    DocumentsBulkCreate,
    DocumentsBulkResponse,
)
from argilla_server.jobs.document_jobs import upload_document_job

_LOGGER = logging.getLogger(__name__)


async def _check_existing_documents(db: AsyncSession, document_create: DocumentCreate) -> List[Document]:
    """
    Check if documents already exist based on reference, DOI, PMID, or ID.
    Reuses the logic from the existing document handler but returns all matching documents.

    Args:
        db: Database session
        document_create: Document creation data

    Returns:
        List of existing documents if found, empty list otherwise
    """
    conditions = []

    if document_create.pmid:
        conditions.append(Document.pmid == document_create.pmid)
    if document_create.url:
        conditions.append(Document.url == document_create.url)
    if document_create.doi:
        conditions.append(Document.doi == document_create.doi)
    if document_create.id:
        conditions.append(Document.id == document_create.id)
    if document_create.reference:
        conditions.append(Document.reference == document_create.reference)

    if not conditions:
        return []

    # Check if documents with the same pmid, url, doi, id, or reference already exist
    result = await db.execute(
        select(Document).where(and_(Document.workspace_id == document_create.workspace_id, or_(*conditions)))
    )
    existing_documents = result.scalars().all()

    return list(existing_documents)


async def analyze_import_status(db: AsyncSession, analysis_request: ImportAnalysisRequest) -> ImportAnalysisResponse:
    """
    Analyze import status for documents by checking existing documents and determining
    whether each document should be added, updated, skipped, or marked as failed.

    Args:
        db: Database session
        analysis_request: Request containing workspace_id and documents metadata

    Returns:
        ImportAnalysisResponse with document statuses and summary
    """
    documents_info: Dict[str, DocumentImportAnalysis] = {}
    add_count = update_count = skip_count = failed_count = 0

    for reference, file_metadata in analysis_request.documents.items():
        try:
            existing_documents = await _check_existing_documents(db, file_metadata.document_create)

            validation_errors = validate_document_metadata(file_metadata)
            if validation_errors:
                status = ImportStatus.FAILED
                failed_count += 1

            elif not existing_documents:
                status = ImportStatus.ADD
                add_count += 1
            else:
                has_new_files = await _has_new_files(db, existing_documents, file_metadata.associated_files)
                if has_new_files:
                    status = ImportStatus.UPDATE
                    update_count += 1
                else:
                    status = ImportStatus.SKIP
                    skip_count += 1

            documents_info[reference] = DocumentImportAnalysis(
                document_create=file_metadata.document_create,
                title=file_metadata.title,
                authors=file_metadata.authors,
                year=file_metadata.year,
                venue=file_metadata.venue,
                associated_files=[f.filename for f in file_metadata.associated_files],
                status=status,
                validation_errors=validation_errors if validation_errors else [],
            )

        except Exception as e:
            _LOGGER.error(f"Error analyzing document {reference}: {str(e)}")
            documents_info[reference] = DocumentImportAnalysis(
                document_create=file_metadata.document_create,
                title=file_metadata.title,
                authors=file_metadata.authors,
                year=file_metadata.year,
                venue=file_metadata.venue,
                associated_files=[f.filename for f in file_metadata.associated_files],
                status=ImportStatus.FAILED,
                validation_errors=[f"Error analyzing document: {str(e)}"],
            )
            failed_count += 1

    summary = ImportSummary(
        total_documents=len(analysis_request.documents),
        add_count=add_count,
        update_count=update_count,
        skip_count=skip_count,
        failed_count=failed_count,
    )

    return ImportAnalysisResponse(documents=documents_info, summary=summary)


async def _has_new_files(db: AsyncSession, existing_documents: List[Document], new_files: List[FileInfo]) -> bool:
    """
    Check if there are new files to add to existing documents.

    This function determines if any of the new files are not already associated with the documents.
    It's specifically designed to handle supplemental files being added to a reference that
    already has the main PDF uploaded.

    Args:
        db: Database session
        existing_documents: List of existing documents in database
        new_files: List of new files to be imported

    Returns:
        True if there are new files to add, False otherwise
    """
    # If no new files, no update needed
    if not new_files:
        return False

    # If no existing documents or no documents with files, update is needed
    if not existing_documents or not any(doc.url for doc in existing_documents):
        return True

    # Extract the filenames from all existing documents
    existing_filenames = set()
    for doc in existing_documents:
        if doc.file_name:
            existing_filenames.add(doc.file_name)

    # Check if any of the new files have names that don't exist in the existing files
    for file_info in new_files:
        if file_info.filename not in existing_filenames:
            return True

    # No new files found
    return False


def compare_file_sizes(existing_size: Optional[int], new_files: List[FileInfo]) -> bool:
    """
    Compare file sizes to determine if file updates are needed.

    Args:
        existing_size: Size of existing file in bytes (None if no existing file)
        new_files: List of new files with size information

    Returns:
        True if files should be updated, False otherwise
    """
    if not new_files:
        return False

    if existing_size is None:
        return True

    # Check if any new file has a different size than the existing file
    for file_info in new_files:
        if file_info.size != existing_size:
            return True

    return False


def validate_document_metadata(file_metadata: DocumentMetadata) -> List[str]:
    """
    Validate DocumentCreate object for import requirements.

    Args:
        document_create: Document creation data to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not file_metadata.document_create.workspace_id:
        errors.append("workspace_id is required")

    if not file_metadata.associated_files:
        errors.append("At least one associated file is required")

    if not any(
        [
            file_metadata.document_create.reference,
            file_metadata.document_create.doi,
            file_metadata.document_create.pmid,
            file_metadata.document_create.url,
            file_metadata.document_create.file_name,
        ]
    ):
        errors.append("At least one identifier (reference, doi, pmid, url, or file_name) is required")

    # Validate DOI format if provided
    if file_metadata.document_create.doi and not _is_valid_doi(file_metadata.document_create.doi):
        errors.append(f"Invalid DOI format: {file_metadata.document_create.doi}")

    # Validate PMID format if provided
    if file_metadata.document_create.pmid and not _is_valid_pmid(file_metadata.document_create.pmid):
        errors.append(f"Invalid PMID format: {file_metadata.document_create.pmid}")

    return errors


def _is_valid_doi(doi: str) -> bool:
    if not doi:
        return False

    # Basic DOI validation - should start with "10." and contain a "/"
    return doi.startswith("10.") and "/" in doi


def _is_valid_pmid(pmid: str) -> bool:
    if not pmid:
        return False

    # PMID should be numeric
    return pmid.isdigit()


async def check_existing_document(db: AsyncSession, document_create: DocumentCreate) -> Optional[Document]:
    """
    Check if a document already exists based on reference, DOI, PMID, or ID.

    Args:
        db: Database session
        document_create: Document creation data

    Returns:
        Existing document if found, None otherwise
    """
    # Add conditions for non-empty attributes
    conditions = []
    if document_create.pmid:
        conditions.append(Document.pmid == document_create.pmid)
    if document_create.url:
        conditions.append(Document.url == document_create.url)
    if document_create.doi:
        conditions.append(Document.doi == document_create.doi)
    if document_create.id:
        conditions.append(Document.id == document_create.id)
    if document_create.reference:
        conditions.append(Document.reference == document_create.reference)

    if not conditions:
        return None

    # Check if a document with the same pmid, url, or doi already exists
    existing_document = await db.execute(
        select(Document).where(and_(Document.workspace_id == document_create.workspace_id, or_(*conditions)))
    )
    existing_document = existing_document.scalars().first()

    return existing_document


async def process_bulk_upload(
    bulk_create: DocumentsBulkCreate,
    files: List[UploadFile],
) -> DocumentsBulkResponse:
    """
    Process bulk document upload with associated PDF files.

    Args:
        bulk_metadata: DocumentsBulkCreate
        files: List of PDF files to upload

    Returns:
        DocumentsBulkResponse with job IDs and validation results
    """

    # Create a mapping of filenames to file objects for quick lookup
    file_mapping = {file.filename: file for file in files}

    # Validate that all referenced files are included in the upload
    missing_files = []
    for doc in bulk_create.documents:
        if doc.associated_file not in file_mapping:
            missing_files.append(doc.associated_file)

    if missing_files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Referenced files not found in upload: {', '.join(missing_files)}",
        )

    # Process each document and create jobs
    job_ids = {}
    failed_validations = []

    for doc in bulk_create.documents:
        try:
            # Get the associated file
            file = file_mapping[doc.associated_file]

            if not file.filename or not file.filename.lower().endswith(".pdf"):
                failed_validations.append(f"{file.filename}: Not a PDF file")
                continue

            # Read file content
            file_content = await file.read()

            # Validate file size (optional, adjust limits as needed)
            if len(file_content) > 100 * 1024 * 1024:  # 100 MB limit
                failed_validations.append(f"{file.filename}: File exceeds maximum size of 100 MB")
                continue

            # Reset file position for potential future reads
            await file.seek(0)

            # Set filename if not already set
            if not doc.document_create.file_name:
                doc.document_create.file_name = file.filename

            # Create a job for document upload
            job = upload_document_job.delay(document_data=doc.document_create.model_dump(), file_data=file_content)

            # Store job ID mapped to reference key for tracking
            job_ids[doc.reference] = job.id

        except Exception as e:
            _LOGGER.error(f"Error processing document {doc.reference}: {str(e)}")
            failed_validations.append(f"{doc.reference}: {str(e)}")

    return DocumentsBulkResponse(
        job_ids=job_ids, total_documents=len(bulk_create.documents), failed_validations=failed_validations
    )
