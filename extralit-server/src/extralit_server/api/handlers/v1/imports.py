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
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import DocumentPolicy, authorize
from extralit_server.api.schemas.v1.imports import (
    ImportAnalysisRequest,
    ImportAnalysisResponse,
    ImportHistoryCreate,
    ImportHistoryCreateResponse,
    ImportHistoryResponse,
)
from extralit_server.contexts.imports import analyze_import_status, create_import_history
from extralit_server.database import get_async_db
from extralit_server.models import ImportHistory, User, Workspace
from extralit_server.security import auth

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["imports"])


@router.post("/imports/analyze", status_code=status.HTTP_200_OK)
async def analyze_import(
    *,
    analysis_request: ImportAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
) -> ImportAnalysisResponse:
    """
    Analyze import request to determine add/update/skip status for each document.

    This endpoint receives file metadata (not file contents) from the frontend
    and analyzes which documents should be added, updated, skipped, or failed
    based on existing documents in the workspace.

    Args:
        analysis_request: Request containing workspace_id and documents metadata
        db: Database session
        current_user: Authenticated user

    Returns:
        ImportAnalysisResponse with document statuses and summary

    Raises:
        HTTPException: If workspace doesn't exist or other validation errors occur
    """
    await authorize(current_user, DocumentPolicy.create())

    workspace = await Workspace.get(db, analysis_request.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{analysis_request.workspace_id}` not found",
        )

    validation_errors = _validate_analysis_request(analysis_request)
    if validation_errors:
        _LOGGER.warning(f"Import analysis validation errors: {validation_errors}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid import analysis request", "errors": validation_errors},
        )

    try:
        response = await analyze_import_status(db, analysis_request)
        _LOGGER.info(
            f"Import analysis completed for workspace {workspace.id}: "
            f"{response.summary.add_count} to add, "
            f"{response.summary.update_count} to update, "
            f"{response.summary.skip_count} to skip, "
            f"{response.summary.failed_count} failed"
        )
        return response

    except ValidationError as e:
        _LOGGER.error(f"Validation error during import analysis: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Validation error during import analysis", "errors": e.errors()},
        )
    except Exception as e:
        _LOGGER.error(f"Error during import analysis: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing import: {e!s}",
        )


def _validate_analysis_request(analysis_request: ImportAnalysisRequest) -> list[str]:
    """
    Validate the import analysis request.

    Args:
        analysis_request: Request to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not analysis_request.documents:
        errors.append("No documents provided for analysis")
        return errors

    if len(analysis_request.documents) > 1000:
        errors.append(f"Too many documents provided ({len(analysis_request.documents)}). Maximum is 1000.")

    for reference, file_metadata in analysis_request.documents.items():
        if not reference or not isinstance(reference, str):
            errors.append(f"Invalid reference key: {reference}")
            continue

        if file_metadata.document_create.workspace_id != analysis_request.workspace_id:
            errors.append(
                f"Document {reference} has mismatched workspace_id: "
                f"{file_metadata.document_create.workspace_id} != {analysis_request.workspace_id}"
            )

    return errors


@router.post("/imports/history", status_code=status.HTTP_201_CREATED)
async def create_import_history_endpoint(
    *,
    import_history_create: ImportHistoryCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
) -> ImportHistoryCreateResponse:
    """
    Create import history record to store generic tabular dataframe data.

    This endpoint is called after bulk upload completion to store the complete
    import record with the original parsed data (BibTeX, CSV, etc.) in a
    standardized dataframe format.

    Args:
        import_history_create: Import history creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        ImportHistoryResponse with created record information

    Raises:
        HTTPException: If workspace doesn't exist or creation fails
    """
    await authorize(current_user, DocumentPolicy.create())

    workspace = await Workspace.get(db, import_history_create.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{import_history_create.workspace_id}` not found",
        )

    validation_errors = _validate_import_history_request(import_history_create)
    if validation_errors:
        _LOGGER.warning(f"Import history validation errors: {validation_errors}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid import history request", "errors": validation_errors},
        )

    try:
        response = await create_import_history(db, import_history_create, current_user.id)
        _LOGGER.info(
            f"Import history created for workspace {workspace.id}: "
            f"filename={import_history_create.filename}, "
            f"record_id={response.id}"
        )
        return response

    except Exception as e:
        _LOGGER.error(f"Error creating import history: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating import history: {e!s}",
        )


def _validate_import_history_request(import_history_create: ImportHistoryCreate) -> list[str]:
    """
    Validate the import history creation request.

    Args:
        import_history_create: Request to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not import_history_create.filename:
        errors.append("Filename is required")

    if not import_history_create.filename.strip():
        errors.append("Filename cannot be empty")

    if not import_history_create.data:
        errors.append("Data is required")

    # Validate that data contains expected structure for dataframe
    if import_history_create.data:
        if not isinstance(import_history_create.data, dict):
            errors.append("Data must be a dictionary")
        else:
            # Check for expected dataframe structure (schema and data fields)
            if "data" not in import_history_create.data:
                errors.append("Data must contain 'data' field")

            # Validate schema structure if present - only check for reference column
            if "schema" in import_history_create.data:
                schema = import_history_create.data["schema"]
                if not isinstance(schema, dict):
                    errors.append("Schema must be a dictionary")
                elif "fields" in schema:
                    # Check that reference field exists in schema
                    fields = schema.get("fields", [])
                    if isinstance(fields, list):
                        field_names = [field.get("name") for field in fields if isinstance(field, dict)]
                        if "reference" not in field_names:
                            errors.append("Schema must contain a 'reference' field")

            # Validate data structure if present - only check for reference column
            if "data" in import_history_create.data:
                data_rows = import_history_create.data["data"]
                if not isinstance(data_rows, list):
                    errors.append("Data rows must be a list")
                elif data_rows:  # If there are data rows, check for reference column
                    first_row = data_rows[0]
                    if isinstance(first_row, dict) and "reference" not in first_row:
                        errors.append("Data rows must contain a 'reference' column")

    # Validate metadata structure if present
    if import_history_create.metadata is not None:
        if not isinstance(import_history_create.metadata, dict):
            errors.append("Metadata must be a dictionary")
        else:
            # Validate that metadata contains reference-level information
            # Expected structure: {"reference": {"status": "add|update|skip|failed", "associated_files": [...]}}
            for ref_key, ref_metadata in import_history_create.metadata.items():
                if not isinstance(ref_metadata, dict):
                    errors.append(f"Metadata for reference '{ref_key}' must be a dictionary")
                    continue

                # Validate status field
                if "status" in ref_metadata:
                    valid_statuses = ["add", "update", "skip", "failed"]
                    if ref_metadata["status"] not in valid_statuses:
                        errors.append(
                            f"Invalid status '{ref_metadata['status']}' for reference '{ref_key}'. Must be one of: {valid_statuses}"
                        )

                # Validate associated_files field if present
                if "associated_files" in ref_metadata:
                    if not isinstance(ref_metadata["associated_files"], list):
                        errors.append(f"Associated files for reference '{ref_key}' must be a list")

    return errors


@router.get("/imports/history", status_code=status.HTTP_200_OK)
async def list_import_histories(
    *,
    workspace_id: UUID,
    limit: int | None = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
) -> list[ImportHistoryResponse]:
    """
    List import history records for a workspace.

    Args:
        workspace_id: Workspace ID to filter import histories
        limit: Optional limit on number of records to return (for Recent Imports sidebar)
        db: Database session
        current_user: Authenticated user

    Returns:
        List of ImportHistoryResponse records

    Raises:
        HTTPException: If workspace doesn't exist or access denied
    """
    await authorize(current_user, DocumentPolicy.create())

    workspace = await Workspace.get(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{workspace_id}` not found",
        )

    try:
        query = (
            select(ImportHistory)
            .options(selectinload(ImportHistory.user))
            .where(ImportHistory.workspace_id == workspace_id)
            .order_by(ImportHistory.inserted_at.desc())
        )

        if limit is not None:
            query = query.limit(limit)

        result = await db.execute(query)
        import_histories = result.scalars().all()

        # Convert to response format (include metadata but not data for list view)
        response_list = []
        for history in import_histories:
            response_list.append(
                ImportHistoryResponse(
                    id=history.id,
                    workspace_id=history.workspace_id,
                    username=history.user.username,
                    filename=history.filename,
                    created_at=history.inserted_at,
                    metadata=history.metadata_,  # Include metadata in list view
                    data=None,
                )
            )
        _LOGGER.info(f"Retrieved {len(response_list)} import histories for workspace {workspace_id}")
        return response_list

    except Exception as e:
        _LOGGER.error(f"Error retrieving import histories: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving import histories: {e!s}",
        )


@router.get("/imports/history/{history_id}", status_code=status.HTTP_200_OK)
async def get_import_history(
    *,
    history_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
) -> ImportHistoryResponse:
    """
    Get detailed import history record including data and metadata.

    Args:
        history_id: Import history record ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Complete import history record with data and metadata

    Raises:
        HTTPException: If record doesn't exist or access denied
    """
    await authorize(current_user, DocumentPolicy.create())

    try:
        query = select(ImportHistory).options(selectinload(ImportHistory.user)).where(ImportHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()

        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Import history with id `{history_id}` not found",
            )

        # Check workspace access
        workspace = await Workspace.get(db, history.workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        response = ImportHistoryResponse(
            id=history.id,
            workspace_id=history.workspace_id,
            username=history.user.username,
            filename=history.filename,
            created_at=history.inserted_at,
            data=history.data,  # Include data in detailed view
            metadata=history.metadata_,  # Include metadata in detailed view
        )

        _LOGGER.info(f"Retrieved import history {history_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error retrieving import history {history_id}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving import history: {e!s}",
        )
