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
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from argilla_server.database import get_async_db
from argilla_server.security import auth
from argilla_server.models import User, Workspace
from argilla_server.models.database import Document
from argilla_server.api.policies.v1 import DocumentPolicy, authorize
from argilla_server.api.handlers.v1.documents import check_existing_document
from argilla_server.api.schemas.v1.imports import (
    ImportAnalysisRequest,
    ImportAnalysisResponse,
    ImportDocumentInfo,
    ImportSummary,
    ImportStatus,
)

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["imports"])


def determine_import_status(existing_document: Document, new_files: list, reference_key: str) -> ImportStatus:
    """Determine the import status based on existing document and new files."""
    if existing_document is None:
        # No existing document found
        if new_files:
            return ImportStatus.ADD
        else:
            # No files to import
            return ImportStatus.FAILED

    # Document exists, check if we need to update
    if new_files:
        # For now, we'll mark as update if there are new files
        # In a more sophisticated implementation, we could compare file sizes/hashes
        return ImportStatus.UPDATE
    else:
        # Document exists but no new files
        return ImportStatus.SKIP


@router.post("/imports/analyze", status_code=status.HTTP_200_OK, response_model=ImportAnalysisResponse)
async def analyze_import(
    *,
    analysis_request: ImportAnalysisRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
) -> ImportAnalysisResponse:
    """
    Analyze import request to determine add/update/skip status for each document.

    This endpoint receives file metadata (not file contents) from the frontend
    and analyzes which documents should be added, updated, skipped, or failed
    based on existing documents in the workspace.
    """
    await authorize(current_user, DocumentPolicy.create())

    # Verify workspace exists
    workspace = await Workspace.get(db, analysis_request.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{analysis_request.workspace_id}` not found",
        )

    documents_info: Dict[str, ImportDocumentInfo] = {}

    # Counters for summary
    add_count = 0
    update_count = 0
    skip_count = 0
    failed_count = 0

    try:
        for reference_key, file_metadata in analysis_request.documents.items():
            try:
                # Check if document already exists
                existing_document = await check_existing_document(db, file_metadata.document_create)

                # Determine import status
                status_result = determine_import_status(
                    existing_document, file_metadata.associated_files, reference_key
                )

                # Update counters
                if status_result == ImportStatus.ADD:
                    add_count += 1
                elif status_result == ImportStatus.UPDATE:
                    update_count += 1
                elif status_result == ImportStatus.SKIP:
                    skip_count += 1
                elif status_result == ImportStatus.FAILED:
                    failed_count += 1

                # Create document info
                documents_info[reference_key] = ImportDocumentInfo(
                    document_create=file_metadata.document_create,
                    title=file_metadata.title,
                    authors=file_metadata.authors,
                    year=file_metadata.year,
                    venue=file_metadata.venue,
                    associated_files=[f.filename for f in file_metadata.associated_files],
                    status=status_result,
                    existing_document_id=existing_document.id if existing_document else None,
                )

            except Exception as e:
                _LOGGER.error(f"Error analyzing document {reference_key}: {str(e)}")
                # Mark as failed if there's an error analyzing this document
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

        # Create summary
        summary = ImportSummary(
            total_documents=len(analysis_request.documents),
            add_count=add_count,
            update_count=update_count,
            skip_count=skip_count,
            failed_count=failed_count,
        )

        return ImportAnalysisResponse(
            documents=documents_info,
            summary=summary,
        )

    except Exception as e:
        _LOGGER.error(f"Error during import analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing import: {str(e)}",
        )
