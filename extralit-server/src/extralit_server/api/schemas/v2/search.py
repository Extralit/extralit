from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from extralit_server.api.schemas.v2.records import LIST_RECORDS_LIMIT_DEFAULT, LIST_RECORDS_LIMIT_LE


class RecordFilter(BaseModel):
    column: str
    op: Literal["eq", "in", "ge", "le"]
    value: Any

    @model_validator(mode="after")
    def _validate_in_value(self) -> "RecordFilter":
        if self.op == "in" and (isinstance(self.value, (str, bytes)) or not hasattr(self.value, "__iter__")):
            raise ValueError(
                f"Filter op='in' requires a list of values, got {type(self.value).__name__!r}."
                ' Pass a JSON array, e.g. {"op": "in", "value": [1, 2, 3]}.'
            )
        return self


class RecordSearchQuery(BaseModel):
    text: str | None = None
    filters: list[RecordFilter] = Field(default_factory=list)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=LIST_RECORDS_LIMIT_DEFAULT, ge=1, le=LIST_RECORDS_LIMIT_LE)
