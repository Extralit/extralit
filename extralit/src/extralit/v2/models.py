from typing import Optional

from pydantic import BaseModel

from extralit.v2._api._generated import (
    ProjectionCell,
    ProjectionRecord,
    ProjectionView,
    QuestionRead,
    RecordRead,
    ReferenceGroup,
    ReferenceView,
    ResponseRead,
    SchemaRead,
    SchemaVersionRead,
    SuggestionRead,
)

__all__ = [
    "ProjectionCell",
    "ProjectionRecord",
    "ProjectionView",
    "Question",
    "Record",
    "ReferenceGroup",
    "ReferenceView",
    "Response",
    "Schema",
    "SchemaVersion",
    "SearchPage",
    "Suggestion",
    "unwrap_response_values",
    "wrap_response_values",
]


class Schema(SchemaRead):
    pass


class SchemaVersion(SchemaVersionRead):
    def find_column(self, name: str) -> Optional[dict]:
        for column in self.columns_cache:
            if column.get("name") == name:
                return column
        return None


class Record(RecordRead):
    pass


class Question(QuestionRead):
    pass


class Suggestion(SuggestionRead):
    pass


def wrap_response_values(values: dict) -> dict:
    """Server stores response values double-wrapped: {question_name: {"value": ...}}."""
    return {name: {"value": value} for name, value in values.items()}


def unwrap_response_values(values: Optional[dict]) -> dict:
    return {name: cell.get("value") if isinstance(cell, dict) else cell for name, cell in (values or {}).items()}


class Response(ResponseRead):
    @property
    def unwrapped_values(self) -> dict:
        return unwrap_response_values(self.values)


class SearchPage(BaseModel):
    """One page of records. `total` is approximate: stale index ids are skipped and
    FTS saturates (~10k) — never present it as an exact count."""

    items: "list[Record]"
    total: int
