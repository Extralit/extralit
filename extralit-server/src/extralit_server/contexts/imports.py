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
from uuid import UUID
from os.path import basename
from typing import Dict, List, Optional

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select

from extralit_server.models.database import Document, ImportHistory
from extralit_server.models import Document
from extralit_server.api.schemas.v1.documents import DocumentCreate, DocumentListItem
from extralit_server.api.schemas.v1.imports import (
    FileInfo,
    DocumentMetadata,
    ImportAnalysisRequest,
    ImportAnalysisResponse,
    DocumentImportAnalysis,
    ImportStatus,
    ImportSummary,
    DocumentsBulkCreate,
    DocumentsBulkResponse,
    ImportHistoryCreate,
    ImportHistoryCreateResponse,
)
from extralit_server.jobs.document_jobs import upload_reference_documents_job

_LOGGER = logging.getLogger(__name__)


async def create_document(db: "AsyncSession", dataset_create: DocumentCreate) -> DocumentListItem:
    document = await Document.create(
        db,
        id=dataset_create.id,
        reference=dataset_create.reference,
        url=dataset_create.url,
        file_name=dataset_create.file_name,
        pmid=dataset_create.pmid,
        doi=dataset_create.doi,
        workspace_id=dataset_create.workspace_id,
        metadata_=dataset_create.metadata,
    )

    return DocumentListItem.model_validate(document)


async def update_document(db: "AsyncSession", document: Document) -> Document:
    """Update an existing document in the database."""
    await document.save(db, autocommit=True)
    return document


async def delete_documents(
    db: "AsyncSession",
    workspace_id: UUID,
    id: Optional[UUID] = None,
    reference: Optional[str] = None,
) -> List[DocumentListItem]:
    async with db.begin_nested():
        params = [Document.workspace_id == workspace_id]
        if id is not None and id != "":
            params.append(Document.id == id)
        if reference:
            params.append(Document.reference == reference)
        documents = await Document.delete_many(db=db, conditions=params, autocommit=False)

    await db.commit()
    documents = [DocumentListItem.model_validate(doc) for doc in documents]
    return documents


async def list_documents(db: "AsyncSession", workspace_id: UUID) -> List[DocumentListItem]:
    result = await db.execute(select(Document).filter_by(workspace_id=workspace_id))
    documents: List[Document] = result.scalars().all()
    documents = [DocumentListItem.model_validate(doc) for doc in documents]

    return documents


async def find_existing_documents(
    db: AsyncSession,
    workspace_id: UUID,
    document_id: Optional[UUID] = None,
    reference: Optional[str] = None,
    file_name: Optional[str] = None,
    pmid: Optional[str] = None,
    doi: Optional[str] = None,
    url: Optional[str] = None,
) -> List[DocumentListItem]:
    """
    Find existing documents that matches any of provided criteria.

    Args:
        db: Database session
        workspace_id: UUID of the workspace to search in
        document_id: Optional document ID to match
        reference: Optional reference to match
        pmid: Optional PMID to match
        doi: Optional DOI to match
        url: Optional URL to match

    Returns:
        List of existing documents matching the criteria (empty if none found)
    """
    conditions = []

    if document_id:
        conditions.append(Document.id == document_id)
    if reference:
        conditions.append(Document.reference == reference)
    if file_name:
        conditions.append(Document.file_name == file_name)
    if pmid:
        conditions.append(Document.pmid == pmid)
    if doi:
        conditions.append(Document.doi == doi)
    if url:
        conditions.append(Document.url == url)

    if not conditions:
        return []

    # Find documents matching any of the conditions within the workspace
    result = await db.execute(select(Document).where(and_(Document.workspace_id == workspace_id, or_(*conditions))))
    existing_documents = result.scalars().all()

    return [DocumentListItem.model_validate(doc) for doc in existing_documents]


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
            existing_documents_list = await find_existing_documents(
                db=db,
                workspace_id=file_metadata.document_create.workspace_id,
                document_id=file_metadata.document_create.id,
                reference=file_metadata.document_create.reference,
                pmid=file_metadata.document_create.pmid,
                doi=file_metadata.document_create.doi,
                url=file_metadata.document_create.url,
            )

            # Convert DocumentListItem back to Document objects for _has_new_files compatibility
            existing_documents = []
            if existing_documents_list:
                for doc_item in existing_documents_list:
                    result = await db.execute(select(Document).where(Document.id == doc_item.id))
                    doc = result.scalars().first()
                    if doc:
                        existing_documents.append(doc)

            validation_errors = validate_document_metadata(file_metadata)

            if validation_errors:
                status = ImportStatus.FAILED
                failed_count += 1
            elif not existing_documents:
                status = ImportStatus.ADD
                add_count += 1
            else:
                has_new_files = await _has_new_files(existing_documents, file_metadata.associated_files)
                if has_new_files:
                    status = ImportStatus.UPDATE
                    update_count += 1
                else:
                    status = ImportStatus.SKIP
                    skip_count += 1

            documents_info[reference] = DocumentImportAnalysis(
                document_create=file_metadata.document_create,
                associated_files=[f.filename for f in file_metadata.associated_files],
                status=status,
                validation_errors=validation_errors if validation_errors else [],
            )

        except Exception as e:
            _LOGGER.error(f"Error analyzing document {reference}: {str(e)}")
            documents_info[reference] = DocumentImportAnalysis(
                document_create=file_metadata.document_create,
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


async def _has_new_files(existing_documents: List[Document], new_files: List[FileInfo]) -> bool:
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

    if not existing_documents or not any(doc.url for doc in existing_documents):
        return True

    existing_filenames = set()
    for doc in existing_documents:
        if doc.file_name:
            existing_filenames.add(basename(doc.file_name))

    for file_info in new_files:
        if basename(file_info.filename) not in existing_filenames:
            return True
        # else:
        #     # Compare file size
        #     for doc in existing_documents:
        #         if doc.file_name and basename(doc.file_name) == basename(file_info.filename):
        #             if file_info.size and file_info.size != doc.size: # TODO get doc.size
        #                 return True
        #             break
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


async def process_bulk_upload(
    bulk_create: DocumentsBulkCreate,
    files: List[UploadFile],
    user_id: str,
) -> DocumentsBulkResponse:
    """
    Process bulk document upload with associated PDF files using reference-based jobs.

    This function creates one job per reference that handles multiple files for that reference.
    It validates all files, groups them by reference, and creates reference-based upload jobs
    for efficient processing and progress tracking.

    Args:
        bulk_create: DocumentsBulkCreate with reference-based document information
        files: List of PDF files to upload
        user_id: ID of the user creating the documents

    Returns:
        DocumentsBulkResponse with job IDs indexed by reference and validation results
    """
    from extralit_server.jobs import DEFAULT_QUEUE

    # Create a mapping of filenames to file objects for quick lookup
    file_mapping = {file.filename: file for file in files} if files else {}

    # Validate that all referenced files are included in the upload
    missing_files = []
    all_referenced_files = set()

    for doc in bulk_create.documents:
        for filename in doc.associated_files:
            all_referenced_files.add(filename)
            if filename not in file_mapping:
                missing_files.append(filename)

    # Only validate missing files if there are any referenced files
    if all_referenced_files and missing_files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Referenced files not found in upload: {', '.join(missing_files)}",
        )

    # Group documents by reference (should be 1:1 but validate)
    reference_to_doc = {}
    for doc in bulk_create.documents:
        if doc.reference in reference_to_doc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate reference key found: {doc.reference}",
            )
        reference_to_doc[doc.reference] = doc

    # Process each reference and create reference-based jobs
    job_ids = {}
    failed_validations = []

    for reference, doc in reference_to_doc.items():
        try:
            # Validate and read all files for this reference
            file_data_list = []
            reference_failed = False

            # Handle documents with no associated files
            if not doc.associated_files:
                # Create a reference-based job for documents without files
                job = DEFAULT_QUEUE.enqueue(
                    upload_reference_documents_job,
                    reference=reference,
                    reference_data=doc.document_create.model_dump(),
                    file_data_list=[],
                    user_id=user_id,
                    job_timeout=None,  # No timeout for large uploads
                )

                # Store job ID mapped to reference key for frontend tracking
                job_ids[reference] = job.id
                _LOGGER.info(f"Created reference-based job {job.id} for reference {reference} with no files")
                continue

            for filename in doc.associated_files:
                try:
                    file = file_mapping[filename]

                    if not file.filename or not file.filename.lower().endswith(".pdf"):
                        failed_validations.append(f"{filename}: Not a PDF file")
                        reference_failed = True
                        continue

                    # Read file content
                    file_content = await file.read()

                    # Validate file size (100 MB limit)
                    if len(file_content) > 100 * 1024 * 1024:
                        failed_validations.append(f"{filename}: File exceeds maximum size of 100 MB")
                        reference_failed = True
                        continue

                    # Reset file position for potential future reads
                    await file.seek(0)

                    file_data_list.append((filename, file_content))

                except Exception as e:
                    _LOGGER.error(f"Error processing file {filename} for reference {reference}: {str(e)}")
                    failed_validations.append(f"{filename}: {str(e)}")
                    reference_failed = True

            # Skip this reference if any files failed validation
            if reference_failed:
                continue

            # Set a default filename if not already set (use first file)
            if not doc.document_create.file_name and file_data_list:
                doc.document_create.file_name = file_data_list[0][0]

            # Create a reference-based job for multiple files
            job = DEFAULT_QUEUE.enqueue(
                upload_reference_documents_job,
                reference=reference,
                reference_data=doc.document_create.model_dump(),
                file_data_list=file_data_list,
                user_id=user_id,
                job_timeout=None,  # No timeout for large uploads
            )

            # Store job ID mapped to reference key for frontend tracking
            job_ids[reference] = job.id
            _LOGGER.info(
                f"Created reference-based job {job.id} for reference {reference} with {len(file_data_list)} files"
            )

        except Exception as e:
            _LOGGER.error(f"Error processing reference {reference}: {str(e)}")
            failed_validations.append(f"{reference}: {str(e)}")

    return DocumentsBulkResponse(
        job_ids=job_ids, total_documents=len(reference_to_doc), failed_validations=failed_validations
    )


async def create_import_history(
    db: AsyncSession, import_history_create: ImportHistoryCreate, user_id: UUID | str
) -> ImportHistoryCreateResponse:
    """
    Create an import history record to store tabular dataframe data and import metadata.

    This function is called after bulk upload completion to store the complete
    import record with the original parsed data (BibTeX, CSV, etc.) in a
    standardized dataframe format, along with metadata about import status
    and associated files for each reference.

    Args:
        db: Database session
        import_history_create: Import history creation data
        user_id: ID of the user creating the import history

    Returns:
        ImportHistoryResponse with created record information

    Raises:
        HTTPException: If workspace doesn't exist or creation fails
    """
    try:
        import_history = ImportHistory(
            workspace_id=import_history_create.workspace_id,
            user_id=user_id,
            filename=import_history_create.filename,
            data=import_history_create.data,
            metadata_=import_history_create.metadata,
        )

        db.add(import_history)
        await db.commit()
        await db.refresh(import_history)

        _LOGGER.info(
            f"Created import history record {import_history.id} for workspace {import_history.workspace_id} "
            f"with filename {import_history.filename}"
        )

        return ImportHistoryCreateResponse(
            id=import_history.id,
            workspace_id=import_history.workspace_id,
            filename=import_history.filename,
            created_at=import_history.inserted_at,
        )

    except Exception as e:
        _LOGGER.error(f"Error creating import history: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating import history: {str(e)}",
        )
