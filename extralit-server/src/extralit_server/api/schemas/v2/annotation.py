from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from extralit_server.enums import ResponseStatus, SuggestionType


class SuggestionUpsert(BaseModel):
    question_id: UUID
    value: Any
    score: float | list[float] | None = None
    agent: str | None = None
    type: SuggestionType | None = None


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    question_id: UUID
    value: Any
    score: float | list[float] | None
    agent: str | None
    type: SuggestionType | None
    inserted_at: datetime
    updated_at: datetime


class Suggestions(BaseModel):
    items: list[SuggestionRead]


class ResponseUpsert(BaseModel):
    values: dict[str, dict[str, Any]] | None = None  # {question_name: {"value": ...}}
    status: ResponseStatus


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    user_id: UUID
    values: dict[str, Any] | None
    status: ResponseStatus
    inserted_at: datetime
    updated_at: datetime
