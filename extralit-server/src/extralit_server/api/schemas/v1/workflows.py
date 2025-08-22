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

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StartWorkflowRequest(BaseModel):
    """Request schema for starting a workflow."""

    document_id: UUID = Field(..., description="Document UUID to process")
    workspace_name: str = Field(..., description="Workspace name")
    reference: Optional[str] = Field(None, description="Document reference for tracking")
    force: bool = Field(False, description="Force restart if workflow already exists")


class StartWorkflowResponse(BaseModel):
    """Response schema for starting a workflow."""

    workflow_id: str = Field(..., description="Workflow ID")
    document_id: str = Field(..., description="Document ID")
    group_id: str = Field(..., description="RQ Group ID for tracking")
    status: str = Field(..., description="Initial workflow status")
    reference: Optional[str] = Field(None, description="Document reference")
    restarted_jobs: Optional[list[str]] = Field(None, description="List of restarted job IDs (for restarts)")


class RestartWorkflowRequest(BaseModel):
    """Request schema for restarting a workflow."""

    document_id: UUID = Field(..., description="Document UUID to restart")
    failed_only: bool = Field(True, description="Only restart failed jobs")


class WorkflowStatusResponse(BaseModel):
    """Response schema for workflow status."""

    workflow_id: str = Field(..., description="Workflow ID")
    document_id: str = Field(..., description="Document ID")
    group_id: str = Field(..., description="RQ Group ID")
    status: str = Field(..., description="Workflow status")
    progress: float = Field(..., description="Progress percentage (0.0-1.0)")
    reference: Optional[str] = Field(None, description="Document reference")
    workspace_name: Optional[str] = Field(None, description="Workspace name")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
    workflow_type: str = Field(..., description="Type of workflow")

    # Job statistics
    total_jobs: int = Field(..., description="Total number of jobs")
    completed_jobs: int = Field(..., description="Number of completed jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    running_jobs: int = Field(..., description="Number of running jobs")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="When workflow was created")
    updated_at: Optional[datetime] = Field(None, description="When workflow was last updated")

    # Error information
    error: Optional[str] = Field(None, description="Error message if workflow failed")

    # Job details (optional, for detailed queries)
    jobs: Optional[list[dict[str, Any]]] = Field(None, description="Detailed job information")


class WorkflowListRequest(BaseModel):
    """Request schema for listing workflows."""

    workspace_name: Optional[str] = Field(None, description="Filter by workspace name")
    status_filter: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(50, description="Maximum number of workflows to return")
