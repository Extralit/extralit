from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ProjectionCell(BaseModel):
    question_name: str
    value: Any | None = None
    source: Literal["response", "suggestion"] | None = None  # None => neither exists yet


class ProjectionRecord(BaseModel):
    record_id: UUID
    schema_id: UUID
    reference: str
    cells: list[ProjectionCell]


class ProjectionView(BaseModel):
    reference: str
    records: list[ProjectionRecord]
    total_records: int
