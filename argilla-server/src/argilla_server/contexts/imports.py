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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select

from argilla_server.models.database import Document
from argilla_server.api.schemas.v1.documents import DocumentCreate
from argilla_server.api.schemas.v1.imports import (
    FileInfo,
    ImportAnalysisRequest,
    ImportAnalysisResponse,
    ImportDocumentInfo,
    ImportStatus,
    ImportSummary,
)

_LOGGER = logging.getLogger(__name__)


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
    documents_info: Dict[str, ImportDocumentInfo] = {}
    add_count = update_count = skip_count = failed_count = 0

    for reference_key, file_metadata in analysis_request.documents.items():
        try:
            # Check if document already exists
            existing_document = await _check_existing_document(db, file_metadata.document_create)

            # Validate document metadata
            validation_errors = validate_document_metadata(file_metadata.document_create)
            if validation_errors:
                status = ImportStatus.FAILED
                failed_count += 1
                _LOGGER.warning(f"Document {reference_key} failed validation: {validation_errors}")
            elif existing_document is None:
                # New document - add
                status = ImportStatus.ADD
                add_count += 1
            else:
                # Document exists - check if update is needed
                needs_update = await _needs_file_update(existing_document, file_metadata.associated_files)
                if needs_update:
                    status = ImportStatus.UPDATE
                    update_count += 1
                else:
                    status = ImportStatus.SKIP
                    skip_count += 1

            documents_info[reference_key] = ImportDocumentInfo(
                document_create=file_metadata.document_create,
                title=file_metadata.title,
                authors=file_metadata.authors,
                year=file_metadata.year,
                venue=file_metadata.venue,
                associated_files=[f.filename for f in file_metadata.associated_files],
                status=status,
                existing_document_id=existing_document.id if existing_document else None,
            )

        except Exception as e:
            _LOGGER.error(f"Error analyzing document {reference_key}: {str(e)}")
            documents_info[reference_key] = ImportDocumentInfo(
                document_create=file_metadata.document_create,
                title=file_metadata.title,
                authors=file_metadata.authors,
                year=file_metadata.year,
                venue=file_metadata.venue,
                associated_files=[f.filename for f in file_metadata.associated_files],
                status=ImportStatus.FAILED,
                existing_document_id=None,
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


async def _check_existing_document(db: AsyncSession, document_create: DocumentCreate) -> Optional[Document]:
    """
    Check if a document already exists based on reference, DOI, PMID, or ID.
    Reuses the logic from the existing document handler.

    Args:
        db: Database session
        document_create: Document creation data

    Returns:
        Existing document if found, None otherwise
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
        return None

    # Check if a document with the same pmid, url, doi, id, or reference already exists
    result = await db.execute(
        select(Document).where(and_(Document.workspace_id == document_create.workspace_id, or_(*conditions)))
    )
    existing_document = result.scalars().first()

    return existing_document


async def _needs_file_update(existing_document: Document, new_files: List[FileInfo]) -> bool:
    """
    Determine if an existing document needs file updates by comparing file sizes.

    Args:
        existing_document: Existing document in database
        new_files: List of new files to be imported

    Returns:
        True if files need to be updated, False otherwise
    """
    # If no new files, no update needed
    if not new_files:
        return False

    # If existing document has no file, update is needed
    if not existing_document.url:
        return True

    # For now, we'll consider any new files as requiring an update
    # In a more sophisticated implementation, we could compare file hashes
    # or check if the existing file matches any of the new files by size
    return True


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


def validate_document_metadata(document_create: DocumentCreate) -> List[str]:
    """
    Validate DocumentCreate object for import requirements.

    Args:
        document_create: Document creation data to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if not document_create.workspace_id:
        errors.append("workspace_id is required")

    # Check that at least one identifier is provided
    if not any(
        [
            document_create.reference,
            document_create.doi,
            document_create.pmid,
            document_create.url,
            document_create.file_name,
        ]
    ):
        errors.append("At least one identifier (reference, doi, pmid, url, or file_name) is required")

    # Validate DOI format if provided
    if document_create.doi and not _is_valid_doi(document_create.doi):
        errors.append(f"Invalid DOI format: {document_create.doi}")

    # Validate PMID format if provided
    if document_create.pmid and not _is_valid_pmid(document_create.pmid):
        errors.append(f"Invalid PMID format: {document_create.pmid}")

    return errors


def _is_valid_doi(doi: str) -> bool:
    """
    Validate DOI format.

    Args:
        doi: DOI string to validate

    Returns:
        True if DOI format is valid, False otherwise
    """
    if not doi:
        return False

    # Basic DOI validation - should start with "10." and contain a "/"
    return doi.startswith("10.") and "/" in doi


def _is_valid_pmid(pmid: str) -> bool:
    """
    Validate PMID format.

    Args:
        pmid: PMID string to validate

    Returns:
        True if PMID format is valid, False otherwise
    """
    if not pmid:
        return False

    # PMID should be numeric
    return pmid.isdigit()
