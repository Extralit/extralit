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

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from extralit._models import ResourceModel

__all__ = ["WorkspaceDoctorCheckResult", "WorkspaceDoctorResponse", "WorkspaceModel"]


class WorkspaceModel(ResourceModel):
    name: str

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        """Validate the name of the workspace is url safe and does not contain underscores"""
        if not re.match(r"^[a-zA-Z0-9.-]+$", value):
            raise ValueError("Workspace name must be url safe and cannot contain underscores")
        return value


class WorkspaceDoctorCheckResult(BaseModel):
    """Result of a single doctor check."""
    
    check_name: str
    status: str
    message: str
    fixed: bool = False


class WorkspaceDoctorResponse(BaseModel):
    """Response from workspace doctor diagnostic."""
    
    workspace_id: UUID
    workspace_name: str
    checks: list[WorkspaceDoctorCheckResult]
    overall_status: str
