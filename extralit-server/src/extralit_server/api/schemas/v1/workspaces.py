from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Workspace(BaseModel):
    id: UUID
    name: str
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    id: UUID | None = None
    name: str = Field(min_length=1)


class Workspaces(BaseModel):
    items: list[Workspace]


class WorkspaceUserCreate(BaseModel):
    user_id: UUID


class WorkspaceDoctorCheckResult(BaseModel):
    check_name: str
    status: str  # "ok", "warning", "error"
    message: str
    fixed: bool = False


class WorkspaceDoctorResponse(BaseModel):
    workspace_id: UUID
    workspace_name: str
    checks: list[WorkspaceDoctorCheckResult]
    overall_status: str  # "healthy", "issues_found", "issues_fixed"
