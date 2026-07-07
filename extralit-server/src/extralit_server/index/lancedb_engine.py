"""LanceDB-backed IndexEngine: one table per schema, BM25 full-text + scalar filtering.

Uses the async LanceDB API. The connection is opened lazily on first use so importing
the module (and constructing the engine) never touches the filesystem/URI.
"""

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import lancedb
import pyarrow as pa
from lancedb.index import FTS

from extralit_server.index.base import IndexEngine, IndexFilter, IndexSearchHit, IndexSearchResult
from extralit_server.index.mapping import SYSTEM_FIELDS, arrow_schema_for, arrow_type_for, table_name_for
from extralit_server.settings import settings

# Arrow type -> LanceDB SQL type name, for `add_columns` cast expressions during evolution.
# Must cover every Arrow type `mapping.arrow_type_for` can produce, or an evolved column
# would silently get a different type than the same column at create-table time
# (see tests/integration/index/test_lancedb_engine.py::test_sql_type_covers_every_mapped_arrow_type).
_SQL_TYPE_BY_ARROW = {
    pa.large_string(): "string",
    pa.int64(): "bigint",
    pa.int32(): "int",
    pa.float64(): "double",
    pa.float32(): "float",
    pa.bool_(): "boolean",
    pa.timestamp("ns"): "timestamp",
}


def _sql_type_for(dtype: str) -> str:
    return _SQL_TYPE_BY_ARROW.get(arrow_type_for(dtype), "string")


# Exact FTS totals are computed by materializing the match set; beyond this many matches
# the reported total saturates at the ceiling (extraction tables are far smaller today).
_FTS_TOTAL_CEILING = 10_000


def _validate_column(column: str, allowed: set[str]) -> None:
    """Reject column identifiers that are not in the known-safe set.

    This prevents SQL injection via crafted column names since Datafusion does not
    support parameterised identifiers — only values can be safely escaped.
    """
    if column not in allowed:
        raise ValueError(f"Unknown or disallowed filter column {column!r}. Allowed columns: {sorted(allowed)}")


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _where_clause(filters: list[IndexFilter] | None, allowed_columns: set[str] | None = None) -> str | None:
    if not filters:
        return None
    clauses = []
    for f in filters:
        if allowed_columns is not None:
            _validate_column(f.column, allowed_columns)
        if f.op == "eq":
            if f.value is None:
                clauses.append(f"{f.column} IS NULL")
            else:
                clauses.append(f"{f.column} = {_sql_literal(f.value)}")
        elif f.op == "ge":
            clauses.append(f"{f.column} >= {_sql_literal(f.value)}")
        elif f.op == "le":
            clauses.append(f"{f.column} <= {_sql_literal(f.value)}")
        elif f.op == "in":
            if isinstance(f.value, str) or not hasattr(f.value, "__iter__"):
                raise TypeError(f"IndexFilter op='in' requires a list/tuple of values, got {type(f.value).__name__!r}")
            values = ", ".join(_sql_literal(v) for v in f.value)
            clauses.append(f"{f.column} IN ({values})")
    return " AND ".join(clauses) if clauses else None


class LanceIndexEngine(IndexEngine):
    def __init__(self, uri: str) -> None:
        self._uri = uri
        self._db: Any = None

    @classmethod
    async def new_instance(cls) -> "LanceIndexEngine":
        return cls(uri=settings.lancedb_uri)

    async def _conn(self) -> Any:
        if self._db is None:
            self._db = await lancedb.connect_async(self._uri)
        return self._db

    async def close(self) -> None:
        # AsyncConnection has no explicit close in the current API; drop the reference.
        self._db = None

    async def _list_tables(self) -> list[str]:
        """Return all table names from the LanceDB connection, paginating to exhaustion."""
        db = await self._conn()
        names: list[str] = []
        page_token: str | None = None
        while True:
            kwargs = {"page_token": page_token} if page_token else {}
            response = await db.list_tables(**kwargs)
            names.extend(response.tables)
            page_token = response.page_token or None
            if not page_token:
                break
        return names

    async def table_names(self) -> list[str]:
        return await self._list_tables()

    async def ensure_table(self, schema_id: UUID, columns: list[dict[str, Any]]) -> None:
        name = table_name_for(schema_id)
        schema = arrow_schema_for(columns)
        if name not in await self._list_tables():
            db = await self._conn()
            table = await db.create_table(name, schema=schema)
            await table.create_index("text", config=FTS())
            return
        # Evolve: add any columns present in `columns` but missing from the live table.
        db = await self._conn()
        table = await db.open_table(name)
        existing = set((await table.schema()).names)
        to_add = {c["name"]: f"cast(NULL as {_sql_type_for(c['dtype'])})" for c in columns if c["name"] not in existing}
        if to_add:
            await table.add_columns(to_add)

    async def drop_table(self, schema_id: UUID) -> None:
        name = table_name_for(schema_id)
        if name in await self._list_tables():
            db = await self._conn()
            await db.drop_table(name)

    async def upsert(self, schema_id: UUID, rows: list[dict[str, Any]], columns: list[dict[str, Any]]) -> None:
        if not rows:
            return
        db = await self._conn()
        table = await db.open_table(table_name_for(schema_id))
        data = pa.Table.from_pylist(rows, schema=arrow_schema_for(columns))
        await table.merge_insert("record_id").when_matched_update_all().when_not_matched_insert_all().execute(data)
        await table.optimize()  # fold new rows into the FTS index

    async def delete(self, schema_id: UUID, record_ids: Iterable[UUID]) -> None:
        ids = [str(rid) for rid in record_ids]
        if not ids:
            return
        db = await self._conn()
        table = await db.open_table(table_name_for(schema_id))
        values = ", ".join(_sql_literal(i) for i in ids)
        await table.delete(f"record_id IN ({values})")

    async def search(
        self,
        schema_id: UUID,
        *,
        text: str | None = None,
        filters: list[IndexFilter] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> IndexSearchResult:
        db = await self._conn()
        name = table_name_for(schema_id)
        if name not in await self._list_tables():
            return IndexSearchResult(hits=[], total=0)
        table = await db.open_table(name)
        live_columns = set((await table.schema()).names)
        allowed_columns = live_columns | set(SYSTEM_FIELDS)
        clause = _where_clause(filters, allowed_columns)

        if text:
            # `count_rows` only evaluates scalar predicates — it cannot apply the FTS
            # match, so the total for a text query must come from the match set itself.
            # Materialize matches up to a ceiling and page in Python; beyond the ceiling
            # the total saturates at _FTS_TOTAL_CEILING (documented, bounded work).
            query = await table.search(text, query_type="fts")
            if clause:
                query = query.where(clause, prefilter=True)
            arrow = await query.limit(_FTS_TOTAL_CEILING).to_arrow()
            matches = arrow.to_pylist()
            hits = [
                IndexSearchHit(record_id=UUID(row["record_id"]), score=row.get("_score"))
                for row in matches[offset : offset + limit]
            ]
            return IndexSearchResult(hits=hits, total=len(matches))

        query = table.query()
        if clause:
            query = query.where(clause)
        arrow = await query.limit(offset + limit).to_arrow()
        rows = arrow.to_pylist()[offset:]
        hits = [IndexSearchHit(record_id=UUID(row["record_id"]), score=None) for row in rows]
        total = await table.count_rows(clause) if clause else await table.count_rows()
        return IndexSearchResult(hits=hits, total=total)
