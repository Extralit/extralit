# v2 LanceDB Index Engine Implementation Plan (Phase 3 of 6)

> **Historical note (2026-07-26):** The `/api/v2` parallel tree described in this document was folded back into `/api/v1`. See `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`. This document is kept as a historical record; its API paths, models, and file references may no longer exist.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a LanceDB-backed index engine that derives one Lance table per v2 schema from Postgres, exposing full-text (BM25) + scalar-filter search over records via `POST /api/v2/schemas/{id}/records:search`, kept in sync best-effort on write and rebuildable from Postgres.

**Architecture:** Postgres stays the source of truth; the Lance table is a derived, rebuildable index. Sync **mirrors v1's proven shape** — create/evolve the index when a schema version is published, `upsert` records inline after the Postgres commit, `delete` on record delete, and a reindex CLI as the recovery path — but through a **new v2-shaped `IndexEngine`** taking `Schema`/`V2Record` (not the v1 `SearchEngine` ABC, which is typed on v1 models and stays untouched until Phase 6). Failure semantics differ from v1 deliberately: a failed sync **logs a warning and never fails the API request** (spec §15). Search consults Lance only for matching/ranking (record ids + scores); response payloads are **hydrated from Postgres** so results always reflect the source of truth even when the index is stale.

**Tech Stack:** Python 3.10+, `lancedb` (async API: `connect_async`, `merge_insert`, `create_index(FTS)`, `add_columns`, `optimize`), PyArrow (bundled with pandas 3.0), FastAPI, SQLAlchemy async, Typer (CLI), async pytest + factory-boy.

## Global Constraints

- Python floor **3.10** (`extralit-server/pyproject.toml` `requires-python = ">=3.10"`). No 3.11+-only syntax.
- Package management is **uv only**: `uv add lancedb`, `uv run pytest`, `uv run ruff check`. Never edit `pyproject.toml` deps by hand; never call pip/poetry.
- Settings use the `EXTRALIT_` env prefix (`settings.py` `Config.env_prefix = "EXTRALIT_"`), so the new URI setting is `EXTRALIT_LANCEDB_URI`.
- **ES coexistence — additive only.** Do **not** touch, import, or delete `search_engine/` (v1 lives on it until Phase 6). This phase adds a parallel `index/` package.
- **Best-effort sync, never fatal.** Any exception from the index engine during a sync hook is caught, logged at WARNING with schema + record ids, and swallowed — the API request still succeeds. Only the explicit `:rebuild-index` endpoint and the reindex CLI surface index errors.
- **Postgres is authoritative; Lance is rebuildable.** Search returns ids/scores from Lance; payloads are always fetched from Postgres. Never serialize a response body from Lance rows.
- Lance table name per schema: `schema_{schema_id.hex}` (a valid identifier; UUIDs contain `-` which is unsafe in some Lance backends).
- Vector/embedding work is **out of scope** (spec §15 defers it to a PDF-chunk-retrieval session). No vector column, no `similarity_search`, no litellm calls in this phase.
- ORM class for records is `V2Record` (imported from `extralit_server.models.v2`); status enum is `V2RecordStatus`.
- Existing test seam: `extralit_server.contexts.v2.records._fetch_body_json` is monkeypatched in record tests to avoid S3. Follow the same AsyncMock pattern where a body/columns fetch is needed.

---

## File Structure

**New package `index/`** (engine + Lance mechanics + pure mapping; no v1 imports):
- `src/extralit_server/index/__init__.py` — `get_index_engine()` DI provider (async generator, mirrors `get_search_engine`).
- `src/extralit_server/index/base.py` — `IndexEngine` ABC + `IndexSearchHit`/`IndexSearchResult` + filter dataclasses (v2-shaped).
- `src/extralit_server/index/mapping.py` — **pure** helpers: pandera-dtype→Arrow, `arrow_schema_for`, `table_name_for`, `concat_text`, `record_to_row`, `union_columns`.
- `src/extralit_server/index/lancedb_engine.py` — `LanceIndexEngine(IndexEngine)` against a `lancedb.connect_async(uri)` connection.

**New sync orchestration** (glue between contexts and the engine; owns best-effort semantics):
- `src/extralit_server/contexts/v2/index_sync.py` — `sync_schema_table`, `sync_upserted_records`, `sync_deleted_records`, `rebuild_schema_index`.

**New search request/response schemas:**
- `src/extralit_server/api/schemas/v2/search.py` — `RecordFilter`, `RecordSearchQuery`.

**New CLI** (v2 twin of `cli/search_engine/reindex.py`):
- `src/extralit_server/cli/index/__init__.py` — Typer app.
- `src/extralit_server/cli/index/__main__.py` — command wiring.
- `src/extralit_server/cli/index/reindex.py` — `Reindexer` batched rebuild.

**Modified:**
- `src/extralit_server/settings.py` — add `lancedb_uri` + default validator.
- `src/extralit_server/api/v2/schemas.py` — publish handler calls `sync_schema_table` (best-effort).
- `src/extralit_server/api/v2/records.py` — bulk-upsert + delete handlers call sync; add `:search` and `:rebuild-index` endpoints.
- `src/extralit_server/cli/__init__.py` — register the `index` Typer app.

**Tests:**
- `tests/unit/index/test_mapping.py` — pure mapping helpers (no services).
- `tests/integration/index/test_lancedb_engine.py` — engine against a tmp-dir Lance uri.
- `tests/integration/contexts/v2/test_index_sync.py` — orchestration + failure-swallow.
- `tests/integration/api/v2/test_records_search.py` — `:search`, `:rebuild-index`, sync-on-write.
- `tests/unit/index/test_settings_lancedb_uri.py` — URI default.

---

## Task 1: LanceDB dependency + `lancedb_uri` setting

**Files:**
- Modify: `extralit-server/pyproject.toml` (via `uv add`)
- Modify: `extralit-server/src/extralit_server/settings.py`
- Test: `extralit-server/tests/unit/index/test_settings_lancedb_uri.py`

**Interfaces:**
- Produces: `settings.lancedb_uri: str` — always a concrete path/URI (never None after validation); defaults to `{home_path}/lance`.

- [ ] **Step 1: Add the dependency**

Run: `cd extralit-server && uv add lancedb`
Expected: `pyproject.toml` gains `lancedb` under `[project].dependencies`; `uv.lock` updates; exit 0.

- [ ] **Step 2: Write the failing test**

Create `extralit-server/tests/unit/index/__init__.py` (empty file), then create `extralit-server/tests/unit/index/test_settings_lancedb_uri.py`:

```python
import os
from pathlib import Path

from extralit_server.settings import Settings


def test_lancedb_uri_defaults_under_home_path():
    s = Settings(home_path="/tmp/extralit-home", lancedb_uri=None)
    assert s.lancedb_uri == os.path.join("/tmp/extralit-home", "lance")


def test_lancedb_uri_explicit_value_is_respected():
    s = Settings(home_path="/tmp/extralit-home", lancedb_uri="s3://bucket/lance")
    assert s.lancedb_uri == "s3://bucket/lance"


def test_lancedb_uri_reads_env_prefix(monkeypatch):
    monkeypatch.setenv("EXTRALIT_LANCEDB_URI", "/data/custom-lance")
    s = Settings(home_path="/tmp/extralit-home")
    assert s.lancedb_uri == "/data/custom-lance"
    assert Path("/data/custom-lance").name == "custom-lance"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/unit/index/test_settings_lancedb_uri.py -v`
Expected: FAIL — `Settings` has no field `lancedb_uri` (pydantic ignores/rejects it or attribute missing).

- [ ] **Step 3: Add the setting**

In `settings.py`, add the field near the `s3_*` fields (after `s3_region`):

```python
    lancedb_uri: str | None = Field(
        default=None,
        validate_default=True,
        description="URI for the LanceDB index store (v2). Defaults to `{home_path}/lance`. "
        "A local path works on the compose named volume and HF-Spaces persistent storage; "
        "an s3:// URI is accepted by lancedb.connect but unsupported/unvalidated for now.",
    )
```

Then add a validator (place it alongside the existing `home_path`/`base_url` validators, after the `home_path` validator so `home_path` is already resolved in `info.data`):

```python
    @field_validator("lancedb_uri", mode="before")
    @classmethod
    def set_lancedb_uri_default(cls, lancedb_uri: str | None, info: ValidationInfo) -> str:
        if lancedb_uri:
            return lancedb_uri
        home_path = info.data.get("home_path") or os.path.join(Path.home(), ".extralit")
        return os.path.join(home_path, "lance")
```

(`os`, `Path`, `field_validator`, `ValidationInfo` are already imported in `settings.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/unit/index/test_settings_lancedb_uri.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/pyproject.toml extralit-server/uv.lock extralit-server/src/extralit_server/settings.py extralit-server/tests/unit/index/
git commit -m "feat(v2): add lancedb dependency and EXTRALIT_LANCEDB_URI setting"
```

---

## Task 2: Pure mapping helpers (`index/mapping.py`)

**Files:**
- Create: `extralit-server/src/extralit_server/index/__init__.py` (empty for now; filled in Task 5)
- Create: `extralit-server/src/extralit_server/index/mapping.py`
- Test: `extralit-server/tests/unit/index/test_mapping.py`

**Interfaces:**
- Consumes: `columns_cache: list[dict]` entries shaped `{"name", "dtype", "nullable", "review"}` (from `SchemaVersion.columns_cache`, derived by `derive_columns_cache`). Observed pandera 0.32 / pandas 3.0 dtype strings: `"string[pyarrow]"`, `"int64"`, `"float64"`, `"bool"`, `"datetime64[ns]"`.
- Produces:
  - `SYSTEM_FIELDS: list[str]` = `["record_id", "reference", "schema_version_id", "status", "external_id", "text"]`
  - `table_name_for(schema_id: UUID) -> str`
  - `union_columns(caches: list[list[dict]]) -> list[dict]` — deduped union of column entries across versions, first occurrence wins, stable order.
  - `arrow_schema_for(columns: list[dict]) -> pa.Schema`
  - `arrow_type_for(dtype: str) -> pa.DataType`
  - `concat_text(fields: dict, columns: list[dict]) -> str`
  - `record_to_row(record, columns: list[dict]) -> dict` — accepts anything with `.id`, `.reference`, `.schema_version_id`, `.status`, `.external_id`, `.fields`; returns a dict with every key in `arrow_schema_for(columns)`, missing cells as `None`.

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/unit/index/test_mapping.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pyarrow as pa

from extralit_server.enums import V2RecordStatus
from extralit_server.index import mapping


COLUMNS = [
    {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
    {"name": "year", "dtype": "int64", "nullable": True, "review": None},
    {"name": "score", "dtype": "float64", "nullable": True, "review": None},
]


def test_table_name_is_hex_prefixed():
    sid = uuid4()
    assert mapping.table_name_for(sid) == f"schema_{sid.hex}"


def test_arrow_type_mapping_covers_pandera_dtypes():
    assert mapping.arrow_type_for("string[pyarrow]") == pa.large_string()
    assert mapping.arrow_type_for("int64") == pa.int64()
    assert mapping.arrow_type_for("float64") == pa.float64()
    assert mapping.arrow_type_for("bool") == pa.bool_()
    assert pa.types.is_timestamp(mapping.arrow_type_for("datetime64[ns]"))


def test_arrow_type_unknown_dtype_falls_back_to_string():
    assert mapping.arrow_type_for("category") == pa.large_string()


def test_arrow_schema_has_system_fields_and_typed_columns():
    schema = mapping.arrow_schema_for(COLUMNS)
    names = schema.names
    for sys_field in mapping.SYSTEM_FIELDS:
        assert sys_field in names
    assert schema.field("year").type == pa.int64()
    assert schema.field("text").type == pa.large_string()


def test_union_columns_dedupes_by_name_first_wins():
    v1 = [{"name": "a", "dtype": "int64", "nullable": True, "review": None}]
    v2 = [
        {"name": "a", "dtype": "int64", "nullable": True, "review": None},
        {"name": "b", "dtype": "string[pyarrow]", "nullable": True, "review": None},
    ]
    union = mapping.union_columns([v1, v2])
    assert [c["name"] for c in union] == ["a", "b"]


def test_concat_text_joins_string_columns_only():
    fields = {"title": "Deep Learning", "year": 2016, "score": 9.1}
    text = mapping.concat_text(fields, COLUMNS)
    assert "title: Deep Learning" in text
    assert "year" not in text  # non-string dtype excluded


def test_record_to_row_fills_missing_cells_with_none():
    rec = SimpleNamespace(
        id=uuid4(),
        reference="pmid:1",
        schema_version_id=uuid4(),
        status=V2RecordStatus.pending,
        external_id="x-1",
        fields={"title": "Deep Learning"},  # `year`/`score` absent
    )
    row = mapping.record_to_row(rec, COLUMNS)
    assert row["record_id"] == str(rec.id)
    assert row["schema_version_id"] == str(rec.schema_version_id)
    assert row["status"] == V2RecordStatus.pending.value
    assert row["title"] == "Deep Learning"
    assert row["year"] is None
    assert row["score"] is None
    assert row["text"] == "title: Deep Learning"
    # every arrow-schema field is present as a key
    assert set(row) == set(mapping.arrow_schema_for(COLUMNS).names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/unit/index/test_mapping.py -v`
Expected: FAIL — `extralit_server.index.mapping` does not exist (ModuleNotFoundError).

- [ ] **Step 3: Write the implementation**

Create `extralit-server/src/extralit_server/index/__init__.py` as an empty file (the DI provider is added in Task 5 — keep it empty so importing `extralit_server.index.mapping` does not pull in `lancedb` yet):

```python
```

Create `extralit-server/src/extralit_server/index/mapping.py`:

```python
"""Pure, I/O-free helpers mapping v2 schema columns and records to a Lance row layout.

No LanceDB, DB, or object-store access — given a `columns_cache` (from
`SchemaVersion.columns_cache`) and a record, build the Arrow schema and row dicts the
index engine writes. The Lance table for a schema is the union (superset) of columns
across its versions plus system/identity columns and a derived `text` column that
carries the BM25 full-text index.
"""

from typing import Any
from uuid import UUID

import pyarrow as pa

# Identity/system columns present in every schema's Lance table, independent of the
# user-defined columns. `text` is the concatenated string-cell blob the FTS index covers.
SYSTEM_FIELDS = ["record_id", "reference", "schema_version_id", "status", "external_id", "text"]

# Observed pandera 0.32 / pandas 3.0 `str(column.dtype)` values -> Arrow types.
# large_string is used for text so the FTS index has no 2GiB offset ceiling.
_ARROW_BY_DTYPE = {
    "string[pyarrow]": pa.large_string(),
    "string": pa.large_string(),
    "object": pa.large_string(),
    "int64": pa.int64(),
    "int32": pa.int32(),
    "float64": pa.float64(),
    "float32": pa.float32(),
    "bool": pa.bool_(),
    "boolean": pa.bool_(),
    "datetime64[ns]": pa.timestamp("ns"),
}

# Column dtypes we treat as full-text material for the `text` blob.
_STRING_DTYPES = {"string[pyarrow]", "string", "object"}


def table_name_for(schema_id: UUID) -> str:
    """Lance table name for a schema. UUID hex (no dashes) is a safe identifier."""
    return f"schema_{schema_id.hex}"


def arrow_type_for(dtype: str) -> pa.DataType:
    """Map a pandera/pandas dtype string to an Arrow type; unknown -> large_string."""
    return _ARROW_BY_DTYPE.get(dtype, pa.large_string())


def union_columns(caches: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Union column entries across versions, first occurrence wins, order preserved."""
    seen: dict[str, dict[str, Any]] = {}
    for cache in caches:
        for column in cache or []:
            name = column["name"]
            if name not in seen:
                seen[name] = column
    return list(seen.values())


def arrow_schema_for(columns: list[dict[str, Any]]) -> pa.Schema:
    """Build the full Arrow schema: system fields + one typed field per schema column.

    All fields are nullable in Lance regardless of the Pandera `nullable` flag —
    Postgres enforces validation; the index must hold superset rows where older-version
    records legitimately lack newer columns.
    """
    fields = [
        pa.field("record_id", pa.large_string()),
        pa.field("reference", pa.large_string()),
        pa.field("schema_version_id", pa.large_string()),
        pa.field("status", pa.large_string()),
        pa.field("external_id", pa.large_string()),
    ]
    for column in columns:
        fields.append(pa.field(column["name"], arrow_type_for(column["dtype"])))
    fields.append(pa.field("text", pa.large_string()))
    return pa.schema(fields)


def concat_text(fields: dict[str, Any], columns: list[dict[str, Any]]) -> str:
    """Concatenate string-typed cells into a `col: value` blob for the FTS index."""
    lines = []
    for column in columns:
        if column["dtype"] not in _STRING_DTYPES:
            continue
        value = fields.get(column["name"])
        if value is None:
            continue
        lines.append(f"{column['name']}: {value}")
    return "\n".join(lines)


def record_to_row(record: Any, columns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a Lance row dict for a record against the table's column superset.

    Every field in `arrow_schema_for(columns)` is present as a key; schema columns the
    record does not carry are filled with None (older-version rows in an evolved table).
    Permissive extra fields in `record.fields` that are not schema columns are ignored.
    UUID/enum system values are stringified to match the Arrow schema.
    """
    fields = record.fields or {}
    row: dict[str, Any] = {
        "record_id": str(record.id),
        "reference": record.reference,
        "schema_version_id": str(record.schema_version_id),
        "status": record.status.value if hasattr(record.status, "value") else str(record.status),
        "external_id": record.external_id,
    }
    for column in columns:
        row[column["name"]] = fields.get(column["name"])
    row["text"] = concat_text(fields, columns)
    return row
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/unit/index/test_mapping.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/index/__init__.py extralit-server/src/extralit_server/index/mapping.py extralit-server/tests/unit/index/test_mapping.py
git commit -m "feat(v2): pure Arrow/Lance mapping helpers for schema columns and records"
```

---

## Task 3: `IndexEngine` ABC + result/filter models (`index/base.py`)

**Files:**
- Create: `extralit-server/src/extralit_server/index/base.py`
- Test: `extralit-server/tests/unit/index/test_base.py`

**Interfaces:**
- Produces:
  - `IndexFilter` dataclass: `column: str`, `op: Literal["eq", "in", "ge", "le"]`, `value: Any`.
  - `IndexSearchHit(BaseModel)`: `record_id: UUID`, `score: float | None`.
  - `IndexSearchResult(BaseModel)`: `hits: list[IndexSearchHit]`, `total: int`.
  - `IndexEngine(ABC)` with abstract async methods: `new_instance() -> IndexEngine` (classmethod), `close()`, `ensure_table(schema_id, columns)`, `drop_table(schema_id)`, `upsert(schema_id, rows, columns)`, `delete(schema_id, record_ids)`, `search(schema_id, *, text, filters, offset, limit) -> IndexSearchResult`, `table_names() -> list[str]`.

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/unit/index/test_base.py`:

```python
import inspect
from uuid import uuid4

from extralit_server.index.base import IndexEngine, IndexFilter, IndexSearchHit, IndexSearchResult


def test_index_engine_is_abstract():
    import pytest

    with pytest.raises(TypeError):
        IndexEngine()  # abstract methods unimplemented


def test_required_async_methods_present():
    for name in ("close", "ensure_table", "drop_table", "upsert", "delete", "search", "table_names"):
        method = getattr(IndexEngine, name)
        assert inspect.iscoroutinefunction(method), f"{name} must be async"


def test_result_models_roundtrip():
    hit = IndexSearchHit(record_id=uuid4(), score=1.5)
    result = IndexSearchResult(hits=[hit], total=1)
    assert result.total == 1
    assert result.hits[0].score == 1.5


def test_index_filter_shape():
    f = IndexFilter(column="year", op="ge", value=2000)
    assert (f.column, f.op, f.value) == ("year", "ge", 2000)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/unit/index/test_base.py -v`
Expected: FAIL — `extralit_server.index.base` does not exist.

- [ ] **Step 3: Write the implementation**

Create `extralit-server/src/extralit_server/index/base.py`:

```python
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
    async def new_instance(cls) -> "IndexEngine":
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    @abstractmethod
    async def ensure_table(self, schema_id: UUID, columns: list[dict[str, Any]]) -> None:
        """Create the schema's table if absent, else evolve it to the column superset."""

    @abstractmethod
    async def drop_table(self, schema_id: UUID) -> None:
        ...

    @abstractmethod
    async def upsert(self, schema_id: UUID, rows: list[dict[str, Any]], columns: list[dict[str, Any]]) -> None:
        """Merge rows into the table keyed on `record_id` (update-or-insert)."""

    @abstractmethod
    async def delete(self, schema_id: UUID, record_ids: Iterable[UUID]) -> None:
        ...

    @abstractmethod
    async def search(
        self,
        schema_id: UUID,
        *,
        text: str | None = None,
        filters: list[IndexFilter] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> IndexSearchResult:
        ...

    @abstractmethod
    async def table_names(self) -> list[str]:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/unit/index/test_base.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/index/base.py extralit-server/tests/unit/index/test_base.py
git commit -m "feat(v2): v2-shaped IndexEngine ABC and search result/filter models"
```

---

## Task 4: `LanceIndexEngine` implementation (`index/lancedb_engine.py`)

**Files:**
- Create: `extralit-server/src/extralit_server/index/lancedb_engine.py`
- Test: `extralit-server/tests/integration/index/__init__.py` (empty), `extralit-server/tests/integration/index/test_lancedb_engine.py`

**Interfaces:**
- Consumes: `IndexEngine`, `IndexFilter`, `IndexSearchHit`, `IndexSearchResult` (Task 3); `mapping.table_name_for`, `mapping.arrow_schema_for` (Task 2); `settings.lancedb_uri` (Task 1).
- Produces: `LanceIndexEngine(IndexEngine)` with `__init__(self, uri: str)` and `classmethod new_instance()` reading `settings.lancedb_uri`. Runs entirely on a local tmp-dir uri in tests (no external service).

**Notes for the implementer (verified against LanceDB async docs):**
- Connect: `db = await lancedb.connect_async(uri)`.
- Create empty table: `await db.create_table(name, schema=arrow_schema)`. Open: `await db.open_table(name)`. Existence: `name in await db.table_names()`.
- Evolve: `await table.add_columns({col: f"cast(NULL as {sql_type})"})` for each missing column (SQL-expression form; the column is added nullable).
- Upsert: `await table.merge_insert("record_id").when_matched_update_all().when_not_matched_insert_all().execute(pa_table)`.
- FTS index: `await table.create_index("text", config=FTS())` (import `from lancedb.index import FTS`). Call `await table.optimize()` after writes so new rows fold into the index.
- Delete: `await table.delete(sql_predicate)`.
- Count: `await table.count_rows(filter)` (filter is a SQL string or None).
- Search with text: `q = (await table.search(text, query_type="fts")).where(clause, prefilter=True)`; without text: `q = table.query().where(clause)`. Materialize: `await q.limit(offset + limit).to_arrow()`, then slice `[offset:]` in Python. FTS relevance is the `_score` column; a plain scan has no score (None).

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/integration/index/__init__.py` (empty), then `extralit-server/tests/integration/index/test_lancedb_engine.py`:

```python
from uuid import uuid4

import pytest

from extralit_server.index.base import IndexFilter
from extralit_server.index.lancedb_engine import LanceIndexEngine
from extralit_server.index.mapping import record_to_row

pytestmark = pytest.mark.asyncio

COLUMNS = [
    {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
    {"name": "year", "dtype": "int64", "nullable": True, "review": None},
]


class _Rec:
    def __init__(self, title, year, reference="pmid:1", external_id=None):
        from extralit_server.enums import V2RecordStatus

        self.id = uuid4()
        self.reference = reference
        self.schema_version_id = uuid4()
        self.status = V2RecordStatus.pending
        self.external_id = external_id
        self.fields = {"title": title, "year": year}


@pytest.fixture
async def engine(tmp_path):
    eng = LanceIndexEngine(uri=str(tmp_path / "lance"))
    yield eng
    await eng.close()


async def test_ensure_upsert_and_fts_search(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("Deep Learning Foundations", 2016), _Rec("Shallow Ponds", 1999)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    result = await engine.search(sid, text="Deep Learning", offset=0, limit=10)
    assert result.total >= 1
    assert recs[0].id in [h.record_id for h in result.hits]


async def test_scalar_filter_without_text(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("A", 2016), _Rec("B", 1999)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    result = await engine.search(sid, filters=[IndexFilter(column="year", op="ge", value=2000)], limit=10)
    ids = [h.record_id for h in result.hits]
    assert recs[0].id in ids and recs[1].id not in ids


async def test_upsert_updates_in_place(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    rec = _Rec("Original", 2000)
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)
    rec.fields["title"] = "Rewritten"
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)

    result = await engine.search(sid, filters=[IndexFilter(column="year", op="eq", value=2000)], limit=10)
    assert len([h for h in result.hits if h.record_id == rec.id]) == 1


async def test_delete_removes_rows(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    rec = _Rec("Doomed", 2010)
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)
    await engine.delete(sid, [rec.id])

    result = await engine.search(sid, filters=[IndexFilter(column="year", op="eq", value=2010)], limit=10)
    assert rec.id not in [h.record_id for h in result.hits]


async def test_ensure_table_evolves_to_superset(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    evolved = COLUMNS + [{"name": "doi", "dtype": "string[pyarrow]", "nullable": True, "review": None}]
    await engine.ensure_table(sid, evolved)  # idempotent + adds `doi`
    assert engine  # no exception; table now carries the new column


async def test_fts_total_counts_matches_not_table_rows(engine):
    # `count_rows` cannot evaluate the FTS match, so `total` must come from the match
    # set: 2 of 3 rows match "Deep"; the page respects `limit` but `total` reports 2.
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("Deep Learning Foundations", 2016), _Rec("Shallow Ponds", 1999), _Rec("Deep Sea Biology", 2005)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    result = await engine.search(sid, text="Deep", offset=0, limit=1)
    assert len(result.hits) == 1
    assert result.total == 2


async def test_sql_type_covers_every_mapped_arrow_type():
    # Create-path (`arrow_schema_for`) and evolve-path (`add_columns` cast) must agree:
    # every Arrow type `arrow_type_for` can produce needs a SQL type entry, or an evolved
    # column (e.g. datetime) would silently become `string`.
    from extralit_server.index.lancedb_engine import _SQL_TYPE_BY_ARROW
    from extralit_server.index.mapping import _ARROW_BY_DTYPE

    for arrow_type in set(_ARROW_BY_DTYPE.values()):
        assert arrow_type in _SQL_TYPE_BY_ARROW, f"no SQL type for Arrow type {arrow_type}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/index/test_lancedb_engine.py -v`
Expected: FAIL — `extralit_server.index.lancedb_engine` does not exist.

- [ ] **Step 3: Write the implementation**

Create `extralit-server/src/extralit_server/index/lancedb_engine.py`:

```python
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
from extralit_server.index.mapping import arrow_schema_for, arrow_type_for, table_name_for
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


def _sql_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _where_clause(filters: list[IndexFilter] | None) -> str | None:
    if not filters:
        return None
    clauses = []
    for f in filters:
        if f.op == "eq":
            clauses.append(f"{f.column} = {_sql_literal(f.value)}")
        elif f.op == "ge":
            clauses.append(f"{f.column} >= {_sql_literal(f.value)}")
        elif f.op == "le":
            clauses.append(f"{f.column} <= {_sql_literal(f.value)}")
        elif f.op == "in":
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

    async def table_names(self) -> list[str]:
        db = await self._conn()
        return list(await db.table_names())

    async def ensure_table(self, schema_id: UUID, columns: list[dict[str, Any]]) -> None:
        db = await self._conn()
        name = table_name_for(schema_id)
        schema = arrow_schema_for(columns)
        if name not in await db.table_names():
            table = await db.create_table(name, schema=schema)
            await table.create_index("text", config=FTS())
            return
        # Evolve: add any columns present in `columns` but missing from the live table.
        table = await db.open_table(name)
        existing = set((await table.schema()).names)
        to_add = {c["name"]: f"cast(NULL as {_sql_type_for(c['dtype'])})" for c in columns if c["name"] not in existing}
        if to_add:
            await table.add_columns(to_add)

    async def drop_table(self, schema_id: UUID) -> None:
        db = await self._conn()
        name = table_name_for(schema_id)
        if name in await db.table_names():
            await db.drop_table(name)

    async def upsert(self, schema_id: UUID, rows: list[dict[str, Any]], columns: list[dict[str, Any]]) -> None:
        if not rows:
            return
        db = await self._conn()
        table = await db.open_table(table_name_for(schema_id))
        data = pa.Table.from_pylist(rows, schema=arrow_schema_for(columns))
        await (
            table.merge_insert("record_id").when_matched_update_all().when_not_matched_insert_all().execute(data)
        )
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
        if name not in await db.table_names():
            return IndexSearchResult(hits=[], total=0)
        table = await db.open_table(name)
        clause = _where_clause(filters)

        if text:
            # `count_rows` only evaluates scalar predicates — it cannot apply the FTS
            # match, so the total for a text query must come from the match set itself.
            # Materialize matches up to a ceiling and page in Python; beyond the ceiling
            # the total saturates at _FTS_TOTAL_CEILING (documented, bounded work).
            query = (await table.search(text, query_type="fts"))
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/index/test_lancedb_engine.py -v`
Expected: 7 passed. (If `_score` is absent on the FTS result in the installed lancedb, read the actual column name from `arrow.schema.names` and adjust the `.get("_score")` key — the row-id assertions must still pass.)

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/index/lancedb_engine.py extralit-server/tests/integration/index/
git commit -m "feat(v2): LanceIndexEngine — per-schema table, FTS + scalar filter, merge-insert upsert"
```

---

## Task 5: `get_index_engine()` DI provider (`index/__init__.py`)

**Files:**
- Modify: `extralit-server/src/extralit_server/index/__init__.py`
- Test: `extralit-server/tests/integration/index/test_get_index_engine.py`

**Interfaces:**
- Produces: `async def get_index_engine() -> AsyncGenerator[IndexEngine, None]` — yields a `LanceIndexEngine.new_instance()` and closes it in `finally` (mirrors `search_engine.get_search_engine`). Usable as a FastAPI `Depends`.

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/integration/index/test_get_index_engine.py`:

```python
import pytest

from extralit_server.index import get_index_engine
from extralit_server.index.lancedb_engine import LanceIndexEngine

pytestmark = pytest.mark.asyncio


async def test_get_index_engine_yields_lance_engine(monkeypatch, tmp_path):
    monkeypatch.setattr("extralit_server.settings.settings.lancedb_uri", str(tmp_path / "lance"))
    seen = None
    async for engine in get_index_engine():
        seen = engine
    assert isinstance(seen, LanceIndexEngine)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/index/test_get_index_engine.py -v`
Expected: FAIL — `cannot import name 'get_index_engine' from 'extralit_server.index'`.

- [ ] **Step 3: Write the implementation**

Replace the (empty) `extralit-server/src/extralit_server/index/__init__.py` with:

```python
from collections.abc import AsyncGenerator

from extralit_server.index.base import IndexEngine
from extralit_server.index.lancedb_engine import LanceIndexEngine


async def get_index_engine() -> AsyncGenerator[IndexEngine, None]:
    """FastAPI dependency: yield a v2 index engine, closing it afterwards.

    Mirrors `search_engine.get_search_engine`. The engine is currently always
    LanceIndexEngine; a registry can be added if a second backend appears.
    """
    engine = await LanceIndexEngine.new_instance()
    try:
        yield engine
    finally:
        await engine.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/index/test_get_index_engine.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/index/__init__.py extralit-server/tests/integration/index/test_get_index_engine.py
git commit -m "feat(v2): get_index_engine DI provider (mirrors get_search_engine)"
```

---

## Task 6: Best-effort sync orchestration (`contexts/v2/index_sync.py`)

**Files:**
- Create: `extralit-server/src/extralit_server/contexts/v2/index_sync.py`
- Test: `extralit-server/tests/integration/contexts/v2/test_index_sync.py`

**Interfaces:**
- Consumes: `IndexEngine` (Task 3); `mapping.union_columns`, `mapping.record_to_row` (Task 2); `Schema`, `SchemaVersion`, `V2Record` ORM.
- Produces (all best-effort except `rebuild_schema_index`):
  - `async def table_columns(db, schema) -> list[dict]` — union of every version's `columns_cache` for the schema (the table superset).
  - `async def sync_schema_table(engine, db, schema) -> None` — ensure the Lance table exists/evolved to the superset. Swallows + logs on failure.
  - `async def sync_upserted_records(engine, db, schema, records) -> None` — build rows against the superset, `engine.upsert`. Swallows + logs.
  - `async def sync_deleted_records(engine, schema, record_ids) -> None` — `engine.delete`. Swallows + logs.
  - `async def rebuild_schema_index(engine, db, schema, *, batch_size=500) -> int` — drop, ensure, batch-upsert every record from Postgres; returns count. **Raises** on failure (explicit recovery path, not best-effort).

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/integration/contexts/v2/test_index_sync.py`:

```python
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from extralit_server.contexts.v2 import index_sync
from tests.factories import SchemaFactory, SchemaVersionFactory, V2RecordFactory

pytestmark = pytest.mark.asyncio


async def _published(db):
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(
        schema=schema,
        version=1,
        columns_cache=[{"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None}],
    )
    await schema.update(db, current_version_id=version.id)
    return schema, version


async def test_table_columns_unions_versions(db):
    schema, v1 = await _published(db)
    await SchemaVersionFactory.create(
        schema=schema,
        version=2,
        columns_cache=[
            {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
            {"name": "year", "dtype": "int64", "nullable": True, "review": None},
        ],
    )
    columns = await index_sync.table_columns(db, schema)
    assert {c["name"] for c in columns} == {"title", "year"}


async def test_sync_schema_table_calls_ensure(db):
    schema, _ = await _published(db)
    engine = AsyncMock()
    await index_sync.sync_schema_table(engine, db, schema)
    engine.ensure_table.assert_awaited_once()


async def test_sync_upserted_records_builds_rows(db):
    schema, version = await _published(db)
    record = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Hi"})
    engine = AsyncMock()
    await index_sync.sync_upserted_records(engine, db, schema, [record])
    engine.upsert.assert_awaited_once()
    args, kwargs = engine.upsert.call_args
    rows = args[1]
    assert rows[0]["title"] == "Hi"


async def test_sync_swallows_engine_errors(db):
    schema, version = await _published(db)
    record = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Hi"})
    engine = AsyncMock()
    engine.upsert.side_effect = RuntimeError("lance down")
    # Must NOT raise — best-effort.
    await index_sync.sync_upserted_records(engine, db, schema, [record])


async def test_rebuild_raises_on_failure(db):
    schema, _ = await _published(db)
    engine = AsyncMock()
    engine.drop_table.side_effect = RuntimeError("lance down")
    with pytest.raises(RuntimeError):
        await index_sync.rebuild_schema_index(engine, db, schema)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_index_sync.py -v`
Expected: FAIL — `extralit_server.contexts.v2.index_sync` does not exist.

- [ ] **Step 3: Write the implementation**

Create `extralit-server/src/extralit_server/contexts/v2/index_sync.py`:

```python
"""Best-effort synchronization between Postgres (truth) and the LanceDB index.

Sync hooks mirror v1's shape (ensure on publish, upsert after record commit, delete on
delete) but never fail the caller: any engine error is logged and swallowed, and the
`:rebuild-index` endpoint / reindex CLI is the recovery path (spec §15). Only
`rebuild_schema_index` raises, since the caller explicitly asked to rebuild.
"""

import logging
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.index.base import IndexEngine
from extralit_server.index.mapping import record_to_row, union_columns
from extralit_server.models.v2 import Schema, SchemaVersion, V2Record

_LOGGER = logging.getLogger("extralit_server.index")


async def table_columns(db: AsyncSession, schema: Schema) -> list[dict[str, Any]]:
    """The Lance table's column superset: union of every version's columns_cache."""
    caches = (
        (await db.execute(select(SchemaVersion.columns_cache).where(SchemaVersion.schema_id == schema.id)))
        .scalars()
        .all()
    )
    return union_columns([c or [] for c in caches])


async def sync_schema_table(engine: IndexEngine, db: AsyncSession, schema: Schema) -> None:
    try:
        columns = await table_columns(db, schema)
        await engine.ensure_table(schema.id, columns)
    except Exception as exc:  # noqa: BLE001 — best-effort; truth is in Postgres
        _LOGGER.warning("Index ensure_table failed for schema %s: %s", schema.id, exc)


async def sync_upserted_records(
    engine: IndexEngine, db: AsyncSession, schema: Schema, records: list[V2Record]
) -> None:
    if not records:
        return
    try:
        columns = await table_columns(db, schema)
        await engine.ensure_table(schema.id, columns)
        rows = [record_to_row(record, columns) for record in records]
        await engine.upsert(schema.id, rows, columns)
    except Exception as exc:  # noqa: BLE001
        record_ids = [str(r.id) for r in records]
        _LOGGER.warning("Index upsert failed for schema %s records %s: %s", schema.id, record_ids, exc)


async def sync_deleted_records(engine: IndexEngine, schema: Schema, record_ids: Iterable[UUID]) -> None:
    ids = list(record_ids)
    if not ids:
        return
    try:
        await engine.delete(schema.id, ids)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Index delete failed for schema %s records %s: %s", schema.id, ids, exc)


async def rebuild_schema_index(
    engine: IndexEngine, db: AsyncSession, schema: Schema, *, batch_size: int = 500
) -> int:
    """Drop and repopulate the schema's Lance table from Postgres. Raises on failure."""
    columns = await table_columns(db, schema)
    await engine.drop_table(schema.id)
    await engine.ensure_table(schema.id, columns)

    total = 0
    offset = 0
    while True:
        records = (
            (
                await db.execute(
                    select(V2Record)
                    .where(V2Record.schema_id == schema.id)
                    .order_by(V2Record.inserted_at.asc())
                    .offset(offset)
                    .limit(batch_size)
                )
            )
            .scalars()
            .all()
        )
        if not records:
            break
        rows = [record_to_row(record, columns) for record in records]
        await engine.upsert(schema.id, rows, columns)
        total += len(records)
        offset += batch_size
    return total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_index_sync.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/contexts/v2/index_sync.py extralit-server/tests/integration/contexts/v2/test_index_sync.py
git commit -m "feat(v2): best-effort index sync orchestration + rebuild"
```

---

## Task 7: Wire schema-publish → `sync_schema_table`

**Files:**
- Modify: `extralit-server/src/extralit_server/api/v2/schemas.py`
- Test: `extralit-server/tests/integration/api/v2/test_schemas.py` (add one test)

**Interfaces:**
- Consumes: `get_index_engine` (Task 5), `index_sync.sync_schema_table` (Task 6).

- [ ] **Step 1: Write the failing test**

Append to `extralit-server/tests/integration/api/v2/test_schemas.py`:

```python
async def test_publish_version_creates_index_table(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    ensure = AsyncMock()
    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.sync_schema_table", ensure)

    from tests.factories import SchemaFactory

    schema = await SchemaFactory.create()
    import pandera.pandas as pa

    body = pa.DataFrameSchema(columns={"title": pa.Column(pa.String, nullable=False)}).to_json()
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/versions",
        headers=owner_auth_header,
        json={"body": body},
    )
    assert resp.status_code in (200, 201), resp.text
    ensure.assert_awaited_once()
```

(If `SchemaVersionCreate` requires more fields than `body`, mirror the existing publish test in this file — copy its request JSON and add the assertion.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_schemas.py::test_publish_version_creates_index_table -v`
Expected: FAIL — `sync_schema_table` is never awaited (patched mock has 0 calls).

- [ ] **Step 3: Wire the handler**

In `api/v2/schemas.py`, add imports at the top:

```python
from extralit_server.contexts.v2 import index_sync
from extralit_server.index import get_index_engine
from extralit_server.index.base import IndexEngine
```

Locate `publish_schema_version` (around line 106). Add the engine dependency to its signature and call sync after `publish_version` returns:

```python
async def publish_schema_version(
    *,
    schema_id: UUID,
    payload: SchemaVersionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    s3_client=Depends(files_ctx.get_s3_client),
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.publish(schema))
    workspace = await Workspace.get_or_raise(db, schema.workspace_id)
    version = await schemas_ctx.publish_version(
        db,
        s3_client,
        schema,
        body=payload.body,
        bucket=workspace.name,
        review_widgets=payload.review_widgets,
        created_by=current_user.id,
    )
    # Best-effort: ensure/evolve the Lance table to the new column superset.
    await index_sync.sync_schema_table(index_engine, db, schema)
    return version
```

(Preserve the exact argument names the existing `publish_version` call uses — copy them from the current handler body; only add the `index_engine` param and the `sync_schema_table` line.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_schemas.py -v`
Expected: all passing, including the new test.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/api/v2/schemas.py extralit-server/tests/integration/api/v2/test_schemas.py
git commit -m "feat(v2): ensure/evolve Lance table on schema publish (best-effort)"
```

---

## Task 8: Wire bulk-upsert + delete → sync

**Files:**
- Modify: `extralit-server/src/extralit_server/api/v2/records.py`
- Test: `extralit-server/tests/integration/api/v2/test_records.py` (add tests)

**Interfaces:**
- Consumes: `get_index_engine`, `index_sync.sync_upserted_records`, `index_sync.sync_deleted_records`.

- [ ] **Step 1: Write the failing test**

Append to `extralit-server/tests/integration/api/v2/test_records.py`:

```python
async def test_bulk_upsert_syncs_index(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    sync = AsyncMock()
    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.sync_upserted_records", sync)
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada", "age": 36}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 200, resp.text
    sync.assert_awaited_once()


async def test_bulk_upsert_survives_index_failure(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    # Real best-effort path: engine raises, request must still be 200.
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.upsert",
        AsyncMock(side_effect=RuntimeError("lance down")),
    )
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.ensure_table",
        AsyncMock(side_effect=RuntimeError("lance down")),
    )
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada", "age": 36}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 200, resp.text


async def test_delete_syncs_index(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    sync = AsyncMock()
    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.sync_deleted_records", sync)
    _patch_fetch(monkeypatch)
    schema, version = await _published_schema(db)
    from tests.factories import V2RecordFactory

    record = await V2RecordFactory.create(schema=schema, version=version, fields={"name": "X"})
    resp = await async_client.delete(
        f"/api/v2/schemas/{schema.id}/records?ids={record.id}",
        headers=owner_auth_header,
    )
    assert resp.status_code == 204, resp.text
    sync.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_records.py -k "syncs_index or survives_index" -v`
Expected: FAIL — sync mocks never awaited.

- [ ] **Step 3: Wire the handlers**

In `api/v2/records.py`, add imports:

```python
from extralit_server.contexts.v2 import index_sync
from extralit_server.index import get_index_engine
from extralit_server.index.base import IndexEngine
```

Add `index_engine` to `bulk_upsert_schema_records` and sync after the context returns:

```python
async def bulk_upsert_schema_records(
    *,
    schema_id: UUID,
    payload: RecordsBulkUpsert,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    s3_client=Depends(files_ctx.get_s3_client),
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.upsert_records(schema))
    workspace = await Workspace.get_or_raise(db, schema.workspace_id)
    records = await records_ctx.bulk_upsert_records(db, s3_client, schema, items=payload.items, bucket=workspace.name)
    await index_sync.sync_upserted_records(index_engine, db, schema, records)
    return Records(items=records, total=len(records))
```

Add `index_engine` to `delete_schema_records` and sync after the delete. Because `delete_records` only returns a rowcount, parse the ids once at the handler and pass them to both the context and the sync:

```python
async def delete_schema_records(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    ids: Annotated[str, Query(description="Comma-separated record ids to delete")],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.delete_records(schema))
    if not ids.strip():
        raise UnprocessableEntityError("No record IDs provided")
    record_ids = parse_uuids(ids)
    if len(record_ids) > DELETE_RECORDS_LIMIT:
        raise UnprocessableEntityError(f"Cannot delete more than {DELETE_RECORDS_LIMIT} records at once")
    await records_ctx.delete_records(db, schema, record_ids)
    await index_sync.sync_deleted_records(index_engine, schema, record_ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_records.py -v`
Expected: all passing, including the three new tests.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/api/v2/records.py extralit-server/tests/integration/api/v2/test_records.py
git commit -m "feat(v2): sync Lance index on record bulk-upsert and delete (best-effort)"
```

---

## Task 9: Search request schema + `:search` endpoint (PG hydration)

**Files:**
- Create: `extralit-server/src/extralit_server/api/schemas/v2/search.py`
- Modify: `extralit-server/src/extralit_server/api/v2/records.py`
- Test: `extralit-server/tests/integration/api/v2/test_records_search.py`

**Interfaces:**
- Consumes: `IndexEngine.search`, `IndexFilter`, `get_index_engine`; `RecordRead`/`Records` (existing); `V2Record` ORM.
- Produces:
  - `RecordFilter(BaseModel)`: `column: str`, `op: Literal["eq","in","ge","le"]`, `value: Any`.
  - `RecordSearchQuery(BaseModel)`: `text: str | None = None`, `filters: list[RecordFilter] = []`, `offset: int = 0` (`ge=0`), `limit: int = 50` (`ge=1, le=1000`).
  - Endpoint `POST /api/v2/schemas/{schema_id}/records:search -> Records`. Hits come from Lance; payloads are fetched from Postgres and returned in Lance's hit order; `total` is the engine's total.

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/integration/api/v2/test_records_search.py`:

```python
from unittest.mock import AsyncMock
from uuid import uuid4

import pandera.pandas as pa
import pytest

from extralit_server.index.base import IndexSearchHit, IndexSearchResult
from tests.factories import SchemaFactory, SchemaVersionFactory, V2RecordFactory

pytestmark = pytest.mark.asyncio

BODY = pa.DataFrameSchema(
    columns={"title": pa.Column(pa.String, nullable=False), "year": pa.Column(pa.Int, nullable=True)}
).to_json()


async def _published(db):
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(
        schema=schema,
        version=1,
        columns_cache=[
            {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
            {"name": "year", "dtype": "int64", "nullable": True, "review": None},
        ],
    )
    await schema.update(db, current_version_id=version.id)
    return schema, version


async def test_search_hydrates_from_postgres_in_hit_order(async_client, owner_auth_header, db, monkeypatch):
    schema, version = await _published(db)
    r1 = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Deep", "year": 2016})
    r2 = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Shallow", "year": 1999})

    # Engine returns r2 then r1; response must preserve that order and hydrate real payloads.
    fake = IndexSearchResult(hits=[IndexSearchHit(record_id=r2.id), IndexSearchHit(record_id=r1.id)], total=2)
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.search", AsyncMock(return_value=fake)
    )

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:search",
        headers=owner_auth_header,
        json={"text": "deep"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [str(r2.id), str(r1.id)]
    assert body["items"][1]["fields"]["title"] == "Deep"  # real PG payload, not from Lance


async def test_search_empty_result(async_client, owner_auth_header, db, monkeypatch):
    schema, _ = await _published(db)
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.search",
        AsyncMock(return_value=IndexSearchResult(hits=[], total=0)),
    )
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:search",
        headers=owner_auth_header,
        json={"filters": [{"column": "year", "op": "ge", "value": 3000}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"items": [], "total": 0}


async def test_search_requires_membership(async_client, annotator_auth_header, db):
    # `annotator_auth_header` is a non-member of the schema's workspace (repo idiom for
    # the 403 case; see test_records.py::test_non_member_cannot_read_records).
    schema, _ = await _published(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:search",
        headers=annotator_auth_header,
        json={"text": "x"},
    )
    assert resp.status_code == 403, resp.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_records_search.py -v`
Expected: FAIL — 404/405 (no `:search` route).

- [ ] **Step 3: Write the schema + endpoint**

Create `extralit-server/src/extralit_server/api/schemas/v2/search.py`:

```python
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
```

In `api/v2/records.py`, add imports:

```python
from extralit_server.api.schemas.v2.search import RecordSearchQuery
from extralit_server.index.base import IndexFilter
```

Add the endpoint (place it after the bulk-upsert handler):

```python
@router.post("/schemas/{schema_id}/records:search", response_model=Records)
async def search_schema_records(
    *,
    schema_id: UUID,
    payload: RecordSearchQuery,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Full-text (BM25) + scalar-filter search over a schema's records.

    Lance supplies matching record ids and scores; payloads are hydrated from Postgres
    (the source of truth) and returned in the engine's hit order. `total` is the engine's
    total match count, which may exceed the returned page.
    """
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.list_records(schema))

    filters = [IndexFilter(column=f.column, op=f.op, value=f.value) for f in payload.filters]
    result = await index_engine.search(
        schema.id, text=payload.text, filters=filters, offset=payload.offset, limit=payload.limit
    )
    if not result.hits:
        return Records(items=[], total=result.total)

    hit_ids = [hit.record_id for hit in result.hits]
    rows = (
        (await db.execute(select(V2Record).where(V2Record.id.in_(hit_ids), V2Record.schema_id == schema.id)))
        .scalars()
        .all()
    )
    by_id = {row.id: row for row in rows}
    ordered = [by_id[rid] for rid in hit_ids if rid in by_id]  # preserve Lance order; skip PG-missing (stale index)
    return Records(items=[RecordRead.model_validate(r) for r in ordered], total=result.total)
```

Add the SQLAlchemy `select` and `V2Record` imports if not already present at the top of `records.py`:

```python
from sqlalchemy import select

from extralit_server.models.v2 import Schema, V2Record
```

(`Schema` is already imported; add `V2Record` to that line and add the `select` import.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_records_search.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/api/schemas/v2/search.py extralit-server/src/extralit_server/api/v2/records.py extralit-server/tests/integration/api/v2/test_records_search.py
git commit -m "feat(v2): POST /schemas/{id}/records:search — Lance FTS + filter, PG hydration"
```

---

## Task 10: `:rebuild-index` endpoint

**Files:**
- Modify: `extralit-server/src/extralit_server/api/v2/records.py`
- Test: `extralit-server/tests/integration/api/v2/test_records_search.py` (add tests)

**Interfaces:**
- Consumes: `index_sync.rebuild_schema_index`, `SchemaPolicy.upsert_records` (rebuild is a write-class op → owner/admin).
- Produces: `POST /api/v2/schemas/{schema_id}:rebuild-index -> {"indexed": int}` (200). Surfaces engine errors (not best-effort) as 500.

- [ ] **Step 1: Write the failing test**

Append to `extralit-server/tests/integration/api/v2/test_records_search.py`:

```python
async def test_rebuild_index_reindexes_all_records(async_client, owner_auth_header, db, monkeypatch):
    schema, version = await _published(db)
    await V2RecordFactory.create(schema=schema, version=version, fields={"title": "A", "year": 2001})
    await V2RecordFactory.create(schema=schema, version=version, fields={"title": "B", "year": 2002})

    calls = {}

    async def fake_rebuild(engine, db_, s, *, batch_size=500):
        calls["schema_id"] = s.id
        return 2

    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.rebuild_schema_index", fake_rebuild)

    resp = await async_client.post(f"/api/v2/schemas/{schema.id}:rebuild-index", headers=owner_auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"indexed": 2}
    assert calls["schema_id"] == schema.id


async def test_rebuild_index_requires_write_access(async_client, annotator_auth_header, db):
    # Non-member of the workspace → 403 (repo idiom; see test_records.py negative-authz tests).
    schema, _ = await _published(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}:rebuild-index",
        headers=annotator_auth_header,
    )
    assert resp.status_code == 403, resp.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_records_search.py -k rebuild -v`
Expected: FAIL — no `:rebuild-index` route.

- [ ] **Step 3: Write the endpoint**

In `api/v2/records.py`, add:

```python
@router.post("/schemas/{schema_id}:rebuild-index")
async def rebuild_schema_index(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    index_engine: Annotated[IndexEngine, Depends(get_index_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    """Drop and repopulate the schema's Lance table from Postgres (the recovery path).

    Unlike the write-time sync hooks, this surfaces engine errors to the caller — the
    operator explicitly asked to rebuild.
    """
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.upsert_records(schema))
    indexed = await index_sync.rebuild_schema_index(index_engine, db, schema)
    return {"indexed": indexed}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_records_search.py -v`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/api/v2/records.py extralit-server/tests/integration/api/v2/test_records_search.py
git commit -m "feat(v2): POST /schemas/{id}:rebuild-index recovery endpoint"
```

---

## Task 11: Reindex CLI (`cli/index/`)

**Files:**
- Create: `extralit-server/src/extralit_server/cli/index/__init__.py`
- Create: `extralit-server/src/extralit_server/cli/index/__main__.py`
- Create: `extralit-server/src/extralit_server/cli/index/reindex.py`
- Modify: `extralit-server/src/extralit_server/cli/__init__.py`
- Test: `extralit-server/tests/integration/cli/test_index_reindex.py`

**Interfaces:**
- Consumes: `get_index_engine`, `index_sync.rebuild_schema_index`, `Schema` ORM, `AsyncSessionLocal`.
- Produces: `extralit_server index reindex [--schema-id UUID]` — rebuild one schema or every schema; `extralit_server index list` — print Lance table names. A reusable `Reindexer.reindex_schema(db, engine, schema_id)` and `Reindexer.reindex_all(db, engine)` (v2 twin of `cli/search_engine/reindex.py`, minus the v1 vectors/responses selectinloads).

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/integration/cli/__init__.py` (if absent, empty), then `extralit-server/tests/integration/cli/test_index_reindex.py`:

```python
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from extralit_server.cli.index.reindex import Reindexer
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_reindex_schema_rebuilds(db, monkeypatch):
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(schema=schema, version=1)
    await schema.update(db, current_version_id=version.id)

    rebuild = AsyncMock(return_value=0)
    monkeypatch.setattr("extralit_server.cli.index.reindex.rebuild_schema_index", rebuild)
    engine = AsyncMock()

    await Reindexer.reindex_schema(db, engine, schema.id)
    rebuild.assert_awaited_once()


async def test_reindex_all_iterates_schemas(db, monkeypatch):
    await SchemaFactory.create()
    await SchemaFactory.create()
    rebuild = AsyncMock(return_value=0)
    monkeypatch.setattr("extralit_server.cli.index.reindex.rebuild_schema_index", rebuild)
    engine = AsyncMock()

    count = await Reindexer.reindex_all(db, engine)
    assert count >= 2
    assert rebuild.await_count >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/cli/test_index_reindex.py -v`
Expected: FAIL — `extralit_server.cli.index` does not exist.

- [ ] **Step 3: Write the CLI**

Create `extralit-server/src/extralit_server/cli/index/reindex.py`:

```python
"""v2 index reindex CLI — the recovery path for the derived LanceDB index.

A lean twin of `cli/search_engine/reindex.py`: iterate schemas, and for each drop and
repopulate its Lance table from Postgres via `rebuild_schema_index`.
"""

import asyncio
from typing import Optional
from uuid import UUID

import typer
from rich.progress import Progress
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.cli.rich import echo_in_panel
from extralit_server.contexts.v2.index_sync import rebuild_schema_index
from extralit_server.database import AsyncSessionLocal
from extralit_server.index import get_index_engine
from extralit_server.index.base import IndexEngine
from extralit_server.models.v2 import Schema


class Reindexer:
    @classmethod
    async def reindex_schema(cls, db: AsyncSession, engine: IndexEngine, schema_id: UUID) -> int:
        schema = (await db.execute(select(Schema).filter_by(id=schema_id))).scalar_one()
        return await rebuild_schema_index(engine, db, schema)

    @classmethod
    async def reindex_all(cls, db: AsyncSession, engine: IndexEngine) -> int:
        schemas = (await db.execute(select(Schema).order_by(Schema.inserted_at.asc()))).scalars().all()
        for schema in schemas:
            await rebuild_schema_index(engine, db, schema)
        return len(schemas)


async def _reindex(schema_id: Optional[UUID] = None) -> None:
    async with AsyncSessionLocal() as db:
        async for engine in get_index_engine():
            with Progress() as progress:
                if schema_id is not None:
                    task = progress.add_task(f"reindexing schema {schema_id}...", total=1)
                    indexed = await Reindexer.reindex_schema(db, engine, schema_id)
                    progress.advance(task)
                    echo_in_panel(f"Reindexed {indexed} records.", title="Done", title_align="left")
                else:
                    schemas = await Reindexer.reindex_all(db, engine)
                    echo_in_panel(f"Reindexed {schemas} schema table(s).", title="Done", title_align="left")


async def _list_tables() -> None:
    async for engine in get_index_engine():
        for name in await engine.table_names():
            typer.echo(name)


def reindex(
    schema_id: Optional[UUID] = typer.Option(None, help="The id of a single schema to reindex"),
) -> None:
    asyncio.run(_reindex(schema_id))


def list() -> None:
    asyncio.run(_list_tables())
```

Create `extralit-server/src/extralit_server/cli/index/__main__.py`:

```python
from typer import Typer

from .reindex import list, reindex

app = Typer(help="Commands for the Extralit v2 LanceDB index.", no_args_is_help=True)

app.command(name="list", help="List existing LanceDB index tables.")(list)
app.command(name="reindex", help="Rebuild v2 schema index tables from Postgres.")(reindex)

if __name__ == "__main__":
    app()
```

Create `extralit-server/src/extralit_server/cli/index/__init__.py`:

```python
from .__main__ import app

__all__ = ["app"]
```

In `extralit-server/src/extralit_server/cli/__init__.py`, register the app (add the import next to the others and the `add_typer` next to the existing ones):

```python
from .index import app as index_app
...
app.add_typer(index_app, name="index")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/cli/test_index_reindex.py -v`
Expected: 2 passed.

- [ ] **Step 5: Verify CLI wiring loads**

Run: `cd extralit-server && uv run python -m extralit_server index --help`
Expected: help text listing `list` and `reindex` subcommands, exit 0.

- [ ] **Step 6: Commit**

```bash
git add extralit-server/src/extralit_server/cli/index/ extralit-server/src/extralit_server/cli/__init__.py extralit-server/tests/integration/cli/
git commit -m "feat(v2): index reindex CLI (extralit_server index reindex|list)"
```

---

## Task 12: Full-suite gate + lint

**Files:** none (verification only)

- [ ] **Step 1: Run the whole v2 + index test set**

Run:
```bash
cd extralit-server && uv run pytest tests/unit/index tests/integration/index tests/integration/contexts/v2 tests/integration/api/v2 tests/integration/cli/test_index_reindex.py -v
```
Expected: all pass. Investigate and fix any failure before proceeding — do not mark complete with red tests.

- [ ] **Step 2: Confirm v1 search_engine is untouched and still imports**

Run: `cd extralit-server && uv run python -c "import extralit_server.search_engine; import extralit_server.index; print('ok')"`
Expected: `ok` (v1 and v2 index packages coexist; no import-time collision).

- [ ] **Step 3: App-import smoke (registry coexistence)**

Run: `cd extralit-server && uv run python -c "from extralit_server.api.v2 import api_v2; from extralit_server._app import create_server_app; create_server_app(); print('ok')"`
Expected: `ok` (v1 and v2 mount together at `/api/v1` and `/api/v2`; `_app.create_server_app` is the real factory).

- [ ] **Step 4: Lint**

Run: `cd extralit-server && uv run ruff check src/extralit_server/index src/extralit_server/contexts/v2/index_sync.py src/extralit_server/cli/index src/extralit_server/api/v2 src/extralit_server/api/schemas/v2`
Expected: clean (the pre-existing `helpers.py` ASYNC240 noted in the Phase 2 plan is unrelated and out of scope).

- [ ] **Step 5: Commit any lint fixes**

```bash
git add -A
git commit -m "chore(v2): lint + gate for Phase 3 LanceDB index"
```

---

## Out of scope (recorded, not built here)

- **Embeddings / vector search / `similarity_search`** — deferred to the PDF-chunk-retrieval design session (spec §15). No vector column, no litellm, no lazy-dim evolution in this phase.
- **Compose `worker` volume mount** — only needed once workers write Lance (embedding jobs); Phase 3 sync runs inline in the web process and the reindex CLI runs in the server container, both of which already see the data volume. Defer to the embedding phase.
- **S3-backed Lance** — `EXTRALIT_LANCEDB_URI` accepts an `s3://` value through `lancedb.connect_async`, but MinIO commit-concurrency and per-query latency are unvalidated; unsupported for now.
- **`metadata` filtering in `:search`** — `record.metadata` is not projected into a filterable Lance column this phase (spec §15 future-work ledger).
- **Job-queue offload of sync** — sync is inline; offload is a later optimization (spec §6).
- **Deleting `search_engine/`** — happens at Phase 6 retirement, not now.

## Self-review notes

- **Spec §15 coverage:** local-default URI (Task 1) ✓; ES additive-only — no `search_engine/` edits, verified in Task 12 ✓; v1-mirrored hook points with a v2 `IndexEngine` (Tasks 3–8) ✓; best-effort log-and-continue failure semantics (Task 6, tested in Task 8) ✓; reindex CLI recovery path (Task 11) + `:rebuild-index` (Task 10) ✓; PG-hydrated search (Task 9) ✓; Lance row layout — system columns + typed columns + derived `text` FTS column (Task 2) ✓; embeddings deferred (Out of scope) ✓.
- **Spec §6/§7 coverage:** `upsert_records`/`delete_records`/`search`/`rebuild` engine surface (Tasks 3–4) ✓; `:search` text FTS + scalar filter, vector deferred (Task 9) ✓; reference grouping untouched (Phase 2) ✓.
- **Type consistency:** `ensure_table(schema_id, columns)`, `upsert(schema_id, rows, columns)`, `search(schema_id, *, text, filters, offset, limit) -> IndexSearchResult`, `IndexFilter(column, op, value)`, `record_to_row(record, columns)`, `table_columns(db, schema)` are used identically across the engine, sync context, routers, and CLI.
