# Schema Registry & Versioning Implementation Plan (Phase 1 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `Schema` entity (the v2 "Dataset") and its object-store-backed, versioned Pandera body — schema CRUD, version publishing, derived column cache, and server-side validation — as an isolated `/api/v2` module alongside untouched v1.

**Architecture:** New isolated v2 module set (`models/v2/`, `contexts/v2/`, `api/v2/`, `api/schemas/v2/`) sharing only `workspaces`/`users`/auth with v1. A `Schema` row is the core entity (1:1 with the UI's "Dataset"); each `SchemaVersion` row points at a Pandera `DataFrameSchema` JSON body stored in the workspace's object-store bucket (versioned via S3 `version_id`/`etag`), plus a denormalized `columns_cache` derived from that body for fast validation/UI. Postgres is the source of truth; the object store holds schema bodies.

**Tech Stack:** FastAPI, SQLAlchemy (async) + Alembic, Pandera (+ pandas), aioboto3 S3 (existing `contexts/files.py`), pytest-asyncio + factory-boy.

## Global Constraints

- Python 3.10+ (server). Use `uv` exclusively for deps: `uv add <pkg>`, `uv run <tool>`. Never edit `pyproject.toml` by hand for deps.
- All schema changes go through Alembic (`uv run alembic -c src/extralit_server/alembic.ini ...`).
- v1 back-compat is NOT a goal; do not modify v1 handlers/models in this phase (v2 is purely additive). v1 is retired in Phase 6.
- New tables/models use distinct names safe to run beside v1: tables `schemas`, `schema_versions`; ORM classes `Schema`, `SchemaVersion`.
- Postgres is source of truth; the object store holds Pandera bodies, versioned via native S3 `version_id`/`etag`.
- Object-store layout: bucket = workspace name (existing per-workspace bucket convention); schema body key = `schemas/{schema_id}/v{version}.json`.
- All work happens in the git branch `feat/schema-centric-data-model` (already created). Commit after every task.
- Run commands from `extralit-server/` unless noted. Test command: `uv run pytest <path> -v --disable-warnings`.

---

## File Structure

**Create:**
- `src/extralit_server/models/v2/__init__.py` — re-exports v2 ORM models for Alembic discovery.
- `src/extralit_server/models/v2/schemas.py` — `Schema`, `SchemaVersion` ORM models.
- `src/extralit_server/api/schemas/v2/__init__.py` — package marker.
- `src/extralit_server/api/schemas/v2/schemas.py` — Pydantic request/response models.
- `src/extralit_server/contexts/v2/__init__.py` — package marker.
- `src/extralit_server/contexts/v2/schema_bodies.py` — pure Pandera body helpers (column-cache derivation + record validation).
- `src/extralit_server/contexts/v2/schemas.py` — schema/version business logic (DB + object store).
- `src/extralit_server/api/v2/__init__.py` — `create_api_v2()` factory.
- `src/extralit_server/api/v2/schemas.py` — `/api/v2` schema router.
- `src/extralit_server/alembic/versions/<rev>_create_schema_and_schema_version_tables.py` — migration.
- `tests/unit/contexts/v2/__init__.py`, `tests/unit/contexts/v2/test_schema_bodies.py` — pure-logic tests.
- `tests/integration/api/v2/__init__.py`, `tests/integration/api/v2/test_schemas.py` — API tests.

**Modify:**
- `src/extralit_server/models/__init__.py` — import v2 models so `DatabaseModel.metadata` sees them.
- `src/extralit_server/enums.py` — add `SchemaKind`, `SchemaStatus`.
- `src/extralit_server/_app.py:212` area — mount `create_api_v2()` at `/api/v2`.
- `tests/factories.py` — add `SchemaFactory`, `SchemaVersionFactory`.

---

## Task 1: Add Pandera dependency and v2 enums

**Files:**
- Modify: `pyproject.toml` (via `uv add`), `src/extralit_server/enums.py`
- Test: `tests/unit/test_enums_v2.py` (Create)

**Interfaces:**
- Produces: `SchemaKind` (`singleton`|`table`), `SchemaStatus` (`draft`|`published`) in `extralit_server.enums`; `pandera` + `pandas` importable in the server venv.

- [ ] **Step 1: Add pandera (pulls pandas)**

Run: `uv add pandera`
Expected: resolves and installs `pandera` and `pandas`; `uv.lock` updated.

- [ ] **Step 2: Verify pandera imports**

Run: `uv run python -c "import pandera as pa, pandas as pd; print(pa.__version__, pd.__version__)"`
Expected: prints two version numbers, no ImportError.

- [ ] **Step 3: Write the failing test**

Create `tests/unit/test_enums_v2.py`:

```python
from extralit_server.enums import SchemaKind, SchemaStatus


def test_schema_kind_values():
    assert SchemaKind.singleton == "singleton"
    assert SchemaKind.table == "table"
    assert {k.value for k in SchemaKind} == {"singleton", "table"}


def test_schema_status_values():
    assert SchemaStatus.draft == "draft"
    assert SchemaStatus.published == "published"
    assert {s.value for s in SchemaStatus} == {"draft", "published"}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_enums_v2.py -v`
Expected: FAIL with `ImportError: cannot import name 'SchemaKind'`.

- [ ] **Step 5: Add the enums**

Append to `src/extralit_server/enums.py`:

```python
class SchemaKind(StrEnum):
    singleton = "singleton"  # exactly one row per `reference` (document-level extraction)
    table = "table"  # many rows per `reference` (table extraction)


class SchemaStatus(StrEnum):
    draft = "draft"
    published = "published"
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_enums_v2.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/extralit_server/enums.py tests/unit/test_enums_v2.py
git commit -m "feat(v2): add pandera dep and SchemaKind/SchemaStatus enums"
```

---

## Task 2: Pandera body helpers (column cache + validation)

Pure functions, no DB/IO — the validation core. TDD-friendly.

**Files:**
- Create: `src/extralit_server/contexts/v2/__init__.py` (empty), `src/extralit_server/contexts/v2/schema_bodies.py`
- Test: `tests/unit/contexts/v2/__init__.py` (empty), `tests/unit/contexts/v2/test_schema_bodies.py`

**Interfaces:**
- Produces:
  - `derive_columns_cache(body_json: str) -> list[dict]` — each dict `{"name": str, "dtype": str, "nullable": bool, "review": dict | None}`.
  - `validate_record_fields(body_json: str, fields: dict) -> dict` — returns coerced fields; raises `SchemaValidationError(errors: list[dict])` on failure.
  - `SchemaValidationError(Exception)` with `.errors: list[dict]`.
- Consumes: `pandera`, `pandas`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/contexts/v2/__init__.py` (empty) and `tests/unit/contexts/v2/test_schema_bodies.py`:

```python
import pandera as pa
import pytest

from extralit_server.contexts.v2.schema_bodies import (
    SchemaValidationError,
    derive_columns_cache,
    validate_record_fields,
)


def _body() -> str:
    schema = pa.DataFrameSchema(
        columns={
            "name": pa.Column(pa.String, nullable=False),
            "age": pa.Column(pa.Int, nullable=True),
        }
    )
    return schema.to_json()


def test_derive_columns_cache_lists_columns_with_dtype_and_nullable():
    cache = derive_columns_cache(_body())
    by_name = {c["name"]: c for c in cache}
    assert set(by_name) == {"name", "age"}
    assert by_name["name"]["nullable"] is False
    assert by_name["age"]["nullable"] is True
    assert "int" in by_name["age"]["dtype"].lower()


def test_validate_record_fields_coerces_and_returns():
    coerced = validate_record_fields(_body(), {"name": "Ada", "age": 36})
    assert coerced["name"] == "Ada"
    assert coerced["age"] == 36


def test_validate_record_fields_raises_on_type_error():
    with pytest.raises(SchemaValidationError) as exc:
        validate_record_fields(_body(), {"name": "Ada", "age": "not-a-number"})
    assert isinstance(exc.value.errors, list)
    assert len(exc.value.errors) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/contexts/v2/test_schema_bodies.py -v`
Expected: FAIL with `ModuleNotFoundError: extralit_server.contexts.v2.schema_bodies`.

- [ ] **Step 3: Implement the helpers**

Create `src/extralit_server/contexts/v2/__init__.py` (empty file) and `src/extralit_server/contexts/v2/schema_bodies.py`:

```python
"""Pure helpers for working with a Pandera DataFrameSchema body (JSON).

No DB or object-store access — given a schema body string, derive a denormalized
column cache and validate a single record's `fields` dict against it.
"""

from typing import Any

import pandas as pd
import pandera as pa


class SchemaValidationError(Exception):
    """Raised when a record's fields fail Pandera validation."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(f"Record failed schema validation with {len(errors)} error(s)")


def _load(body_json: str) -> pa.DataFrameSchema:
    return pa.DataFrameSchema.from_json(body_json)


def derive_columns_cache(body_json: str) -> list[dict[str, Any]]:
    """Return one entry per column: name, dtype, nullable, and optional review widget.

    The `review` widget is read from the Pandera column's `metadata` under the
    `review` key when present (e.g. {"review": {"type": "rating"}}).
    """
    schema = _load(body_json)
    cache: list[dict[str, Any]] = []
    for name, column in schema.columns.items():
        metadata = column.metadata or {}
        cache.append(
            {
                "name": name,
                "dtype": str(column.dtype),
                "nullable": bool(column.nullable),
                "review": metadata.get("review"),
            }
        )
    return cache


def validate_record_fields(body_json: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Validate+coerce a single record's fields against the schema body.

    Returns the coerced single-row mapping. Raises SchemaValidationError with a
    list of {column, check, error} dicts on failure.
    """
    schema = _load(body_json)
    frame = pd.DataFrame([fields])
    try:
        validated = schema.validate(frame, lazy=True)
    except pa.errors.SchemaErrors as exc:
        failures = exc.failure_cases
        errors = [
            {
                "column": row.get("column"),
                "check": row.get("check"),
                "error": str(row.get("failure_case")),
            }
            for row in failures.to_dict(orient="records")
        ]
        raise SchemaValidationError(errors) from exc
    return validated.iloc[0].to_dict()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/contexts/v2/test_schema_bodies.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/extralit_server/contexts/v2/__init__.py src/extralit_server/contexts/v2/schema_bodies.py tests/unit/contexts/v2/
git commit -m "feat(v2): pandera column-cache derivation and record validation helpers"
```

---

## Task 3: ORM models — Schema and SchemaVersion

**Files:**
- Create: `src/extralit_server/models/v2/__init__.py`, `src/extralit_server/models/v2/schemas.py`
- Modify: `src/extralit_server/models/__init__.py`
- Test: `tests/integration/models/v2/__init__.py` (Create), `tests/integration/models/v2/test_schema_models.py` (Create)

**Interfaces:**
- Produces ORM classes (in `extralit_server.models.v2.schemas`, re-exported from `extralit_server.models.v2`):
  - `Schema`: `id`, `workspace_id`, `name`, `kind` (`SchemaKind`), `status` (`SchemaStatus`), `current_version_id: UUID | None`, `settings: dict`, `inserted_at`, `updated_at`; relationship `versions: list[SchemaVersion]`. Uniq(`workspace_id`,`name`).
  - `SchemaVersion`: `id`, `schema_id`, `version: int`, `object_key`, `object_version_id: str | None`, `etag`, `checksum`, `parent_version_id: UUID | None`, `columns_cache: list`, `created_by: UUID | None`; relationship `schema: Schema`. Uniq(`schema_id`,`version`).

- [ ] **Step 1: Write the failing test**

Create `tests/integration/models/v2/__init__.py` (empty) and `tests/integration/models/v2/test_schema_models.py`:

```python
import pytest

from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import WorkspaceFactory

pytestmark = pytest.mark.asyncio


async def test_create_schema_and_version(db):
    workspace = await WorkspaceFactory.create()
    schema = await Schema.create(
        db,
        name="population",
        kind=SchemaKind.table,
        status=SchemaStatus.draft,
        workspace_id=workspace.id,
    )
    version = await SchemaVersion.create(
        db,
        schema_id=schema.id,
        version=1,
        object_key=f"schemas/{schema.id}/v1.json",
        etag="abc123",
        checksum="def456",
        columns_cache=[{"name": "n", "dtype": "str", "nullable": False, "review": None}],
    )
    assert schema.id is not None
    assert version.schema_id == schema.id
    assert version.version == 1

    loaded = await Schema.get(db, schema.id)
    assert loaded.name == "population"
    assert loaded.kind == SchemaKind.table
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/models/v2/test_schema_models.py -v`
Expected: FAIL with `ModuleNotFoundError: extralit_server.models.v2`.

- [ ] **Step 3: Implement the models**

Create `src/extralit_server/models/v2/schemas.py`:

```python
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.base import DatabaseModel

SchemaKindEnum = SAEnum(SchemaKind, name="schema_kind_enum")
SchemaStatusEnum = SAEnum(SchemaStatus, name="schema_status_enum")


class Schema(DatabaseModel):
    __tablename__ = "schemas"

    name: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[SchemaKind] = mapped_column(SchemaKindEnum, default=SchemaKind.table)
    status: Mapped[SchemaStatus] = mapped_column(SchemaStatusEnum, default=SchemaStatus.draft, index=True)
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schema_versions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default={})
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)

    versions: Mapped[list["SchemaVersion"]] = relationship(
        back_populates="schema",
        order_by="SchemaVersion.version",
        cascade="all, delete-orphan",
        foreign_keys="SchemaVersion.schema_id",
    )

    __table_args__ = (UniqueConstraint("workspace_id", "name", name="schema_workspace_id_name_uq"),)

    def __repr__(self) -> str:
        return f"Schema(id={self.id!s}, name={self.name!r}, kind={self.kind!r}, status={self.status!r})"


class SchemaVersion(DatabaseModel):
    __tablename__ = "schema_versions"

    schema_id: Mapped[UUID] = mapped_column(ForeignKey("schemas.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(index=True)
    object_key: Mapped[str] = mapped_column(Text)
    object_version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    parent_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schema_versions.id", ondelete="SET NULL"), nullable=True
    )
    columns_cache: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    schema: Mapped["Schema"] = relationship(back_populates="versions", foreign_keys=[schema_id])

    __table_args__ = (UniqueConstraint("schema_id", "version", name="schema_version_schema_id_version_uq"),)

    def __repr__(self) -> str:
        return f"SchemaVersion(id={self.id!s}, schema_id={self.schema_id!s}, version={self.version!r})"
```

Create `src/extralit_server/models/v2/__init__.py`:

```python
from extralit_server.models.v2.schemas import Schema, SchemaVersion

__all__ = ["Schema", "SchemaVersion"]
```

- [ ] **Step 4: Register v2 models for metadata discovery**

In `src/extralit_server/models/__init__.py`, add an import line so `DatabaseModel.metadata` includes the v2 tables (append after the existing model imports; keep alphabetical neighbours intact):

```python
from extralit_server.models.v2 import Schema, SchemaVersion  # noqa: F401
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/models/v2/test_schema_models.py -v`
Expected: PASS (the `db` fixture runs migrations to `head`; since the migration is not yet created this will FAIL with "relation schemas does not exist"). If so, proceed to Task 4 and re-run this test at Task 4 Step 5.

> Note: this model test depends on Task 4's migration. Commit the models now; the green run happens after Task 4.

- [ ] **Step 6: Commit**

```bash
git add src/extralit_server/models/v2/ src/extralit_server/models/__init__.py tests/integration/models/v2/
git commit -m "feat(v2): Schema and SchemaVersion ORM models"
```

---

## Task 4: Alembic migration for schemas + schema_versions

**Files:**
- Create: `src/extralit_server/alembic/versions/<rev>_create_schema_and_schema_version_tables.py`

**Interfaces:**
- Produces: `schemas` and `schema_versions` tables matching Task 3 models.

- [ ] **Step 1: Generate a migration skeleton (auto-fills revision + down_revision)**

Run: `uv run alembic -c src/extralit_server/alembic.ini revision --autogenerate -m "create schema and schema_version tables"`
Expected: a new file under `alembic/versions/`. Note its path. Autogenerate may produce partial ops; you will replace the `upgrade`/`downgrade` bodies in the next step with the exact content below (keep the generated `revision`/`down_revision` header lines).

- [ ] **Step 2: Replace the upgrade/downgrade bodies**

In the generated file, keep the top `revision`/`down_revision`/`branch_labels`/`depends_on` lines as generated; replace the bodies with:

```python
import sqlalchemy as sa
from alembic import op

# (keep the auto-generated revision/down_revision header lines above)


def upgrade() -> None:
    op.create_table(
        "schemas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.Enum("singleton", "table", name="schema_kind_enum"), nullable=False),
        sa.Column("status", sa.Enum("draft", "published", name="schema_status_enum"), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="schema_workspace_id_name_uq"),
    )
    op.create_index(op.f("ix_schemas_name"), "schemas", ["name"], unique=False)
    op.create_index(op.f("ix_schemas_status"), "schemas", ["status"], unique=False)
    op.create_index(op.f("ix_schemas_workspace_id"), "schemas", ["workspace_id"], unique=False)

    op.create_table(
        "schema_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("object_version_id", sa.Text(), nullable=True),
        sa.Column("etag", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("parent_version_id", sa.Uuid(), nullable=True),
        sa.Column("columns_cache", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("inserted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_version_id"], ["schema_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_id", "version", name="schema_version_schema_id_version_uq"),
    )
    op.create_index(op.f("ix_schema_versions_schema_id"), "schema_versions", ["schema_id"], unique=False)
    op.create_index(op.f("ix_schema_versions_version"), "schema_versions", ["version"], unique=False)

    # Deferred FK: schemas.current_version_id -> schema_versions.id (created after both tables exist)
    op.create_foreign_key(
        "schema_current_version_id_fk",
        "schemas",
        "schema_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("schema_current_version_id_fk", "schemas", type_="foreignkey")
    op.drop_index(op.f("ix_schema_versions_version"), table_name="schema_versions")
    op.drop_index(op.f("ix_schema_versions_schema_id"), table_name="schema_versions")
    op.drop_table("schema_versions")
    op.drop_index(op.f("ix_schemas_workspace_id"), table_name="schemas")
    op.drop_index(op.f("ix_schemas_status"), table_name="schemas")
    op.drop_index(op.f("ix_schemas_name"), table_name="schemas")
    op.drop_table("schemas")
    sa.Enum(name="schema_kind_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="schema_status_enum").drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 3: Apply the migration**

Run: `uv run alembic -c src/extralit_server/alembic.ini upgrade head`
Expected: applies cleanly, creating `schemas` and `schema_versions`.

- [ ] **Step 4: Verify downgrade then re-upgrade (round-trip)**

Run: `uv run alembic -c src/extralit_server/alembic.ini downgrade -1 && uv run alembic -c src/extralit_server/alembic.ini upgrade head`
Expected: both succeed with no errors.

- [ ] **Step 5: Run the Task 3 model test (now green)**

Run: `uv run pytest tests/integration/models/v2/test_schema_models.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add src/extralit_server/alembic/versions/
git commit -m "feat(v2): alembic migration for schemas and schema_versions tables"
```

---

## Task 5: Test factories for Schema and SchemaVersion

**Files:**
- Modify: `tests/factories.py`

**Interfaces:**
- Produces: `SchemaFactory` (SubFactory `WorkspaceFactory`), `SchemaVersionFactory` (SubFactory `SchemaFactory`) usable as `await SchemaFactory.create(...)`.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/models/v2/test_schema_factories.py`:

```python
import pytest

from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_schema_factory_creates_row(db):
    schema = await SchemaFactory.create(name="outcomes")
    assert isinstance(schema, Schema)
    assert schema.workspace_id is not None


async def test_schema_version_factory_links_schema(db):
    version = await SchemaVersionFactory.create()
    assert isinstance(version, SchemaVersion)
    assert version.schema_id is not None
    assert version.version >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/models/v2/test_schema_factories.py -v`
Expected: FAIL with `ImportError: cannot import name 'SchemaFactory'`.

- [ ] **Step 3: Add the factories**

In `tests/factories.py`, add the v2 import to the model import block:

```python
from extralit_server.models.v2 import Schema as SchemaModel
from extralit_server.models.v2 import SchemaVersion as SchemaVersionModel
```

and append (after `WorkspaceFactory` is defined, anywhere later in the file):

```python
class SchemaFactory(BaseFactory):
    class Meta:
        model = SchemaModel

    name = factory.Sequence(lambda n: f"schema-{n}")
    kind = SchemaKind.table
    status = SchemaStatus.draft
    workspace = factory.SubFactory(WorkspaceFactory)


class SchemaVersionFactory(BaseFactory):
    class Meta:
        model = SchemaVersionModel

    schema = factory.SubFactory(SchemaFactory)
    version = factory.Sequence(lambda n: n + 1)
    object_key = factory.LazyAttribute(lambda o: f"schemas/{o.schema.id}/v{o.version}.json")
    etag = factory.Sequence(lambda n: f"etag-{n}")
    checksum = factory.Sequence(lambda n: f"checksum-{n}")
    columns_cache = []
```

Add the enum import near the top of `tests/factories.py` (alongside the existing `from extralit_server.enums import ...` line):

```python
from extralit_server.enums import SchemaKind, SchemaStatus
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/models/v2/test_schema_factories.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/factories.py tests/integration/models/v2/test_schema_factories.py
git commit -m "test(v2): SchemaFactory and SchemaVersionFactory"
```

---

## Task 6: Pydantic API schemas (request/response)

**Files:**
- Create: `src/extralit_server/api/schemas/v2/__init__.py` (empty), `src/extralit_server/api/schemas/v2/schemas.py`
- Test: `tests/unit/api/schemas/v2/__init__.py` (empty), `tests/unit/api/schemas/v2/test_schema_models.py`

**Interfaces:**
- Produces Pydantic models in `extralit_server.api.schemas.v2.schemas`:
  - `SchemaCreate { name: str, kind: SchemaKind, workspace_id: UUID, settings: dict = {} }`
  - `SchemaUpdate { name: str | None, settings: dict | None }`
  - `SchemaVersionCreate { body: str }` (the Pandera `DataFrameSchema.to_json()` string)
  - `SchemaVersionRead` (from_attributes): `id, schema_id, version, object_key, object_version_id, etag, checksum, parent_version_id, columns_cache, inserted_at`
  - `SchemaRead` (from_attributes): `id, name, kind, status, current_version_id, settings, workspace_id, inserted_at, updated_at`
  - `Schemas { items: list[SchemaRead] }`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/api/schemas/v2/__init__.py` (empty) and `tests/unit/api/schemas/v2/test_schema_models.py`:

```python
from uuid import uuid4

from extralit_server.api.schemas.v2.schemas import SchemaCreate, SchemaVersionCreate
from extralit_server.enums import SchemaKind


def test_schema_create_defaults_settings_to_empty_dict():
    payload = SchemaCreate(name="population", kind=SchemaKind.table, workspace_id=uuid4())
    assert payload.settings == {}


def test_schema_version_create_requires_body():
    v = SchemaVersionCreate(body='{"columns": {}}')
    assert v.body.startswith("{")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/schemas/v2/test_schema_models.py -v`
Expected: FAIL with `ModuleNotFoundError: extralit_server.api.schemas.v2.schemas`.

- [ ] **Step 3: Implement the Pydantic models**

Create `src/extralit_server/api/schemas/v2/__init__.py` (empty) and `src/extralit_server/api/schemas/v2/schemas.py`:

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr

from extralit_server.enums import SchemaKind, SchemaStatus

SchemaName = constr(min_length=1, max_length=200)


class SchemaCreate(BaseModel):
    name: SchemaName
    kind: SchemaKind = SchemaKind.table
    workspace_id: UUID
    settings: dict[str, Any] = Field(default_factory=dict)


class SchemaUpdate(BaseModel):
    name: SchemaName | None = None
    settings: dict[str, Any] | None = None


class SchemaVersionCreate(BaseModel):
    body: str = Field(..., description="Pandera DataFrameSchema serialized via .to_json()")


class SchemaVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schema_id: UUID
    version: int
    object_key: str
    object_version_id: str | None
    etag: str
    checksum: str
    parent_version_id: UUID | None
    columns_cache: list[dict[str, Any]]
    inserted_at: datetime


class SchemaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: SchemaKind
    status: SchemaStatus
    current_version_id: UUID | None
    settings: dict[str, Any]
    workspace_id: UUID
    inserted_at: datetime
    updated_at: datetime


class Schemas(BaseModel):
    items: list[SchemaRead]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/api/schemas/v2/test_schema_models.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/extralit_server/api/schemas/v2/ tests/unit/api/schemas/v2/
git commit -m "feat(v2): pydantic request/response schemas for Schema and SchemaVersion"
```

---

## Task 7: Schema context (DB + object store, version publishing)

**Files:**
- Create: `src/extralit_server/contexts/v2/schemas.py`
- Test: `tests/integration/contexts/v2/__init__.py` (empty), `tests/integration/contexts/v2/test_schemas_context.py`

**Interfaces:**
- Consumes: `Schema`/`SchemaVersion` models; `contexts.files.put_object`; `contexts.v2.schema_bodies.derive_columns_cache`; `contexts.files.compute_hash`.
- Produces (all `async`, in `extralit_server.contexts.v2.schemas`):
  - `create_schema(db, *, name, kind, workspace_id, settings=None) -> Schema`
  - `get_schema(db, schema_id) -> Schema | None`
  - `list_schemas(db, *, workspace_id=None) -> list[Schema]`
  - `update_schema(db, schema, *, name=None, settings=None) -> Schema`
  - `delete_schema(db, schema) -> Schema`
  - `publish_version(db, s3_client, schema, *, body: str, bucket: str, created_by=None) -> SchemaVersion` — uploads body to `schemas/{schema_id}/v{n}.json`, derives `columns_cache`, creates the version, advances `schema.current_version_id`, sets `status=published`.
  - `object_key_for(schema_id, version) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/contexts/v2/__init__.py` (empty) and `tests/integration/contexts/v2/test_schemas_context.py`:

```python
from unittest.mock import AsyncMock

import pandera as pa
import pytest

from extralit_server.contexts.files import ObjectMetadata
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import WorkspaceFactory

pytestmark = pytest.mark.asyncio


def _body() -> str:
    return pa.DataFrameSchema(columns={"name": pa.Column(pa.String, nullable=False)}).to_json()


async def test_create_and_list_schema(db):
    ws = await WorkspaceFactory.create()
    schema = await schemas_ctx.create_schema(db, name="population", kind=SchemaKind.table, workspace_id=ws.id)
    assert isinstance(schema, Schema)

    listed = await schemas_ctx.list_schemas(db, workspace_id=ws.id)
    assert [s.id for s in listed] == [schema.id]


async def test_publish_version_uploads_body_and_advances_pointer(db):
    ws = await WorkspaceFactory.create()
    schema = await schemas_ctx.create_schema(db, name="population", kind=SchemaKind.table, workspace_id=ws.id)

    s3 = AsyncMock()
    # put_object returns ObjectMetadata; emulate via patching contexts.files.put_object
    version = await schemas_ctx.publish_version(
        db, s3, schema, body=_body(), bucket=ws.name, created_by=None
    )

    assert isinstance(version, SchemaVersion)
    assert version.version == 1
    assert version.object_key == f"schemas/{schema.id}/v1.json"
    assert any(c["name"] == "name" for c in version.columns_cache)

    refreshed = await Schema.get(db, schema.id)
    assert refreshed.current_version_id == version.id
    assert refreshed.status == SchemaStatus.published

    # Second publish increments version and links lineage
    v2 = await schemas_ctx.publish_version(db, s3, refreshed, body=_body(), bucket=ws.name)
    assert v2.version == 2
    assert v2.parent_version_id == version.id
```

> The test passes a bare `AsyncMock` as the S3 client. Implement `publish_version` to call `contexts.files.put_object`, which we patch in Step 3 via a thin wrapper so the mock works without real S3. See implementation note below.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/contexts/v2/test_schemas_context.py -v`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError: module ... has no attribute 'create_schema'`.

- [ ] **Step 3: Implement the context**

Create `src/extralit_server/contexts/v2/schemas.py`:

```python
"""Business logic for v2 Schemas and their object-store-backed versions."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2.schema_bodies import derive_columns_cache
from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client


def object_key_for(schema_id: UUID, version: int) -> str:
    return f"schemas/{schema_id}/v{version}.json"


async def create_schema(
    db: AsyncSession,
    *,
    name: str,
    kind: SchemaKind,
    workspace_id: UUID,
    settings: dict[str, Any] | None = None,
) -> Schema:
    return await Schema.create(
        db,
        name=name,
        kind=kind,
        workspace_id=workspace_id,
        settings=settings or {},
        status=SchemaStatus.draft,
    )


async def get_schema(db: AsyncSession, schema_id: UUID) -> Schema | None:
    return await Schema.get(db, schema_id)


async def list_schemas(db: AsyncSession, *, workspace_id: UUID | None = None) -> list[Schema]:
    stmt = select(Schema)
    if workspace_id is not None:
        stmt = stmt.filter_by(workspace_id=workspace_id)
    stmt = stmt.order_by(Schema.inserted_at)
    return (await db.execute(stmt)).scalars().all()


async def update_schema(
    db: AsyncSession,
    schema: Schema,
    *,
    name: str | None = None,
    settings: dict[str, Any] | None = None,
) -> Schema:
    values: dict[str, Any] = {}
    if name is not None:
        values["name"] = name
    if settings is not None:
        values["settings"] = settings
    if not values:
        return schema
    return await schema.update(db, **values)


async def delete_schema(db: AsyncSession, schema: Schema) -> Schema:
    return await schema.delete(db)


async def _next_version_number(db: AsyncSession, schema_id: UUID) -> int:
    versions = (
        (await db.execute(select(SchemaVersion).filter_by(schema_id=schema_id))).scalars().all()
    )
    return (max((v.version for v in versions), default=0)) + 1


async def publish_version(
    db: AsyncSession,
    s3_client: "S3Client",
    schema: Schema,
    *,
    body: str,
    bucket: str,
    created_by: UUID | None = None,
) -> SchemaVersion:
    """Upload a Pandera body to the object store and register a new SchemaVersion."""
    next_version = await _next_version_number(db, schema.id)
    key = object_key_for(schema.id, next_version)

    metadata = await files_ctx.put_object(
        s3_client, bucket, key, body, content_type="application/json"
    )

    parent = await db.get(SchemaVersion, schema.current_version_id) if schema.current_version_id else None

    version = await SchemaVersion.create(
        db,
        schema_id=schema.id,
        version=next_version,
        object_key=key,
        object_version_id=getattr(metadata, "version_id", None),
        etag=metadata.etag,
        checksum=files_ctx.compute_hash(body.encode("utf-8")),
        parent_version_id=parent.id if parent else None,
        columns_cache=derive_columns_cache(body),
        created_by=created_by,
        autocommit=False,
    )
    await schema.update(
        db, current_version_id=version.id, status=SchemaStatus.published, autocommit=False
    )
    await db.commit()
    return version
```

> Implementation note for the test mock: `files_ctx.put_object` calls `s3_client.put_object(...)` then `s3_client.head_object(...)`. With a bare `AsyncMock`, `head_object` returns an `AsyncMock`, and `ObjectMetadata` construction would fail. To keep the context test hermetic, patch `put_object` in the test instead of using the real one. Update the test's `test_publish_version_*` to add at the top of the test body:
>
> ```python
> from extralit_server.contexts import files as files_ctx
> files_ctx_put = AsyncMock(return_value=ObjectMetadata(
>     bucket_name=ws.name, object_name="k", etag="etag-1", size=1, last_modified=None,
>     content_type="application/json", version_id="ver-1", metadata={},
> ))
> monkeypatch.setattr("extralit_server.contexts.v2.schemas.files_ctx.put_object", files_ctx_put)
> ```
>
> and add `monkeypatch` to the test signature: `async def test_publish_version_uploads_body_and_advances_pointer(db, monkeypatch):`. (`ObjectMetadata.last_modified` accepts `None`; if its type rejects None, pass a fixed `datetime(2026, 1, 1)`.)

- [ ] **Step 4: Update the test per the mock note, then run**

Apply the monkeypatch note to the publish test. Run: `uv run pytest tests/integration/contexts/v2/test_schemas_context.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/extralit_server/contexts/v2/schemas.py tests/integration/contexts/v2/
git commit -m "feat(v2): schema context with object-store version publishing"
```

---

## Task 8: API router and `/api/v2` mount

**Files:**
- Create: `src/extralit_server/api/v2/__init__.py`, `src/extralit_server/api/v2/schemas.py`
- Modify: `src/extralit_server/_app.py`
- Test: `tests/integration/api/v2/__init__.py` (empty), `tests/integration/api/v2/test_schemas.py`

**Interfaces:**
- Consumes: `contexts.v2.schemas`, `contexts.files.get_s3_client`, `security.auth.get_current_user`, `database.get_async_db`.
- Produces endpoints under `/api/v2`:
  - `POST /schemas` → `SchemaRead` (201)
  - `GET /schemas?workspace_id=` → `Schemas`
  - `GET /schemas/{schema_id}` → `SchemaRead`
  - `PUT /schemas/{schema_id}` → `SchemaRead`
  - `DELETE /schemas/{schema_id}` → `SchemaRead`
  - `POST /schemas/{schema_id}/versions` → `SchemaVersionRead` (201)
  - `GET /schemas/{schema_id}/versions` → `list[SchemaVersionRead]`
  - `GET /schemas/{schema_id}/columns` → `list[dict]` (current version's `columns_cache`)

- [ ] **Step 1: Write the failing test**

Create `tests/integration/api/v2/__init__.py` (empty) and `tests/integration/api/v2/test_schemas.py`:

```python
import pandera as pa
import pytest

from extralit_server.enums import SchemaKind
from tests.factories import OwnerFactory, WorkspaceFactory

pytestmark = pytest.mark.asyncio


def _body() -> str:
    return pa.DataFrameSchema(columns={"name": pa.Column(pa.String, nullable=False)}).to_json()


async def test_create_get_list_schema(async_client, owner_auth_header):
    ws = await WorkspaceFactory.create()
    resp = await async_client.post(
        "/api/v2/schemas",
        headers=owner_auth_header,
        json={"name": "population", "kind": SchemaKind.table.value, "workspace_id": str(ws.id)},
    )
    assert resp.status_code == 201, resp.text
    schema_id = resp.json()["id"]

    resp = await async_client.get(f"/api/v2/schemas/{schema_id}", headers=owner_auth_header)
    assert resp.status_code == 200
    assert resp.json()["name"] == "population"

    resp = await async_client.get(
        f"/api/v2/schemas?workspace_id={ws.id}", headers=owner_auth_header
    )
    assert resp.status_code == 200
    assert [s["id"] for s in resp.json()["items"]] == [schema_id]


async def test_publish_version_and_columns(async_client, owner_auth_header, monkeypatch):
    from unittest.mock import AsyncMock
    from datetime import datetime
    from extralit_server.contexts.files import ObjectMetadata

    monkeypatch.setattr(
        "extralit_server.contexts.v2.schemas.files_ctx.put_object",
        AsyncMock(return_value=ObjectMetadata(
            bucket_name="b", object_name="k", etag="etag-1", size=1,
            last_modified=datetime(2026, 1, 1), content_type="application/json",
            version_id="ver-1", metadata={},
        )),
    )

    ws = await WorkspaceFactory.create()
    resp = await async_client.post(
        "/api/v2/schemas",
        headers=owner_auth_header,
        json={"name": "outcomes", "kind": SchemaKind.table.value, "workspace_id": str(ws.id)},
    )
    schema_id = resp.json()["id"]

    resp = await async_client.post(
        f"/api/v2/schemas/{schema_id}/versions",
        headers=owner_auth_header,
        json={"body": _body()},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 1

    resp = await async_client.get(f"/api/v2/schemas/{schema_id}/columns", headers=owner_auth_header)
    assert resp.status_code == 200
    assert any(c["name"] == "name" for c in resp.json())
```

> If your test suite's fixtures use different names than `async_client` / `owner_auth_header` / `OwnerFactory`, match the existing v1 API tests under `tests/integration/api/handlers/v1/`. Grep there first: `grep -rn "owner_auth_header\|async_client" tests/integration/api | head`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/api/v2/test_schemas.py -v`
Expected: FAIL with 404s (router not mounted) or fixture import error.

- [ ] **Step 3: Implement the router**

Create `src/extralit_server/api/v2/schemas.py`:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v2.schemas import (
    Schemas,
    SchemaCreate,
    SchemaRead,
    SchemaUpdate,
    SchemaVersionCreate,
    SchemaVersionRead,
)
from extralit_server.contexts import files as files_ctx
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError
from extralit_server.models import User, Workspace
from extralit_server.security import auth

router = APIRouter(tags=["v2: schemas"])


@router.post("/schemas", response_model=SchemaRead, status_code=status.HTTP_201_CREATED)
async def create_schema(
    *,
    payload: SchemaCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.create_schema(
        db,
        name=payload.name,
        kind=payload.kind,
        workspace_id=payload.workspace_id,
        settings=payload.settings,
    )
    return schema


@router.get("/schemas", response_model=Schemas)
async def list_schemas(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID | None, Query()] = None,
):
    items = await schemas_ctx.list_schemas(db, workspace_id=workspace_id)
    return Schemas(items=items)


@router.get("/schemas/{schema_id}", response_model=SchemaRead)
async def get_schema(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return schema


@router.put("/schemas/{schema_id}", response_model=SchemaRead)
async def update_schema(
    *,
    schema_id: UUID,
    payload: SchemaUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return await schemas_ctx.update_schema(db, schema, name=payload.name, settings=payload.settings)


@router.delete("/schemas/{schema_id}", response_model=SchemaRead)
async def delete_schema(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return await schemas_ctx.delete_schema(db, schema)


@router.post(
    "/schemas/{schema_id}/versions",
    response_model=SchemaVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_schema_version(
    *,
    schema_id: UUID,
    payload: SchemaVersionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    s3_client=Depends(files_ctx.get_s3_client),
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    workspace = await Workspace.get_or_raise(db, schema.workspace_id)
    return await schemas_ctx.publish_version(
        db, s3_client, schema, body=payload.body, bucket=workspace.name, created_by=current_user.id
    )


@router.get("/schemas/{schema_id}/versions", response_model=list[SchemaVersionRead])
async def list_schema_versions(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return sorted(await schema.awaitable_attrs.versions, key=lambda v: v.version)


@router.get("/schemas/{schema_id}/columns", response_model=list[dict])
async def get_schema_columns(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    if schema.current_version_id is None:
        return []
    from extralit_server.models.v2 import SchemaVersion

    version = await SchemaVersion.get(db, schema.current_version_id)
    return version.columns_cache if version else []
```

Create `src/extralit_server/api/v2/__init__.py`:

```python
from fastapi import FastAPI

from extralit_server._version import __version__ as extralit_version
from extralit_server.api.errors.v1.exception_handlers import add_exception_handlers as add_exception_handlers_v1
from extralit_server.api.handlers.v1 import authentication as authentication_v1
from extralit_server.api.v2 import schemas as schemas_v2
from extralit_server.errors.base_errors import __ALL__
from extralit_server.errors.error_handler import APIErrorHandler


def create_api_v2() -> FastAPI:
    api_v2 = FastAPI(
        title="Extralit v2",
        description="Extralit Server API v2 (schema-centric)",
        version=str(extralit_version),
        responses={error.HTTP_STATUS: error.api_documentation() for error in __ALL__},
    )
    APIErrorHandler.configure_app(api_v2)
    add_exception_handlers_v1(api_v2)

    # Auth endpoints are reused from v1 so v2 tokens work identically.
    api_v2.include_router(authentication_v1.router)
    api_v2.include_router(schemas_v2.router)
    return api_v2


api_v2 = create_api_v2()
```

- [ ] **Step 4: Mount the v2 app**

In `src/extralit_server/_app.py`, add the import near the existing `from extralit_server.api.routes import api_v1` (line ~26):

```python
from extralit_server.api.v2 import api_v2
```

and immediately after the existing `app.mount("/api/v1", api_v1)` (line ~212) add:

```python
    app.mount("/api/v2", api_v2)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/api/v2/test_schemas.py -v`
Expected: PASS (2 passed). If fixture names differ, adjust per the Step-1 note and re-run.

- [ ] **Step 6: Run the full v2 test set + lint**

Run:
```bash
uv run pytest tests/unit/test_enums_v2.py tests/unit/contexts/v2 tests/unit/api/schemas/v2 tests/integration/models/v2 tests/integration/contexts/v2 tests/integration/api/v2 -v
uv run ruff check src/extralit_server/api/v2 src/extralit_server/contexts/v2 src/extralit_server/models/v2 src/extralit_server/api/schemas/v2
```
Expected: all pass; ruff clean (fix any reported issues).

- [ ] **Step 7: Commit**

```bash
git add src/extralit_server/api/v2/ src/extralit_server/_app.py tests/integration/api/v2/
git commit -m "feat(v2): /api/v2 schema router with CRUD + version publishing"
```

---

## Self-Review (completed during authoring)

**Spec coverage (Phase 1 scope only):** Schema-as-entity ✓ (Task 3); object-store-backed
versioned body + thin DB registry + lineage ✓ (Tasks 3,4,7); `columns_cache` derived from
Pandera body ✓ (Task 2,7); server-side validation primitive ✓ (Task 2, consumed by records in
Phase 2); additive Alembic tables beside v1 ✓ (Task 4); isolated `/api/v2` module ✓ (Task 8).
Out-of-phase items (records, LanceDB, annotation, queue, migrator, retirements) are explicitly
deferred to Phases 2–6 below — not gaps.

**Placeholder scan:** none — every code/test step contains full content; the only deferred
value is the Alembic `revision`/`down_revision` header, which Alembic generates in Task 4 Step 1.

**Type consistency:** `derive_columns_cache`/`validate_record_fields`/`SchemaValidationError`
(Task 2) match their consumers in Task 7 and the `columns_cache` shape used in Tasks 3/5/8.
`publish_version` signature matches its router call in Task 8. Model field names match the
migration columns and the Pydantic `from_attributes` readers.

## Downstream phases (separate plans, written after this lands)

2. **Records** — `record` table (`schema_version_id` pin, `reference`, `fields` JSONB),
   validated bulk-upsert (consumes Task 2 helpers), `GET /references/{reference}` cross-schema view.
3. **LanceDB index** — `index/` engine (one table per schema, schema evolution), inline sync on
   record write, `:search`/similarity; delete `search_engine/` (ES/OpenSearch).
4. **Annotation v2** — `question` (column binding; table=N columns), `suggestion`, `response`.
5. **Queue** — `queue`/`queue_item`/`queue_assignment`, distribution/overlap, `GET /queues/{id}/next`.
6. **Migrator + retirement** — v1→v2 per-dataset migrator; delete v1 tables/handlers + frontend
   retirement ledger items from the spec §9.
