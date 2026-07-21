from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ProjectionCell(BaseModel):
    question_name: str
    value: Any | None = None
    source: Literal["response", "suggestion"] | None = None  # None => neither exists yet
    # Enriched provenance (spec §3.2): consumers link and attribute with zero extra calls.
    record_id: UUID | None = None
    agent: str | None = None
    score: float | list[float] | None = None


class ProjectionRecord(BaseModel):
    record_id: UUID
    schema_id: UUID
    reference: str
    cells: list[ProjectionCell]


class ProjectionView(BaseModel):
    reference: str
    records: list[ProjectionRecord]
    total_records: int


class WorkspaceProjectionColumn(BaseModel):
    name: str  # flat "Schema.question" / "Schema.question.subcol" (spec §3.1)
    schema_id: UUID
    schema_name: str
    question_name: str
    sub_column: str | None = None
    dtype: str  # the question type value; the grid treats it as informational


class WorkspaceProjectionCell(BaseModel):
    value: Any | None = None
    source: Literal["response", "suggestion"]
    record_id: UUID
    agent: str | None = None
    score: float | list[float] | None = None


class WorkspaceProjectionRow(BaseModel):
    reference: str
    row_index: int
    cells: dict[str, WorkspaceProjectionCell]  # keyed by column name; absent cells omitted


class WorkspaceProjection(BaseModel):
    columns: list[WorkspaceProjectionColumn]
    rows: list[WorkspaceProjectionRow]
    total_references: int
