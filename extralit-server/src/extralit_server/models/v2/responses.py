from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import ResponseStatus
from extralit_server.models.base import DatabaseModel

if TYPE_CHECKING:
    from extralit_server.models.database import User
    from extralit_server.models.v2.records import V2Record

V2ResponseStatusEnum = SAEnum(ResponseStatus, name="v2_response_status_enum")


class V2Response(DatabaseModel):
    """Human review per (record, user); `values` keyed by question name -> {value} (spec §17.3).
    Multiple users per record = the overlap axis Phase 5 distribution counts."""

    __tablename__ = "v2_responses"

    record_id: Mapped[UUID] = mapped_column(ForeignKey("v2_records.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    values: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSON), nullable=True)
    status: Mapped[ResponseStatus] = mapped_column(V2ResponseStatusEnum, default=ResponseStatus.submitted, index=True)

    record: Mapped["V2Record"] = relationship("V2Record")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (UniqueConstraint("record_id", "user_id", name="v2_response_record_id_user_id_uq"),)

    @property
    def is_submitted(self) -> bool:
        return self.status == ResponseStatus.submitted

    def __repr__(self) -> str:
        return f"V2Response(id={self.id!s}, record_id={self.record_id!s}, user_id={self.user_id!s}, status={self.status!r})"
