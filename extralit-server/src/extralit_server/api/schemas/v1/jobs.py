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
from rq.job import JobStatus


class Job(BaseModel):
    id: str
    status: JobStatus


class WorkflowJobResult(BaseModel):
    """Schema for workflow job results with RQ Groups metadata."""

    id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Job status")
    document_id: Optional[UUID] = Field(None, description="Document ID associated with the job")
    reference: Optional[str] = Field(None, description="Document reference for tracking")
    workspace_id: Optional[UUID] = Field(None, description="Workspace ID")
    workflow_step: Optional[str] = Field(None, description="Current workflow step")
    progress: Optional[float] = Field(None, description="Job progress (0.0-1.0)")
    error: Optional[str] = Field(None, description="Error message if job failed")
    result: Optional[dict[str, Any]] = Field(None, description="Job result data")
    meta: Optional[dict[str, Any]] = Field(None, description="Additional job metadata")
    started_at: Optional[datetime] = Field(None, description="When job was started")
    completed_at: Optional[datetime] = Field(None, description="When job was completed")

    # RQ Groups integration fields
    group_id: Optional[str] = Field(None, description="RQ Group ID for the workflow")
    group_status: Optional[str] = Field(None, description="Status of the entire RQ Group")
    group_progress: Optional[float] = Field(None, description="Overall progress of the group (0.0-1.0)")
    total_jobs: Optional[int] = Field(None, description="Total number of jobs in the group")
    completed_jobs: Optional[int] = Field(None, description="Number of completed jobs in the group")
    failed_jobs: Optional[int] = Field(None, description="Number of failed jobs in the group")
    running_jobs: Optional[int] = Field(None, description="Number of running jobs in the group")
