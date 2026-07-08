from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from extralit_server.enums import QuestionType

QUESTION_COLUMNS_MIN = 1


class QuestionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1)
    description: str | None = None
    type: QuestionType
    columns: list[str] = Field(..., min_length=QUESTION_COLUMNS_MIN)
    settings: dict[str, Any] = Field(default_factory=dict)
    required: bool = False


class QuestionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    columns: list[str] | None = None
    settings: dict[str, Any] | None = None
    required: bool | None = None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schema_id: UUID
    name: str
    title: str
    description: str | None
    type: QuestionType
    columns: list[str]
    settings: dict[str, Any]
    required: bool
    inserted_at: datetime
    updated_at: datetime


class Questions(BaseModel):
    items: list[QuestionRead]
