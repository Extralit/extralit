"""Hybrid search over chunk datasets: DuckDB `lance` BM25 and vector legs fused by SQL RRF."""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Optional
from uuid import UUID

import duckdb
from anyio import to_thread
from pydantic_ai import Embedder

from extralit_server.contexts.retrieval.settings import RetrievalSettings
from extralit_server.contexts.retrieval.store import ChunkStore

_LOGGER = logging.getLogger("extralit_server.contexts.retrieval.search")

TYPES = ("text", "table", "figure")
FILTER_COLUMNS = frozenset({"document_id", "reference", "type", "page_start", "page_end"})
PAYLOAD = (
    "chunk_id",
    "document_id",
    "reference",
    "ordinal",
    "type",
    "text",
    "headings",
    "item_refs",
    "page_start",
    "page_end",
)


@dataclass
class SearchFilters:
    document_ids: Sequence[UUID | str] = field(default_factory=list)
    references: Sequence[str] = field(default_factory=list)
    pages: Sequence[int] = field(default_factory=list)
    types: Sequence[str] = field(default_factory=list)


@dataclass
class ChunkHit:
    chunk_id: str
    document_id: str
    reference: Optional[str]
    ordinal: int
    type: str
    text: str
    headings: list[str]
    item_refs: list[str]
    page_start: Optional[int]
    page_end: Optional[int]
    bm25: Optional[float]
    vector: Optional[float]  # distance, lower is closer
    rrf: float


def _column(name: str) -> str:
    if name not in FILTER_COLUMNS:
        raise ValueError(f"Column {name!r} is not filterable")
    return name


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _in(column: str, values: Sequence[Any]) -> str:
    return f"{_column(column)} IN ({', '.join(str(v) if isinstance(v, int) else _literal(str(v)) for v in values)})"


def build_filter(filters: Optional[SearchFilters]) -> Optional[str]:
    """Lance SQL filter from allow-listed columns and quoted literals; None when unfiltered."""
    if filters is None:
        return None
    clauses = []
    if filters.document_ids:
        clauses.append(_in("document_id", [str(UUID(str(d))) for d in filters.document_ids]))
    if filters.references:
        clauses.append(_in("reference", [str(r) for r in filters.references]))
    if filters.types:
        unknown = set(filters.types) - set(TYPES)
        if unknown:
            raise ValueError(f"Unknown chunk types: {sorted(unknown)}")
        clauses.append(_in("type", list(filters.types)))
    if filters.pages:
        spans = [f"({_column('page_start')} <= {int(p)} AND {_column('page_end')} >= {int(p)})" for p in filters.pages]
        clauses.append(f"({' OR '.join(spans)})")
    return " AND ".join(clauses) or None


def fuse_sql(fts: str, vector: Optional[str], rrf_k: int, limit: int) -> str:
    """RRF over ranked legs. `fts` yields PAYLOAD + `bm25`; `vector` yields PAYLOAD + `distance`."""
    columns = ", ".join(PAYLOAD)
    if vector is None:
        vector = "SELECT " + ", ".join(f"NULL AS {c}" for c in PAYLOAD) + ", NULL::DOUBLE AS distance WHERE false"
    merged = ", ".join(f"coalesce(f.{c}, v.{c}) AS {c}" for c in PAYLOAD if c != "chunk_id")
    return f"""
WITH f AS (
    SELECT {columns}, bm25, row_number() OVER (ORDER BY bm25 DESC, chunk_id) AS rank FROM ({fts})
), v AS (
    SELECT {columns}, distance, row_number() OVER (ORDER BY distance ASC, chunk_id) AS rank FROM ({vector})
)
SELECT coalesce(f.chunk_id, v.chunk_id) AS chunk_id, {merged}, f.bm25, v.distance,
    coalesce(1.0 / ({int(rrf_k)} + f.rank), 0) + coalesce(1.0 / ({int(rrf_k)} + v.rank), 0) AS rrf
FROM f FULL OUTER JOIN v ON f.chunk_id = v.chunk_id
ORDER BY rrf DESC, chunk_id
LIMIT {int(limit)}
"""


_CONNECTION_LOCK = threading.Lock()
_CONNECTION: Optional[duckdb.DuckDBPyConnection] = None
_ATTACHED: dict[str, str] = {}


def _connection() -> duckdb.DuckDBPyConnection:
    """Process-wide connection, because loading the extension costs ~300 ms. Caller holds `_CONNECTION_LOCK`."""
    global _CONNECTION
    if _CONNECTION is None:
        connection = duckdb.connect()
        # By path: `LOAD lance` only searches ~/.duckdb/extensions, which the wheel never populates.
        path = files("duckdb_extension_lance") / "extensions" / f"v{duckdb.__version__}" / "lance.duckdb_extension"
        connection.execute(f"LOAD {_literal(str(path))}")
        _CONNECTION = connection
    return _CONNECTION


def _vector_literal(vector: Sequence[float]) -> str:
    return f"[{', '.join(repr(float(x)) for x in vector)}]::FLOAT[{len(vector)}]"


def _attach(connection: duckdb.DuckDBPyConnection, store: ChunkStore) -> str:
    """Attach the store's root once per process; an attached root keeps following new dataset versions."""
    root, options = store.layout.root_uri, store.layout.storage_options
    if root not in _ATTACHED:
        alias = f"ns{len(_ATTACHED)}"
        if root.startswith("s3://") and options:
            pairs = ", ".join(f"{_literal(k)}: {_literal(str(v))}" for k, v in options.items())
            connection.execute(
                f"CREATE OR REPLACE SECRET lance_{alias} "
                f"(TYPE LANCE, SCOPE {_literal(root)}, STORAGE_OPTIONS MAP {{{pairs}}})"
            )
        connection.execute(f"ATTACH {_literal(root)} AS {alias} (TYPE LANCE, READ_ONLY false)")
        _ATTACHED[root] = alias
    return f"{_ATTACHED[root]}.main.chunks"


def _legs(
    tables: list[tuple[str, Optional[str]]],
    query: str,
    vector: Optional[Sequence[float]],
    filter_: Optional[str],
    k: int,
) -> tuple[str, list[Any], Optional[str], list[Any]]:
    """FTS and vector leg SQL (with their parameters) unioned over the stores' tables."""
    payload = ", ".join(PAYLOAD)
    fts, fts_params, vec, vec_params = [], [], [], []
    for table, column in tables:
        # An always-true prefilter still costs ~40% of the FTS leg, so it is only passed when there is one.
        prefilter = ", filter := ?, prefilter := true" if filter_ else ""
        fts.append(f"SELECT {payload}, _score AS bm25 FROM lance_fts({_literal(table)}, 'text', ?, k={k}{prefilter})")
        fts_params += [query, filter_] if filter_ else [query]
        if column is not None and vector is not None:
            vec_filter = f"{column} IS NOT NULL" + (f" AND ({filter_})" if filter_ else "")
            vec.append(
                f"SELECT {payload}, _distance AS distance FROM lance_vector_search({_literal(table)}, "
                f"{_literal(column)}, {_vector_literal(vector)}, k={k}, filter := ?, prefilter := true)"
            )
            vec_params += [vec_filter]
    return " UNION ALL ".join(fts), fts_params, (" UNION ALL ".join(vec) or None), vec_params


def _run(
    stores: Sequence[ChunkStore],
    query: str,
    vector: Optional[Sequence[float]],
    model: str,
    filter_: Optional[str],
    limit: int,
    settings: RetrievalSettings,
) -> list[ChunkHit]:
    tables = []
    with _CONNECTION_LOCK:
        connection = _connection()
        for store in stores:
            if store.open() is None:
                continue
            column = store.vector_columns().get(model) if model else None
            tables.append((_attach(connection, store), column))
        cursor = connection.cursor()
    if not tables:
        return []
    try:
        fts, fts_params, vec, vec_params = _legs(tables, query, vector, filter_, max(settings.candidate_k, limit))
        sql = fuse_sql(fts, vec, settings.rrf_k, limit)
        rows = cursor.execute(sql, fts_params + vec_params).fetchall()
    finally:
        cursor.close()
    return [ChunkHit(*row[: len(PAYLOAD)], bm25=row[-3], vector=row[-2], rrf=row[-1]) for row in rows]


async def embed_query(
    stores: Sequence[ChunkStore], query: str, embedder: Optional[Embedder], settings: RetrievalSettings
) -> Optional[list[float]]:
    """The query vector, or None without an embedder or when no store has a column for the model."""
    model = settings.embedding_model
    if embedder is None or not model:
        return None
    if not await to_thread.run_sync(lambda: any(model in store.vector_columns() for store in stores)):
        return None
    result = await embedder.embed_query(query)
    return [float(x) for x in result.embeddings[0]]


async def hybrid_search(
    stores: Sequence[ChunkStore],
    query: str,
    *,
    embedder: Optional[Embedder] = None,
    vector: Optional[Sequence[float]] = None,
    filters: Optional[SearchFilters] = None,
    limit: int = 10,
    settings: Optional[RetrievalSettings] = None,
) -> list[ChunkHit]:
    """BM25 + vector hits fused by RRF; filters run inside both legs, before top-k.

    Pass `vector` from `embed_query` to search repeatedly on one embedding; otherwise `embedder` computes it.
    """
    settings = settings or RetrievalSettings()
    if vector is None:
        vector = await embed_query(stores, query, embedder, settings)
    return await to_thread.run_sync(
        _run, stores, query, vector, settings.embedding_model, build_filter(filters), limit, settings
    )
