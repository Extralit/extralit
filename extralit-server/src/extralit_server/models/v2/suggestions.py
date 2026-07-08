from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import SuggestionType
from extralit_server.models.base import DatabaseModel

if TYPE_CHECKING:
    from extralit_server.models.v2.questions import V2Question
    from extralit_server.models.v2.records import V2Record

V2SuggestionTypeEnum = SAEnum(SuggestionType, name="v2_suggestion_type_enum")


class V2Suggestion(DatabaseModel):
    """LLM-pre-populated proposed value per (record, question) (spec §17). Superseded by a
    submitted response in the projection view, but retained as provenance."""

    __tablename__ = "v2_suggestions"

    record_id: Mapped[UUID] = mapped_column(ForeignKey("v2_records.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("v2_questions.id", ondelete="CASCADE"), index=True)
    value: Mapped[object] = mapped_column(JSON)
    score: Mapped[float | list[float] | None] = mapped_column(JSON, nullable=True)
    agent: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[SuggestionType | None] = mapped_column(V2SuggestionTypeEnum, nullable=True, index=True)

    record: Mapped["V2Record"] = relationship("V2Record")
    question: Mapped["V2Question"] = relationship("V2Question")

    __table_args__ = (UniqueConstraint("record_id", "question_id", name="v2_suggestion_record_id_question_id_uq"),)

    def __repr__(self) -> str:
        return f"V2Suggestion(id={self.id!s}, record_id={self.record_id!s}, question_id={self.question_id!s})"
