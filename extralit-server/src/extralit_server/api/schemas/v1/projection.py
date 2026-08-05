from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class WorkspaceProjectionColumn(BaseModel):
    name: str  # flat "Dataset.question" / "Dataset.question.subcol" (spec §3.1)
    dataset_id: UUID
    dataset_name: str
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
