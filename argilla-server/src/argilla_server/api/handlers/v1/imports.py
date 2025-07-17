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

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    """
    await authorize(current_user, DocumentPolicy.create())

    # Verify workspace exists
    workspace = await Workspace.get(db, analysis_request.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{analysis_request.workspace_id}` not found",
        )

    try:
        # Use the imports context service to analyze the import status
        response = await analyze_import_status(db, analysis_request)
        return response

    except Exception as e:
        _LOGGER.error(f"Error during import analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing import: {str(e)}",
        )
