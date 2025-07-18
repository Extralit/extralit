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
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from argilla_server.database import get_async_db
from argilla_server.security import auth
from argilla_server.models import User, Workspace
from argilla_server.api.policies.v1 import DocumentPolicy, authorize
from argilla_server.contexts.imports import analyze_import_status
from argilla_server.api.schemas.v1.imports import (
    ImportAnalysisRequest,
    ImportAnalysisResponse,
)

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["imports"])


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
        _LOGGER.error(f"Validation error during import analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Validation error during import analysis", "errors": e.errors()},
        )
    except Exception as e:
        _LOGGER.error(f"Error during import analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing import: {str(e)}",
        )


def _validate_analysis_request(analysis_request: ImportAnalysisRequest) -> List[str]:
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

    for reference_key, file_metadata in analysis_request.documents.items():
        if not reference_key or not isinstance(reference_key, str):
            errors.append(f"Invalid reference key: {reference_key}")
            continue

        if file_metadata.document_create.workspace_id != analysis_request.workspace_id:
            errors.append(
                f"Document {reference_key} has mismatched workspace_id: "
                f"{file_metadata.document_create.workspace_id} != {analysis_request.workspace_id}"
            )

    return errors
