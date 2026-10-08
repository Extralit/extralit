from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_object_session
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from extralit_server.models.mixins import CRUDMixin, TimestampMixin


class DatabaseModel(DeclarativeBase, AsyncAttrs, CRUDMixin, TimestampMixin):
    __abstract__ = True

    # Required in order to access columns with server defaults or SQL expression defaults, subsequent to a flush, without
    # triggering an expired load
    # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    def is_relationship_loaded(self, relationship: str) -> bool:
        return relationship in self.__dict__

    @property
    def current_async_session(self) -> AsyncSession | None:
        return async_object_session(self)
