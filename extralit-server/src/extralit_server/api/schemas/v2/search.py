from typing import Any, Literal

from pydantic import BaseModel, Field

from extralit_server.api.schemas.v2.records import LIST_RECORDS_LIMIT_DEFAULT, LIST_RECORDS_LIMIT_LE


class RecordFilter(BaseModel):
    column: str
    op: Literal["eq", "in", "ge", "le"]
    value: Any


class RecordSearchQuery(BaseModel):
    text: str | None = None
    filters: list[RecordFilter] = Field(default_factory=list)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=LIST_RECORDS_LIMIT_DEFAULT, ge=1, le=LIST_RECORDS_LIMIT_LE)
