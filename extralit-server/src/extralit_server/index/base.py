"""v2 index engine interface — a small, v2-shaped abstraction over the physical index.

Deliberately NOT the v1 `search_engine.base.SearchEngine` ABC: that one is typed on v1
models (Dataset, MetadataProperty, Response) and stays untouched until Phase 6. This
engine speaks schema ids, column caches, and plain row dicts, so it never imports v1.
"""

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


@dataclasses.dataclass
class IndexFilter:
    """A single scalar filter clause against a schema column or system field."""

    column: str
    op: Literal["eq", "in", "ge", "le"]
    value: Any


class IndexSearchHit(BaseModel):
    record_id: UUID
    score: float | None = None


class IndexSearchResult(BaseModel):
    hits: list[IndexSearchHit]
    total: int = 0


class IndexEngine(ABC):
    """Physical index over derived record rows. Postgres remains the source of truth."""

    @classmethod
    @abstractmethod
    async def new_instance(cls) -> "IndexEngine": ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def ensure_table(self, schema_id: UUID, columns: list[dict[str, Any]]) -> None:
        """Create the schema's table if absent, else evolve it to the column superset."""

    @abstractmethod
    async def drop_table(self, schema_id: UUID) -> None: ...

    @abstractmethod
    async def upsert(
        self,
        schema_id: UUID,
        rows: list[dict[str, Any]],
        columns: list[dict[str, Any]],
        *,
        optimize: bool = True,
    ) -> None:
        """Merge rows into the table keyed on `record_id` (update-or-insert).

        Pass ``optimize=False`` when batching many upserts (e.g. during a rebuild) and
        call :meth:`optimize_table` once afterwards to fold all rows into the FTS index.
        """

    async def optimize_table(self, schema_id: UUID) -> None:
        """Compact and update the FTS index after a bulk rebuild.

        Default no-op — concrete engines override when the backend supports it.
        """

    @abstractmethod
    async def delete(self, schema_id: UUID, record_ids: Iterable[UUID]) -> None: ...

    @abstractmethod
    async def search(
        self,
        schema_id: UUID,
        *,
        text: str | None = None,
        filters: list[IndexFilter] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> IndexSearchResult: ...

    @abstractmethod
    async def table_names(self) -> list[str]: ...
