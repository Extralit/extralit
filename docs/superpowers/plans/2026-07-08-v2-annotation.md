# v2 Annotation (Phase 4) Implementation Plan

> **Historical note (2026-07-26):** The `/api/v2` parallel tree described in this document was folded back into `/api/v1`. See `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`. This document is kept as a historical record; its API paths, models, and file references may no longer exist.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the schema-centric annotation layer — questions (reviewable column bindings), suggestions (LLM pre-populated values), responses (human submissions), and a query-time projection view that resolves each reviewable cell — on top of the v2 records built in Phases 1–3.

**Architecture:** Three additive `v2_`-prefixed Postgres tables reached leanly by *reusing* v1's per-type value validators (not re-authoring them). Annotation is Postgres-only (no LanceDB sync). The product surface is a read-model "projection view" that resolves each cell as `submitted response (requesting user) → suggestion`, assembled at query time and exposed as a contract-stable API endpoint. See spec §17 (`docs/superpowers/specs/2026-06-27-schema-centric-data-model-design.md`).

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, async pytest + factory-boy. Package `extralit_server` under `extralit-server/src/`.

## Global Constraints

- **All commands run from `extralit-server/`** with `uv run` (e.g. `uv run pytest`, `uv run alembic -c src/extralit_server/alembic.ini ...`). Never use pip/poetry.
- **v2 naming (spec §14/§17.2):** ORM classes `V2Question`/`V2Suggestion`/`V2Response` on tables `v2_questions`/`v2_suggestions`/`v2_responses`; PG enums `v2_question_type_enum`/`v2_suggestion_type_enum`/`v2_response_status_enum`. A second declarative class named `Question`/`Suggestion`/`Response` breaks v1's string-based `relationship()` registry lookups.
- **Reuse, don't fork:** import v1's `QuestionType`, `SuggestionType`, `ResponseStatus` enums (`extralit_server.enums`) and v1's per-type value validators (`extralit_server.validators.response_values`). Do not duplicate them. `QuestionType` values are `text|rating|label_selection|multi_label_selection|ranking|span|table`.
- **Policy names are `V2`-prefixed:** `QuestionPolicy`/`SuggestionPolicy`/`ResponsePolicy` already exist for v1 in `api/policies/v1/__init__.py`. Use `V2QuestionPolicy`/`V2SuggestionPolicy`/`V2ResponsePolicy`.
- **No Lance sync for annotation (spec §17.5):** annotation contexts/handlers MUST NOT import `extralit_server.index` or `contexts.v2.index_sync`.
- **span deferred (spec §17.3):** `span` is a reserved enum value; question-create rejects `type=span` with a 422. No span anchor/validation in Phase 4.
- **No `record.status` transitions on response submit (spec §17.3):** response upsert never mutates `V2Record.status`.
- **Settings-level validation only (spec §17.3):** no Pandera re-run in annotation; `table` responses validate structure (dict, keys ⊆ `question.columns`) only.
- **Authorize before mutate:** every handler calls `await authorize(current_user, <Policy>.<action>(...))` before touching data, mirroring `api/v2/records.py`.
- **Test auth convention:** integration tests use the `async_client` fixture and dict header fixtures `owner_auth_header` / `annotator_auth_header` (defined in `tests/integration/conftest.py` as `{API_KEY_HEADER_NAME: user.api_key}`). For an arbitrary created user, build `{API_KEY_HEADER_NAME: user.api_key}` importing `API_KEY_HEADER_NAME` from `extralit_server.constants`. Never hardcode the header string.
- **Commit convention:** conventional commits (`feat:`, `test:`, `refactor:`); this repo commits plan/impl work directly to `develop`.

---

## File Structure

**Models** (`src/extralit_server/models/v2/`)
- Create `questions.py` — `V2Question` ORM.
- Create `suggestions.py` — `V2Suggestion` ORM.
- Create `responses.py` — `V2Response` ORM.
- Modify `__init__.py` — export the three classes.
- Modify `schemas.py` — remove `kind`/`SchemaKind` (Task 1).

**Migrations** (`src/extralit_server/alembic/versions/`)
- Create `<hash>_drop_schemas_kind.py` (Task 1).
- Create `<hash>_create_v2_annotation_tables.py` (Task 3).

**Enums** (`src/extralit_server/enums.py`)
- Modify to remove `SchemaKind` (Task 1). No new enums — reuse existing.

**API schemas** (`src/extralit_server/api/schemas/v2/`)
- Create `questions.py` — `QuestionCreate`/`QuestionUpdate`/`QuestionRead`/`Questions`.
- Create `annotation.py` — `SuggestionUpsert`/`SuggestionRead`, `ResponseUpsert`/`ResponseRead`.
- Create `projection.py` — `ProjectionCell`/`ProjectionRecord`/`ProjectionView`.

**Validators** (`src/extralit_server/validators/v2/`)
- Create `__init__.py` (empty).
- Create `questions.py` — `QuestionBindingValidator`.
- Create `values.py` — `V2ResponseValueValidator` (dispatch reusing v1 per-type validators) + `V2SuggestionValidator`.

**Contexts** (`src/extralit_server/contexts/v2/`)
- Create `annotation.py` — question CRUD + suggestion/response upsert/list.
- Create `projection.py` — projection-view assembly.
- Modify `schemas.py` — add `get_version_by_number`.

**Policies** (`src/extralit_server/api/policies/v1/`)
- Create `v2_annotation_policy.py` — `V2QuestionPolicy`, `V2SuggestionPolicy`, `V2ResponsePolicy`.
- Modify `__init__.py` — export the three.

**API handlers** (`src/extralit_server/api/v2/`)
- Create `questions.py` — `/schemas/{id}/questions` router.
- Create `annotation.py` — `/records/{id}/suggestions` + `/records/{id}/responses` router.
- Create `projection.py` — `/references/{ref}/view` router.
- Modify `schemas.py` — add `GET /schemas/{id}/versions/{version}`.
- Modify `__init__.py` — include the new routers.

**Factories** (`tests/factories.py`)
- Add `V2QuestionFactory`, `V2SuggestionFactory`, `V2ResponseFactory`; edit `SchemaFactory` (drop `kind`).

**Tests** (`tests/integration/`)
- `models/v2/test_annotation_models.py`, `contexts/v2/test_annotation_context.py`, `contexts/v2/test_projection.py`, `api/v2/test_questions.py`, `api/v2/test_annotation.py`, `api/v2/test_projection.py`, `api/v2/test_schema_versions.py`, and unit tests under `tests/unit/validators/v2/`.

---

## Task 1: Drop `schemas.kind` / `SchemaKind` (spec §14 prerequisite)

`kind` is emergent from question/column bindings, not a stored discriminator; §14 mandates removing it before question bindings are built.

**Files:**
- Modify: `src/extralit_server/models/v2/schemas.py` (remove `kind`, `SchemaKind`, `SchemaKindEnum`)
- Modify: `src/extralit_server/enums.py` (remove `SchemaKind`)
- Modify: `src/extralit_server/api/schemas/v2/schemas.py` (remove `kind` from `SchemaCreate:14` and `SchemaRead:52`)
- Modify: `src/extralit_server/contexts/v2/schemas.py` (remove the `kind` param from `create_schema:28,35`)
- Modify: `src/extralit_server/api/v2/schemas.py:45` (drop `kind=...` from the `create_schema(...)` call)
- Modify: `tests/factories.py:657` (`SchemaFactory` — remove `kind = SchemaKind.table`)
- Modify: `tests/integration/api/v2/test_schemas.py` (remove `SchemaKind` import + `"kind": ...` from the create body)
- Modify: `tests/integration/contexts/v2/test_schemas_context.py:39,49,74` (drop `kind=SchemaKind.table` from `create_schema(...)` calls + import)
- Create: `src/extralit_server/alembic/versions/<hash>_drop_schemas_kind.py`
- Test: `tests/integration/models/v2/test_schema_models.py` (remove any `kind` assertions)

**Interfaces:**
- Produces: `Schema` model, `SchemaCreate`/`SchemaRead`, and `create_schema(db, *, name, workspace_id, settings=...)` with no `kind`.

- [ ] **Step 1: Find every reference to `SchemaKind`/`kind`**

Run: `cd extralit-server && rg -n "SchemaKind|\bkind\b" src/extralit_server tests`
Expected: matches in `models/v2/schemas.py`, `enums.py`, `api/schemas/v2/schemas.py`, `contexts/v2/schemas.py`, `api/v2/schemas.py`, `tests/factories.py`, `tests/integration/api/v2/test_schemas.py`, `tests/integration/contexts/v2/test_schemas_context.py`. Every hit gets removed in the following steps.

- [ ] **Step 2: Remove `kind` from the `Schema` model**

In `src/extralit_server/models/v2/schemas.py`: delete the `SchemaKind` import, the `SchemaKindEnum = SAEnum(...)` line, the `kind: Mapped[SchemaKind] = mapped_column(...)` line, and the `kind={self.kind!r}` fragment in `__repr__`.

- [ ] **Step 3: Remove `kind` from the API schema, context, and handler call**

- `api/schemas/v2/schemas.py`: delete `kind: SchemaKind = SchemaKind.table` (in `SchemaCreate`) and `kind: SchemaKind` (in `SchemaRead`), and the `SchemaKind` import.
- `contexts/v2/schemas.py`: remove the `kind: "SchemaKind",` parameter from `create_schema` and the `kind=kind,` line in the `Schema(...)` construction; remove the `SchemaKind` import.
- `api/v2/schemas.py:45`: remove the `kind=payload.kind,` argument from the `create_schema(...)` call.

- [ ] **Step 4: Remove `SchemaKind` from enums, factory, and tests**

In `src/extralit_server/enums.py` delete the `class SchemaKind(StrEnum): ...` block. In `tests/factories.py` remove `kind = SchemaKind.table` and its import. In `tests/integration/api/v2/test_schemas.py` remove the `SchemaKind` import and the `"kind": SchemaKind.table.value,` body key. In `tests/integration/contexts/v2/test_schemas_context.py` remove `kind=SchemaKind.table` from the three `create_schema(...)` calls and the `SchemaKind` import.

- [ ] **Step 5: Verify imports resolve**

Run: `cd extralit-server && uv run python -c "import extralit_server.models.v2.schemas, extralit_server.enums, extralit_server.api.schemas.v2.schemas, extralit_server.contexts.v2.schemas, extralit_server.api.v2.schemas; import tests.factories" && cd extralit-server && rg -n "SchemaKind" src tests || echo "no SchemaKind references remain"`
Expected: no ImportError; `no SchemaKind references remain`.

- [ ] **Step 6: Autogenerate the drop migration**

Run: `cd extralit-server && uv run alembic -c src/extralit_server/alembic.ini revision --autogenerate -m "drop schemas.kind"`
Then open the generated file and confirm `upgrade()` contains `op.drop_column("schemas", "kind")`. Add an explicit enum-type drop after it (autogenerate misses PG enums):

```python
def upgrade() -> None:
    op.drop_column("schemas", "kind")
    op.execute("DROP TYPE IF EXISTS schema_kind_enum")


def downgrade() -> None:
    schema_kind = sa.Enum("singleton", "table", name="schema_kind_enum")
    schema_kind.create(op.get_bind(), checkfirst=True)
    op.add_column("schemas", sa.Column("kind", schema_kind, nullable=False, server_default="table"))
```

- [ ] **Step 7: Apply and run the affected schema tests**

Run: `cd extralit-server && uv run alembic -c src/extralit_server/alembic.ini upgrade head && uv run pytest tests/integration/models/v2/test_schema_models.py tests/integration/contexts/v2/test_schemas_context.py tests/integration/api/v2/test_schemas.py -q`
Expected: migration applies; tests pass (fix any remaining `kind` assertion by deleting it).

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "refactor(v2): drop schemas.kind (emergent from bindings, spec §14)"
```

---

## Task 2: v2 annotation ORM models

**Files:**
- Create: `src/extralit_server/models/v2/questions.py`
- Create: `src/extralit_server/models/v2/suggestions.py`
- Create: `src/extralit_server/models/v2/responses.py`
- Modify: `src/extralit_server/models/v2/__init__.py`

**Interfaces:**
- Produces: `V2Question(id, schema_id, name, title, description, type, columns, settings, required, inserted_at, updated_at)`; `V2Suggestion(id, record_id, question_id, value, score, agent, type, ...)`; `V2Response(id, record_id, user_id, values, status, ...)`. Imported as `from extralit_server.models.v2 import V2Question, V2Suggestion, V2Response`.

- [ ] **Step 1: Write `V2Question`**

Create `src/extralit_server/models/v2/questions.py`:

```python
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extralit_server.enums import QuestionType
from extralit_server.models.base import DatabaseModel

if TYPE_CHECKING:
    from extralit_server.models.v2.schemas import Schema

# Distinct PG enum name (v1 stores question type inside settings JSON, but v2 promotes it to a
# first-class column). Reuses the v1 QuestionType *values*.
V2QuestionTypeEnum = SAEnum(QuestionType, name="v2_question_type_enum")


class V2Question(DatabaseModel):
    """Reviewable column binding + review config (spec §17). Its settings drive per-cell
    value validation. `columns` binds >=1 schema column (exactly 1 for non-table types)."""

    __tablename__ = "v2_questions"

    schema_id: Mapped[UUID] = mapped_column(ForeignKey("schemas.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[QuestionType] = mapped_column(V2QuestionTypeEnum, index=True)
    columns: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    settings: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    required: Mapped[bool] = mapped_column(default=False)

    schema: Mapped["Schema"] = relationship("Schema")

    __table_args__ = (UniqueConstraint("schema_id", "name", name="v2_question_schema_id_name_uq"),)

    def __repr__(self) -> str:
        return f"V2Question(id={self.id!s}, schema_id={self.schema_id!s}, name={self.name!r}, type={self.type!r})"
```

- [ ] **Step 2: Write `V2Suggestion`**

Create `src/extralit_server/models/v2/suggestions.py`:

```python
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
```

- [ ] **Step 3: Write `V2Response`**

Create `src/extralit_server/models/v2/responses.py`:

```python
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
```

- [ ] **Step 4: Export from the package**

Replace `src/extralit_server/models/v2/__init__.py` with:

```python
from extralit_server.models.v2.questions import V2Question
from extralit_server.models.v2.records import V2Record
from extralit_server.models.v2.records import V2Record as Record  # v2-namespace alias
from extralit_server.models.v2.responses import V2Response
from extralit_server.models.v2.schemas import Schema, SchemaVersion
from extralit_server.models.v2.suggestions import V2Suggestion

__all__ = ["Record", "Schema", "SchemaVersion", "V2Question", "V2Record", "V2Response", "V2Suggestion"]
```

- [ ] **Step 5: Verify the models import and register**

Run: `cd extralit-server && uv run python -c "from extralit_server.models.v2 import V2Question, V2Suggestion, V2Response; print(V2Question.__tablename__, V2Suggestion.__tablename__, V2Response.__tablename__)"`
Expected: `v2_questions v2_suggestions v2_responses`

- [ ] **Step 6: Commit**

```bash
git add src/extralit_server/models/v2/ && git commit -m "feat(v2): add V2Question/V2Suggestion/V2Response models"
```

---

## Task 3: Migration + factories + model round-trip test

**Files:**
- Create: `src/extralit_server/alembic/versions/<hash>_create_v2_annotation_tables.py`
- Modify: `tests/factories.py`
- Test: `tests/integration/models/v2/test_annotation_models.py`

**Interfaces:**
- Consumes: models from Task 2.
- Produces: `V2QuestionFactory`, `V2SuggestionFactory`, `V2ResponseFactory` (in `tests/factories.py`); the three tables in the DB.

- [ ] **Step 1: Autogenerate the migration**

Run: `cd extralit-server && uv run alembic -c src/extralit_server/alembic.ini revision --autogenerate -m "create v2 annotation tables"`
Open the generated file. Confirm `upgrade()` creates `v2_questions`, `v2_suggestions`, `v2_responses` with their unique constraints. Ensure the three PG enums are created (SQLAlchemy usually emits `sa.Enum(..., name="v2_question_type_enum")` inline; if the autogenerated file references the enum without creating it, add explicit `create` calls at the top of `upgrade()` and `DROP TYPE` in `downgrade()`), e.g.:

```python
def downgrade() -> None:
    op.drop_table("v2_responses")
    op.drop_table("v2_suggestions")
    op.drop_table("v2_questions")
    op.execute("DROP TYPE IF EXISTS v2_response_status_enum")
    op.execute("DROP TYPE IF EXISTS v2_suggestion_type_enum")
    op.execute("DROP TYPE IF EXISTS v2_question_type_enum")
```

- [ ] **Step 2: Apply the migration**

Run: `cd extralit-server && uv run alembic -c src/extralit_server/alembic.ini upgrade head`
Expected: no error. Then `uv run alembic -c src/extralit_server/alembic.ini downgrade -1 && uv run alembic -c src/extralit_server/alembic.ini upgrade head` to confirm downgrade/upgrade round-trips cleanly.

- [ ] **Step 3: Add factories**

In `tests/factories.py`, add the imports (`V2Question as V2QuestionModel`, etc. following the existing `V2RecordModel` import style) and append after `V2RecordFactory`:

```python
class V2QuestionFactory(BaseFactory):
    class Meta:
        model = V2QuestionModel

    schema = factory.SubFactory(SchemaFactory)
    name = factory.Sequence(lambda n: f"question-{n}")
    title = factory.Sequence(lambda n: f"Question {n}")
    type = QuestionType.text
    columns = factory.LazyFunction(list)
    settings = factory.LazyAttribute(lambda o: {"type": o.type.value})
    required = False

    @classmethod
    async def _create(cls, model_class, *args, **kwargs):
        schema = kwargs.get("schema")
        if inspect.isawaitable(schema):
            schema = await schema
            kwargs["schema"] = schema
        if schema is not None:
            kwargs.setdefault("schema_id", schema.id)
        return await super()._create(model_class, *args, **kwargs)


class V2SuggestionFactory(BaseFactory):
    class Meta:
        model = V2SuggestionModel

    record = factory.SubFactory(V2RecordFactory)
    question = factory.SubFactory(V2QuestionFactory)
    value = "suggested"

    @classmethod
    async def _create(cls, model_class, *args, **kwargs):
        for key in ("record", "question"):
            obj = kwargs.get(key)
            if inspect.isawaitable(obj):
                obj = await obj
                kwargs[key] = obj
            if obj is not None:
                kwargs.setdefault(f"{key}_id", obj.id)
        return await super()._create(model_class, *args, **kwargs)


class V2ResponseFactory(BaseFactory):
    class Meta:
        model = V2ResponseModel

    record = factory.SubFactory(V2RecordFactory)
    user = factory.SubFactory(UserFactory)
    values = factory.LazyFunction(dict)
    status = ResponseStatus.submitted

    @classmethod
    async def _create(cls, model_class, *args, **kwargs):
        for key in ("record", "user"):
            obj = kwargs.get(key)
            if inspect.isawaitable(obj):
                obj = await obj
                kwargs[key] = obj
            if obj is not None:
                kwargs.setdefault(f"{key}_id", obj.id)
        return await super()._create(model_class, *args, **kwargs)
```

Add `QuestionType`, `ResponseStatus` to the `from extralit_server.enums import ...` line if not already imported.

- [ ] **Step 4: Write the model round-trip + uniqueness test**

Create `tests/integration/models/v2/test_annotation_models.py`:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from extralit_server.enums import QuestionType, ResponseStatus
from tests.factories import (
    SchemaFactory,
    UserFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2ResponseFactory,
    V2SuggestionFactory,
)


@pytest.mark.asyncio
async def test_question_persists_with_type_and_columns(db):
    q = await V2QuestionFactory.create(type=QuestionType.label_selection, columns=["disease"])
    assert q.id is not None
    assert q.type == QuestionType.label_selection
    assert q.columns == ["disease"]


@pytest.mark.asyncio
async def test_question_name_unique_per_schema(db):
    # Same schema OBJECT passed twice (not schema_id) so the (schema_id, name) constraint trips.
    schema = await SchemaFactory.create()
    await V2QuestionFactory.create(schema=schema, name="dup")
    with pytest.raises(IntegrityError):
        await V2QuestionFactory.create(schema=schema, name="dup")


@pytest.mark.asyncio
async def test_suggestion_unique_per_record_question(db):
    # Pass the parent OBJECTS (not *_id): the factories declare record/question as SubFactory
    # defaults, so passing only ids would let factory-boy create fresh parents and the
    # relationship would win on flush — the (record_id, question_id) constraint would never trip.
    record = await V2RecordFactory.create()
    question = await V2QuestionFactory.create()
    await V2SuggestionFactory.create(record=record, question=question)
    with pytest.raises(IntegrityError):
        await V2SuggestionFactory.create(record=record, question=question)


@pytest.mark.asyncio
async def test_response_unique_per_record_user(db):
    record = await V2RecordFactory.create()
    user = await UserFactory.create()
    r = await V2ResponseFactory.create(record=record, user=user, status=ResponseStatus.submitted,
                                       values={"q": {"value": "x"}})
    assert r.is_submitted
    with pytest.raises(IntegrityError):
        await V2ResponseFactory.create(record=record, user=user)
```

- [ ] **Step 5: Run the tests**

Run: `cd extralit-server && uv run pytest tests/integration/models/v2/test_annotation_models.py -q`
Expected: 4 passed. (If `db` fixture name differs, copy the fixture usage from `tests/integration/models/v2/test_record_models.py`.)

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(v2): migration + factories for v2 annotation tables"
```

---

## Task 4: Question binding validator

**Files:**
- Create: `src/extralit_server/validators/v2/__init__.py` (empty)
- Create: `src/extralit_server/validators/v2/questions.py`
- Test: `tests/unit/validators/v2/test_question_binding.py`

**Interfaces:**
- Consumes: `SchemaVersion.columns_cache` (list of `{"name", "dtype", "nullable", "review"}`), `QuestionType`.
- Produces: `QuestionBindingValidator.validate(*, type: QuestionType, columns: list[str], columns_cache: list[dict]) -> None` — raises `UnprocessableEntityError`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/validators/v2/test_question_binding.py`:

```python
import pytest

from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.v2.questions import QuestionBindingValidator

COLUMNS_CACHE = [
    {"name": "disease", "dtype": "str", "nullable": True, "review": None},
    {"name": "p_value", "dtype": "float64", "nullable": True, "review": None},
]


def test_non_table_binds_exactly_one_existing_column():
    QuestionBindingValidator.validate(type=QuestionType.label_selection, columns=["disease"], columns_cache=COLUMNS_CACHE)


def test_table_binds_one_or_more():
    QuestionBindingValidator.validate(type=QuestionType.table, columns=["disease", "p_value"], columns_cache=COLUMNS_CACHE)


def test_span_is_rejected():
    with pytest.raises(UnprocessableEntityError, match="span"):
        QuestionBindingValidator.validate(type=QuestionType.span, columns=["disease"], columns_cache=COLUMNS_CACHE)


def test_unknown_column_rejected():
    with pytest.raises(UnprocessableEntityError, match="unknown"):
        QuestionBindingValidator.validate(type=QuestionType.text, columns=["missing"], columns_cache=COLUMNS_CACHE)


def test_non_table_multiple_columns_rejected():
    with pytest.raises(UnprocessableEntityError, match="exactly one"):
        QuestionBindingValidator.validate(type=QuestionType.rating, columns=["disease", "p_value"], columns_cache=COLUMNS_CACHE)


def test_empty_binding_rejected():
    with pytest.raises(UnprocessableEntityError, match="at least one"):
        QuestionBindingValidator.validate(type=QuestionType.table, columns=[], columns_cache=COLUMNS_CACHE)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd extralit-server && uv run pytest tests/unit/validators/v2/test_question_binding.py -q`
Expected: FAIL — `ModuleNotFoundError: extralit_server.validators.v2.questions`.

- [ ] **Step 3: Implement the validator**

Create `src/extralit_server/validators/v2/__init__.py` (empty) and `src/extralit_server/validators/v2/questions.py`:

```python
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError

# span is reserved in the enum but deferred to the PDF-chunk design session (spec §17.3).
DEFERRED_TYPES = {QuestionType.span}


class QuestionBindingValidator:
    """Validate a question's column binding against the schema's current columns_cache
    (spec §17.3): existence + arity. Publish-time revalidation and dtype-compat are deferred."""

    @classmethod
    def validate(cls, *, type: QuestionType, columns: list[str], columns_cache: list[dict]) -> None:
        if type in DEFERRED_TYPES:
            raise UnprocessableEntityError(
                f"question type {type.value!r} (span) is not supported in this release; "
                "it is deferred to the PDF-chunk annotation design"
            )
        if not columns:
            raise UnprocessableEntityError("a question must bind at least one column")
        if type != QuestionType.table and len(columns) != 1:
            raise UnprocessableEntityError(
                f"question type {type.value!r} must bind exactly one column, got {len(columns)}"
            )

        known = {entry["name"] for entry in columns_cache}
        unknown = [name for name in columns if name not in known]
        if unknown:
            raise UnprocessableEntityError(
                f"unknown column(s) {unknown!r} for question binding; available columns: {sorted(known)!r}"
            )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd extralit-server && uv run pytest tests/unit/validators/v2/test_question_binding.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/extralit_server/validators/v2/ tests/unit/validators/v2/ && git commit -m "feat(v2): question column-binding validator"
```

---

## Task 5: Value validators (reuse v1 per-type)

**Files:**
- Create: `src/extralit_server/validators/v2/values.py`
- Test: `tests/unit/validators/v2/test_values.py`

**Interfaces:**
- Consumes: v1 per-type validators in `extralit_server.validators.response_values`; `QuestionType`.
- Produces:
  - `V2ResponseValueValidator.validate(value, *, type: QuestionType, settings: dict, columns: list[str]) -> None`
  - `V2SuggestionValidator.validate(value, score, *, type: QuestionType, settings: dict, columns: list[str]) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/validators/v2/test_values.py`:

```python
import pytest

from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.v2.values import V2ResponseValueValidator, V2SuggestionValidator

LABEL_SETTINGS = {"type": "label_selection", "options": [{"value": "yes"}, {"value": "no"}], "strict": True}
TABLE_SETTINGS = {"type": "table"}


def test_text_value_must_be_str():
    V2ResponseValueValidator.validate("ok", type=QuestionType.text, settings={"type": "text"}, columns=["c"])
    with pytest.raises(UnprocessableEntityError):
        V2ResponseValueValidator.validate(5, type=QuestionType.text, settings={"type": "text"}, columns=["c"])


def test_label_must_be_in_options():
    V2ResponseValueValidator.validate("yes", type=QuestionType.label_selection, settings=LABEL_SETTINGS, columns=["c"])
    with pytest.raises(UnprocessableEntityError):
        V2ResponseValueValidator.validate("maybe", type=QuestionType.label_selection, settings=LABEL_SETTINGS, columns=["c"])


def test_table_value_keys_must_be_subset_of_columns():
    V2ResponseValueValidator.validate({"a": 1}, type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"])
    with pytest.raises(UnprocessableEntityError, match="not bound"):
        V2ResponseValueValidator.validate({"z": 1}, type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"])


def test_span_value_is_rejected():
    with pytest.raises(UnprocessableEntityError, match="span"):
        V2ResponseValueValidator.validate([], type=QuestionType.span, settings={"type": "span"}, columns=["c"])


def test_suggestion_score_length_must_match_list_value():
    V2SuggestionValidator.validate(["yes"], [0.9], type=QuestionType.multi_label_selection,
                                   settings={"type": "multi_label_selection", "options": [{"value": "yes"}]}, columns=["c"])
    with pytest.raises(UnprocessableEntityError):
        V2SuggestionValidator.validate(["yes"], [0.9, 0.1], type=QuestionType.multi_label_selection,
                                       settings={"type": "multi_label_selection", "options": [{"value": "yes"}]}, columns=["c"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd extralit-server && uv run pytest tests/unit/validators/v2/test_values.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement, reusing v1 per-type validators**

Create `src/extralit_server/validators/v2/values.py`:

```python
from pydantic import TypeAdapter

from extralit_server.api.schemas.v1.questions import QuestionSettings
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.response_values import (
    LabelSelectionQuestionResponseValueValidator,
    MultiLabelSelectionQuestionResponseValueValidator,
    RankingQuestionResponseValueValidator,
    RatingQuestionResponseValueValidator,
    TextQuestionResponseValueValidator,
)

DEFERRED_TYPES = {QuestionType.span}


def _parsed(settings: dict):
    # Reuse v1's discriminated QuestionSettings union so options/ranges are typed like v1.
    return TypeAdapter(QuestionSettings).validate_python(settings)


class V2ResponseValueValidator:
    """Settings-level value validation reusing v1's per-type validators (spec §17.3).
    span is rejected (deferred); table validates structure only (no Pandera re-run)."""

    @classmethod
    def validate(cls, value, *, type: QuestionType, settings: dict, columns: list[str]) -> None:
        if type in DEFERRED_TYPES:
            raise UnprocessableEntityError(f"question type {type.value!r} (span) is not supported in this release")
        if type == QuestionType.text:
            TextQuestionResponseValueValidator(value).validate()
        elif type == QuestionType.label_selection:
            LabelSelectionQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.multi_label_selection:
            MultiLabelSelectionQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.rating:
            RatingQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.ranking:
            RankingQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.table:
            cls._validate_table(value, columns)
        else:
            raise UnprocessableEntityError(f"unknown question type {type!r}")

    @staticmethod
    def _validate_table(value, columns: list[str]) -> None:
        if not isinstance(value, dict):
            raise UnprocessableEntityError(f"table question expects a dict of values, found {type(value)}")
        bound = set(columns)
        extra = sorted(k for k in value if k not in bound)
        if extra:
            raise UnprocessableEntityError(f"table value keys {extra!r} are not bound columns; bound: {sorted(bound)!r}")


class V2SuggestionValidator:
    """Value validation (same as responses) + v1 score-cardinality checks (spec §17.3)."""

    @classmethod
    def validate(cls, value, score, *, type: QuestionType, settings: dict, columns: list[str]) -> None:
        V2ResponseValueValidator.validate(value, type=type, settings=settings, columns=columns)
        cls._validate_score(value, score)

    @staticmethod
    def _validate_score(value, score) -> None:
        if not isinstance(value, list) and isinstance(score, list):
            raise UnprocessableEntityError("a list of scores is not allowed for a single-value suggestion")
        if isinstance(value, list) and score is not None and not isinstance(score, list):
            raise UnprocessableEntityError("a single score is not allowed for a multi-item suggestion value")
        if isinstance(value, list) and isinstance(score, list) and len(value) != len(score):
            raise UnprocessableEntityError("number of items on value and score doesn't match")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd extralit-server && uv run pytest tests/unit/validators/v2/test_values.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/extralit_server/validators/v2/values.py tests/unit/validators/v2/test_values.py && git commit -m "feat(v2): value validators reusing v1 per-type validators"
```

---

## Task 6: Questions context + API + policy

**Files:**
- Create: `src/extralit_server/api/schemas/v2/questions.py`
- Create: `src/extralit_server/contexts/v2/annotation.py` (question functions)
- Create: `src/extralit_server/api/policies/v1/v2_annotation_policy.py` (`V2QuestionPolicy` now; suggestion/response classes added in Tasks 7–8)
- Modify: `src/extralit_server/api/policies/v1/__init__.py`
- Create: `src/extralit_server/api/v2/questions.py`
- Modify: `src/extralit_server/api/v2/__init__.py`
- Test: `tests/integration/contexts/v2/test_annotation_context.py`, `tests/integration/api/v2/test_questions.py`

**Interfaces:**
- Consumes: `QuestionBindingValidator`; `schemas_ctx.get_schema`; `SchemaVersion.columns_cache`.
- Produces:
  - `contexts.v2.annotation.create_question(db, schema, *, create: QuestionCreate) -> V2Question`, `list_questions(db, schema)`, `get_question(db, question_id)`, `update_question(db, question, *, update)`, `delete_question(db, question)`.
  - `V2QuestionPolicy.{list,get,create,update,delete}`.
  - Router at `POST|GET /schemas/{id}/questions`, `GET|PUT|DELETE /questions/{id}`.

- [ ] **Step 1: Write the API schemas**

Create `src/extralit_server/api/schemas/v2/questions.py`:

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from extralit_server.enums import QuestionType

QUESTION_COLUMNS_MIN = 1


class QuestionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1)
    description: str | None = None
    type: QuestionType
    columns: list[str] = Field(..., min_length=QUESTION_COLUMNS_MIN)
    settings: dict[str, Any] = Field(default_factory=dict)
    required: bool = False


class QuestionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    columns: list[str] | None = None
    settings: dict[str, Any] | None = None
    required: bool | None = None


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schema_id: UUID
    name: str
    title: str
    description: str | None
    type: QuestionType
    columns: list[str]
    settings: dict[str, Any]
    required: bool
    inserted_at: datetime
    updated_at: datetime


class Questions(BaseModel):
    items: list[QuestionRead]
```

- [ ] **Step 2: Write the failing context test**

Create `tests/integration/contexts/v2/test_annotation_context.py`:

```python
import pytest

from extralit_server.api.schemas.v2.questions import QuestionCreate
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.enums import QuestionType, SchemaStatus
from extralit_server.errors.future import UnprocessableEntityError
from tests.factories import SchemaFactory, SchemaVersionFactory


async def _published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(
        schema=schema,
        columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}],
    )
    schema.current_version_id = version.id
    await db.commit()
    return schema


@pytest.mark.asyncio
async def test_create_question_validates_binding(db):
    schema = await _published_schema(db)
    q = await annotation_ctx.create_question(
        db, schema, create=QuestionCreate(name="dx", title="Diagnosis", type=QuestionType.label_selection,
                                          columns=["disease"], settings={"type": "label_selection", "options": [{"value": "x"}]}),
    )
    assert q.id is not None and q.columns == ["disease"]


@pytest.mark.asyncio
async def test_create_question_rejects_unknown_column(db):
    schema = await _published_schema(db)
    with pytest.raises(UnprocessableEntityError, match="unknown"):
        await annotation_ctx.create_question(
            db, schema, create=QuestionCreate(name="bad", title="Bad", type=QuestionType.text, columns=["nope"]),
        )


@pytest.mark.asyncio
async def test_create_question_requires_published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.draft)  # current_version_id is None
    with pytest.raises(UnprocessableEntityError, match="published"):
        await annotation_ctx.create_question(
            db, schema, create=QuestionCreate(name="q", title="Q", type=QuestionType.text, columns=["disease"]),
        )
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_annotation_context.py -q`
Expected: FAIL — `annotation` module / functions missing.

- [ ] **Step 4: Implement the question context**

Create `src/extralit_server/contexts/v2/annotation.py`:

```python
"""Business logic for v2 annotation: questions, suggestions, responses (spec §17).

Postgres-only — this module MUST NOT import the LanceDB index engine."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v2.questions import QuestionCreate, QuestionUpdate
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.v2 import Schema, SchemaVersion, V2Question
from extralit_server.validators.v2.questions import QuestionBindingValidator


async def _current_columns_cache(db: AsyncSession, schema: Schema) -> list[dict]:
    if schema.current_version_id is None:
        raise UnprocessableEntityError(
            f"schema `{schema.id}` has no published version; publish a version before adding questions"
        )
    version = await SchemaVersion.get(db, schema.current_version_id)
    return list(version.columns_cache or [])


async def create_question(db: AsyncSession, schema: Schema, *, create: QuestionCreate) -> V2Question:
    columns_cache = await _current_columns_cache(db, schema)
    QuestionBindingValidator.validate(type=create.type, columns=create.columns, columns_cache=columns_cache)
    question = V2Question(
        schema_id=schema.id,
        name=create.name,
        title=create.title,
        description=create.description,
        type=create.type,
        columns=list(create.columns),
        settings=dict(create.settings),
        required=create.required,
    )
    db.add(question)
    await db.commit()
    return question


async def list_questions(db: AsyncSession, schema: Schema) -> list[V2Question]:
    stmt = select(V2Question).where(V2Question.schema_id == schema.id).order_by(V2Question.inserted_at.asc())
    return (await db.execute(stmt)).scalars().all()


async def get_question(db: AsyncSession, question_id: UUID) -> V2Question | None:
    return await V2Question.get(db, question_id)


async def update_question(db: AsyncSession, question: V2Question, *, update: QuestionUpdate) -> V2Question:
    if update.columns is not None:
        schema = await Schema.get_or_raise(db, question.schema_id)
        columns_cache = await _current_columns_cache(db, schema)
        QuestionBindingValidator.validate(type=question.type, columns=update.columns, columns_cache=columns_cache)
        question.columns = list(update.columns)
    for attr in ("title", "description", "settings", "required"):
        value = getattr(update, attr)
        if value is not None:
            setattr(question, attr, value)
    await db.commit()
    return question


async def delete_question(db: AsyncSession, question: V2Question) -> V2Question:
    await question.delete(db)
    return question
```

(If `DatabaseModel` lacks `.get`/`.get_or_raise`/`.delete`, copy the accessors used in `contexts/v2/schemas.py` — check that file for the exact helper names before implementing.)

- [ ] **Step 5: Run to verify the context tests pass**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_annotation_context.py -q`
Expected: 3 passed.

- [ ] **Step 6: Write the policy**

Create `src/extralit_server/api/policies/v1/v2_annotation_policy.py`:

```python
from uuid import UUID

from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User
from extralit_server.models.v2 import Schema, V2Question


class V2QuestionPolicy:
    @classmethod
    def list(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(schema.workspace_id)

        return is_allowed

    get = list

    @classmethod
    def create(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(schema.workspace_id))

        return is_allowed

    @classmethod
    def _write(cls, question: V2Question) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(question.schema.workspace_id))

        return is_allowed

    update = _write
    delete = _write
```

Add exports to `src/extralit_server/api/policies/v1/__init__.py`: `from extralit_server.api.policies.v1.v2_annotation_policy import V2QuestionPolicy` and add `"V2QuestionPolicy"` to `__all__`.

- [ ] **Step 7: Write the questions router**

Create `src/extralit_server/api/v2/questions.py`:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import V2QuestionPolicy, authorize
from extralit_server.api.schemas.v2.questions import (
    QuestionCreate,
    QuestionRead,
    Questions,
    QuestionUpdate,
)
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError
from extralit_server.models import User
from extralit_server.models.v2 import Schema, V2Question
from extralit_server.security import auth

router = APIRouter(tags=["v2: questions"])


async def _get_schema_or_404(db: AsyncSession, schema_id: UUID) -> Schema:
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return schema


async def _get_question_or_404(db: AsyncSession, question_id: UUID) -> V2Question:
    question = await annotation_ctx.get_question(db, question_id)
    if question is None:
        raise NotFoundError(f"Question with id `{question_id}` not found")
    return question


@router.post("/schemas/{schema_id}/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    *,
    schema_id: UUID,
    payload: QuestionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, V2QuestionPolicy.create(schema))
    return await annotation_ctx.create_question(db, schema, create=payload)


@router.get("/schemas/{schema_id}/questions", response_model=Questions)
async def list_questions(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, V2QuestionPolicy.list(schema))
    return Questions(items=await annotation_ctx.list_questions(db, schema))


@router.get("/questions/{question_id}", response_model=QuestionRead)
async def get_question(
    *,
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await _get_question_or_404(db, question_id)
    schema = await _get_schema_or_404(db, question.schema_id)
    await authorize(current_user, V2QuestionPolicy.get(schema))
    return question


@router.put("/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    *,
    question_id: UUID,
    payload: QuestionUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await _get_question_or_404(db, question_id)
    await authorize(current_user, V2QuestionPolicy.update(question))
    return await annotation_ctx.update_question(db, question, update=payload)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    *,
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await _get_question_or_404(db, question_id)
    await authorize(current_user, V2QuestionPolicy.delete(question))
    await annotation_ctx.delete_question(db, question)
```

Add `from extralit_server.api.v2 import questions as questions_v2` and `api_v2.include_router(questions_v2.router)` in `src/extralit_server/api/v2/__init__.py`.

- [ ] **Step 8: Write the API test**

Create `tests/integration/api/v2/test_questions.py` mirroring `tests/integration/api/v2/test_schemas.py` for auth/client fixtures. Cover: 201 create (happy), 422 unknown column, 422 span, 201→list returns it, 403 for a non-member annotator on create. Example core case:

```python
import pytest

from extralit_server.enums import QuestionType, SchemaStatus
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio

COLUMNS_CACHE = [{"name": "disease", "dtype": "str", "nullable": True, "review": None}]


async def _published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(schema=schema, columns_cache=COLUMNS_CACHE)
    schema.current_version_id = version.id
    await db.commit()
    return schema


async def test_create_question_happy(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "dx", "title": "Dx", "type": QuestionType.text.value, "columns": ["disease"]},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["columns"] == ["disease"]


async def test_create_question_span_rejected(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "s", "title": "S", "type": QuestionType.span.value, "columns": ["disease"]},
    )
    assert resp.status_code == 422
```

(The `owner` / `annotator` users and their `*_auth_header` fixtures come from `tests/integration/conftest.py`.)

- [ ] **Step 9: Run the question tests**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_questions.py tests/integration/contexts/v2/test_annotation_context.py -q`
Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "feat(v2): questions context, API, and policy"
```

---

## Task 7: Suggestions context + API + policy

**Files:**
- Create: `src/extralit_server/api/schemas/v2/annotation.py` (suggestion half)
- Modify: `src/extralit_server/contexts/v2/annotation.py` (add suggestion functions)
- Modify: `src/extralit_server/api/policies/v1/v2_annotation_policy.py` (add `V2SuggestionPolicy`) + `__init__.py`
- Create: `src/extralit_server/api/v2/annotation.py` (suggestion routes)
- Modify: `src/extralit_server/api/v2/__init__.py`
- Test: `tests/integration/api/v2/test_annotation.py` (suggestion cases)

**Interfaces:**
- Consumes: `V2SuggestionValidator`; `V2Record`, `V2Question`.
- Produces: `annotation.upsert_suggestion(db, record, question, *, upsert) -> V2Suggestion`, `annotation.list_suggestions(db, record) -> list[V2Suggestion]`; `V2SuggestionPolicy.{write,read}`; routes `PUT|GET /records/{id}/suggestions`.

- [ ] **Step 1: Write the suggestion API schema**

Create `src/extralit_server/api/schemas/v2/annotation.py`:

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from extralit_server.enums import ResponseStatus, SuggestionType


class SuggestionUpsert(BaseModel):
    question_id: UUID
    value: Any
    score: float | list[float] | None = None
    agent: str | None = None
    type: SuggestionType | None = None


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    question_id: UUID
    value: Any
    score: float | list[float] | None
    agent: str | None
    type: SuggestionType | None
    inserted_at: datetime
    updated_at: datetime


class Suggestions(BaseModel):
    items: list[SuggestionRead]


class ResponseUpsert(BaseModel):
    values: dict[str, dict[str, Any]] | None = None  # {question_name: {"value": ...}}
    status: ResponseStatus


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    record_id: UUID
    user_id: UUID
    values: dict[str, Any] | None
    status: ResponseStatus
    inserted_at: datetime
    updated_at: datetime
```

- [ ] **Step 2: Write the failing suggestion context test**

Append to `tests/integration/contexts/v2/test_annotation_context.py`:

```python
from extralit_server.api.schemas.v2.annotation import SuggestionUpsert
from tests.factories import V2QuestionFactory, V2RecordFactory


@pytest.mark.asyncio
async def test_upsert_suggestion_is_idempotent_per_record_question(db):
    schema = await _published_schema(db)
    question = await V2QuestionFactory.create(schema=schema, type=QuestionType.text, columns=["disease"],
                                              settings={"type": "text"})
    record = await V2RecordFactory.create(version__schema=schema)

    s1 = await annotation_ctx.upsert_suggestion(db, record, question,
                                                upsert=SuggestionUpsert(question_id=question.id, value="a"))
    s2 = await annotation_ctx.upsert_suggestion(db, record, question,
                                                upsert=SuggestionUpsert(question_id=question.id, value="b"))
    assert s1.id == s2.id and s2.value == "b"
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd extralit-server && uv run pytest "tests/integration/contexts/v2/test_annotation_context.py::test_upsert_suggestion_is_idempotent_per_record_question" -q`
Expected: FAIL — `upsert_suggestion` missing.

- [ ] **Step 4: Implement the suggestion context**

Append to `src/extralit_server/contexts/v2/annotation.py` (add imports for `select` already present, `V2Record`, `V2Suggestion`, `SuggestionUpsert`, `V2SuggestionValidator`):

```python
async def upsert_suggestion(db, record, question, *, upsert) -> "V2Suggestion":
    V2SuggestionValidator.validate(
        upsert.value, upsert.score, type=question.type, settings=question.settings, columns=question.columns
    )
    stmt = select(V2Suggestion).where(
        V2Suggestion.record_id == record.id, V2Suggestion.question_id == question.id
    )
    suggestion = (await db.execute(stmt)).scalar_one_or_none()
    if suggestion is None:
        suggestion = V2Suggestion(record_id=record.id, question_id=question.id)
        db.add(suggestion)
    suggestion.value = upsert.value
    suggestion.score = upsert.score
    suggestion.agent = upsert.agent
    suggestion.type = upsert.type
    await db.commit()
    return suggestion


async def list_suggestions(db, record) -> list["V2Suggestion"]:
    stmt = select(V2Suggestion).where(V2Suggestion.record_id == record.id).order_by(V2Suggestion.inserted_at.asc())
    return (await db.execute(stmt)).scalars().all()
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd extralit-server && uv run pytest "tests/integration/contexts/v2/test_annotation_context.py::test_upsert_suggestion_is_idempotent_per_record_question" -q`
Expected: PASS.

- [ ] **Step 6: Add `V2SuggestionPolicy`**

Append to `src/extralit_server/api/policies/v1/v2_annotation_policy.py` (import `V2Record`):

```python
class V2SuggestionPolicy:
    @classmethod
    def read(cls, record: "V2Record") -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(record.schema.workspace_id)

        return is_allowed

    @classmethod
    def write(cls, record: "V2Record") -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(record.schema.workspace_id))

        return is_allowed
```

Export `V2SuggestionPolicy` from `api/policies/v1/__init__.py`.

- [ ] **Step 7: Write the suggestion routes**

Create `src/extralit_server/api/v2/annotation.py` with a shared `_get_record_or_404` (loading the record with its `schema` relationship so policies can read `record.schema.workspace_id`) and the suggestion endpoints:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import V2SuggestionPolicy, authorize
from extralit_server.api.schemas.v2.annotation import SuggestionRead, Suggestions, SuggestionUpsert
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError, UnprocessableEntityError
from extralit_server.models import User
from extralit_server.models.v2 import V2Record
from extralit_server.security import auth

router = APIRouter(tags=["v2: annotation"])


async def _get_record_or_404(db: AsyncSession, record_id: UUID) -> V2Record:
    record = await V2Record.get(db, record_id, options=[selectinload(V2Record.schema)])
    if record is None:
        raise NotFoundError(f"Record with id `{record_id}` not found")
    return record


@router.put("/records/{record_id}/suggestions", response_model=SuggestionRead)
async def upsert_suggestion(
    *,
    record_id: UUID,
    payload: SuggestionUpsert,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    record = await _get_record_or_404(db, record_id)
    await authorize(current_user, V2SuggestionPolicy.write(record))
    question = await annotation_ctx.get_question(db, payload.question_id)
    if question is None or question.schema_id != record.schema_id:
        raise UnprocessableEntityError(f"question `{payload.question_id}` does not belong to this record's schema")
    return await annotation_ctx.upsert_suggestion(db, record, question, upsert=payload)


@router.get("/records/{record_id}/suggestions", response_model=Suggestions)
async def list_suggestions(
    *,
    record_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    record = await _get_record_or_404(db, record_id)
    await authorize(current_user, V2SuggestionPolicy.read(record))
    return Suggestions(items=await annotation_ctx.list_suggestions(db, record))
```

Add `from extralit_server.api.v2 import annotation as annotation_v2` and `api_v2.include_router(annotation_v2.router)` in `api/v2/__init__.py`. (Confirm `V2Record.get` accepts an `options=` kwarg by checking `DatabaseModel.get`; if not, load via a `select(...).options(...)` in the helper.)

- [ ] **Step 8: Write the suggestion API test**

Create `tests/integration/api/v2/test_annotation.py` with an owner PUT-ing a suggestion for a text question and asserting 200 + idempotent re-PUT, plus a 422 when the question belongs to a different schema. Reuse the schema/question/record setup pattern from `test_questions.py`.

- [ ] **Step 9: Run the tests**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_annotation.py tests/integration/contexts/v2/test_annotation_context.py -q`
Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "feat(v2): suggestions context, API, and policy"
```

---

## Task 8: Responses context + API + own-response policy

**Files:**
- Modify: `src/extralit_server/contexts/v2/annotation.py` (add response functions)
- Modify: `src/extralit_server/api/policies/v1/v2_annotation_policy.py` (add `V2ResponsePolicy`) + `__init__.py`
- Modify: `src/extralit_server/api/v2/annotation.py` (add response routes)
- Test: `tests/integration/contexts/v2/test_annotation_context.py`, `tests/integration/api/v2/test_annotation.py` (response cases)

**Interfaces:**
- Consumes: `V2ResponseValueValidator`; `V2Question`, `V2Record`, `V2Response`.
- Produces: `annotation.upsert_response(db, record, user, *, upsert) -> V2Response`, `annotation.get_response(db, record, user) -> V2Response | None`; `V2ResponsePolicy.{read,write}`; routes `PUT|GET /records/{id}/responses`.

- [ ] **Step 1: Write the failing response context test**

Append to `tests/integration/contexts/v2/test_annotation_context.py`:

```python
from extralit_server.api.schemas.v2.annotation import ResponseUpsert
from extralit_server.enums import ResponseStatus, V2RecordStatus
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_upsert_response_keyed_by_question_no_record_status_change(db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(schema=schema, name="dx", type=QuestionType.text, columns=["disease"],
                                   settings={"type": "text"}, required=True)
    record = await V2RecordFactory.create(version__schema=schema, status=V2RecordStatus.pending)
    user = await UserFactory.create()

    resp = await annotation_ctx.upsert_response(
        db, record, user, upsert=ResponseUpsert(status=ResponseStatus.submitted, values={"dx": {"value": "flu"}}))
    assert resp.values == {"dx": {"value": "flu"}}
    assert record.status == V2RecordStatus.pending  # spec §17.3: no status side-effect


@pytest.mark.asyncio
async def test_submitted_response_requires_required_question(db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(schema=schema, name="dx", type=QuestionType.text, columns=["disease"],
                                   settings={"type": "text"}, required=True)
    # A second, optional question (also bound to "disease" — binding validation allows reuse) so the
    # payload can be non-empty while omitting the required one. Submitting empty values would trip the
    # earlier "missing response values" guard instead of the required-question path under test.
    await V2QuestionFactory.create(schema=schema, name="notes", type=QuestionType.text, columns=["disease"],
                                   settings={"type": "text"}, required=False)
    record = await V2RecordFactory.create(version__schema=schema)
    user = await UserFactory.create()

    with pytest.raises(UnprocessableEntityError, match="required"):
        await annotation_ctx.upsert_response(
            db, record, user,
            upsert=ResponseUpsert(status=ResponseStatus.submitted, values={"notes": {"value": "n"}}))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd extralit-server && uv run pytest "tests/integration/contexts/v2/test_annotation_context.py::test_upsert_response_keyed_by_question_no_record_status_change" -q`
Expected: FAIL — `upsert_response` missing.

- [ ] **Step 3: Implement the response context**

Append to `src/extralit_server/contexts/v2/annotation.py` (imports: `V2Response`, `ResponseStatus`, `ResponseUpsert`, `V2ResponseValueValidator`):

```python
async def _schema_questions(db, schema_id) -> list["V2Question"]:
    stmt = select(V2Question).where(V2Question.schema_id == schema_id)
    return (await db.execute(stmt)).scalars().all()


def _validate_response_values(upsert, questions: list["V2Question"]) -> None:
    values = upsert.values or {}
    submitted = upsert.status == ResponseStatus.submitted
    if submitted and not values:
        raise UnprocessableEntityError("missing response values for submitted response")

    by_name = {q.name: q for q in questions}
    for name in values:
        if name not in by_name:
            raise UnprocessableEntityError(f"response value for non-configured question {name!r}")
    for question in questions:
        if submitted and question.required and question.name not in values:
            raise UnprocessableEntityError(f"missing response value for required question {question.name!r}")
    for name, wrapped in values.items():
        question = by_name[name]
        V2ResponseValueValidator.validate(
            wrapped.get("value"), type=question.type, settings=question.settings, columns=question.columns
        )


async def upsert_response(db, record, user, *, upsert) -> "V2Response":
    questions = await _schema_questions(db, record.schema_id)
    _validate_response_values(upsert, questions)

    stmt = select(V2Response).where(V2Response.record_id == record.id, V2Response.user_id == user.id)
    response = (await db.execute(stmt)).scalar_one_or_none()
    if response is None:
        response = V2Response(record_id=record.id, user_id=user.id)
        db.add(response)
    response.values = upsert.values
    response.status = upsert.status
    await db.commit()  # NOTE: never touches record.status (spec §17.3) and never syncs Lance.
    return response


async def get_response(db, record, user) -> "V2Response | None":
    stmt = select(V2Response).where(V2Response.record_id == record.id, V2Response.user_id == user.id)
    return (await db.execute(stmt)).scalar_one_or_none()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_annotation_context.py -q`
Expected: all pass (both new response tests + earlier).

- [ ] **Step 5: Add `V2ResponsePolicy` (own-response authz)**

Append to `src/extralit_server/api/policies/v1/v2_annotation_policy.py` (import `V2Response`):

```python
class V2ResponsePolicy:
    """Own-response authz (spec §17.5), ported from v1 ResponsePolicy with the workspace
    resolved via record.schema.workspace_id."""

    @classmethod
    def read(cls, record: "V2Record") -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(record.schema.workspace_id)

        return is_allowed

    @classmethod
    def upsert_own(cls, record: "V2Record") -> PolicyAction:
        # PUT writes the current user's own response; any workspace member (incl. annotators)
        # may write their own, matching v1 (actor.id == response.user_id).
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(record.schema.workspace_id)

        return is_allowed
```

Export `V2ResponsePolicy` from `api/policies/v1/__init__.py`.

- [ ] **Step 6: Add the response routes**

Append to `src/extralit_server/api/v2/annotation.py` (imports: `V2ResponsePolicy`, `ResponseRead`, `ResponseUpsert`, `annotation_ctx.get_response`):

```python
@router.put("/records/{record_id}/responses", response_model=ResponseRead)
async def upsert_response(
    *,
    record_id: UUID,
    payload: ResponseUpsert,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    record = await _get_record_or_404(db, record_id)
    await authorize(current_user, V2ResponsePolicy.upsert_own(record))
    return await annotation_ctx.upsert_response(db, record, current_user, upsert=payload)


@router.get("/records/{record_id}/responses", response_model=ResponseRead | None)
async def get_own_response(
    *,
    record_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    record = await _get_record_or_404(db, record_id)
    await authorize(current_user, V2ResponsePolicy.read(record))
    return await annotation_ctx.get_response(db, record, current_user)
```

- [ ] **Step 7: Write the response API test (incl. no-Lance-sync assertion)**

Add to `tests/integration/api/v2/test_annotation.py`: an annotator PUT-ing their own response (200), a second annotator getting only their own via GET, and an assertion that the index engine is never called. The no-sync assertion patches the engine and asserts zero calls:

```python
from unittest.mock import AsyncMock, patch


async def test_response_upsert_does_not_sync_lance(async_client, annotator_auth_header, db):
    # ... set up published schema + text question "dx" + record; make `annotator` a member of the
    #     schema's workspace (use WorkspaceUserFactory as v1 response tests do) ...
    with patch("extralit_server.contexts.v2.index_sync.sync_upserted_records", new=AsyncMock()) as synced:
        resp = await async_client.put(
            f"/api/v2/records/{record.id}/responses",
            headers=annotator_auth_header,
            json={"status": "submitted", "values": {"dx": {"value": "flu"}}},
        )
    assert resp.status_code == 200, resp.text
    synced.assert_not_called()  # annotation never touches the index engine (spec §17.5)
```

- [ ] **Step 8: Run the tests**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_annotation.py tests/integration/contexts/v2/test_annotation_context.py -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat(v2): responses context, API, and own-response policy"
```

---

## Task 9: Single-version read endpoint

Pulled into Phase 4 (spec §17.5) so the annotation UI can render records pinned to old versions.

**Files:**
- Modify: `src/extralit_server/contexts/v2/schemas.py` (add `get_version_by_number`)
- Modify: `src/extralit_server/api/v2/schemas.py` (add route)
- Modify: `src/extralit_server/api/schemas/v2/schemas.py` (add `SchemaVersionRead` if absent — check first)
- Test: `tests/integration/api/v2/test_schema_versions.py`

**Interfaces:**
- Consumes: `SchemaVersion`.
- Produces: `schemas_ctx.get_version_by_number(db, schema_id, version) -> SchemaVersion | None`; route `GET /schemas/{id}/versions/{version}`.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/api/v2/test_schema_versions.py`:

```python
import pytest

from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_get_single_version_by_number(async_client, owner_auth_header, db):
    schema = await SchemaFactory.create()
    await SchemaVersionFactory.create(
        schema=schema, version=1, columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}])
    await db.commit()

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/versions/1", headers=owner_auth_header)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == 1
    assert body["columns_cache"][0]["name"] == "disease"


async def test_get_unknown_version_404(async_client, owner_auth_header, db):
    schema = await SchemaFactory.create()
    await db.commit()
    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/versions/999", headers=owner_auth_header)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_schema_versions.py -q`
Expected: FAIL (404 route missing or wrong shape).

- [ ] **Step 3: Add the context function**

Append to `src/extralit_server/contexts/v2/schemas.py`:

```python
async def get_version_by_number(db: AsyncSession, schema_id: UUID, version: int) -> SchemaVersion | None:
    stmt = select(SchemaVersion).where(SchemaVersion.schema_id == schema_id, SchemaVersion.version == version)
    return (await db.execute(stmt)).scalar_one_or_none()
```

(Ensure `select` and `SchemaVersion` are imported in that file.)

- [ ] **Step 4: Add the route**

In `src/extralit_server/api/v2/schemas.py`, reuse or add a `SchemaVersionRead` response model (check `api/schemas/v2/schemas.py` for an existing version read schema; if none, add one exposing `id, schema_id, version, columns_cache, review_widgets, parent_version_id, inserted_at`) and add:

```python
@router.get("/schemas/{schema_id}/versions/{version}", response_model=SchemaVersionRead)
async def get_schema_version(
    *,
    schema_id: UUID,
    version: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, SchemaPolicy.get(schema))
    version_row = await schemas_ctx.get_version_by_number(db, schema_id, version)
    if version_row is None:
        raise NotFoundError(f"Version `{version}` not found for schema `{schema_id}`")
    return version_row
```

(Match the existing imports/helpers in `api/v2/schemas.py`; it already has `_get_schema_or_404`, `SchemaPolicy`, `authorize`, `NotFoundError`.)

- [ ] **Step 5: Run to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_schema_versions.py -q`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(v2): single schema-version read endpoint (§17.5)"
```

---

## Task 10: Projection view

The product read-surface (spec §17.4): per reference, resolve each reviewable cell as `submitted response (requesting user) → suggestion`, grouped by schema/record.

**Files:**
- Create: `src/extralit_server/api/schemas/v2/projection.py`
- Create: `src/extralit_server/contexts/v2/projection.py`
- Create: `src/extralit_server/api/v2/projection.py`
- Modify: `src/extralit_server/api/v2/__init__.py`
- Test: `tests/integration/contexts/v2/test_projection.py`, `tests/integration/api/v2/test_projection.py`

**Interfaces:**
- Consumes: `records_ctx.list_records_by_reference`; `annotation` question/suggestion/response reads; `V2Question`, `V2Suggestion`, `V2Response`.
- Produces: `projection.build_reference_view(db, *, workspace_id, reference, user) -> ProjectionView`; route `GET /projection/references/{reference:path}`.

- [ ] **Step 1: Write the projection schemas**

Create `src/extralit_server/api/schemas/v2/projection.py`:

```python
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ProjectionCell(BaseModel):
    question_name: str
    value: Any | None = None
    source: Literal["response", "suggestion"] | None = None  # None => neither exists yet


class ProjectionRecord(BaseModel):
    record_id: UUID
    schema_id: UUID
    reference: str
    cells: list[ProjectionCell]


class ProjectionView(BaseModel):
    reference: str
    records: list[ProjectionRecord]
    total_records: int
```

- [ ] **Step 2: Write the failing context test**

Create `tests/integration/contexts/v2/test_projection.py`:

```python
import pytest

from extralit_server.contexts.v2 import projection as projection_ctx
from extralit_server.enums import QuestionType, ResponseStatus, SchemaStatus
from tests.factories import (
    SchemaFactory, SchemaVersionFactory, UserFactory, V2QuestionFactory, V2RecordFactory,
    V2ResponseFactory, V2SuggestionFactory,
)


async def _schema_with_question(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published, workspace__name="wsp")
    version = await SchemaVersionFactory.create(
        schema=schema, columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}])
    schema.current_version_id = version.id
    q = await V2QuestionFactory.create(schema=schema, name="dx", type=QuestionType.text, columns=["disease"],
                                       settings={"type": "text"})
    await db.commit()
    return schema, version, q


@pytest.mark.asyncio
async def test_cell_resolves_to_suggestion_when_no_response(db):
    schema, version, q = await _schema_with_question(db)
    record = await V2RecordFactory.create(version=version, reference="doc-1")
    await V2SuggestionFactory.create(record=record, question=q, value="flu")
    user = await UserFactory.create()

    view = await projection_ctx.build_reference_view(
        db, workspace_id=schema.workspace_id, reference="doc-1", user=user)
    cell = view.records[0].cells[0]
    assert cell.value == "flu" and cell.source == "suggestion"


@pytest.mark.asyncio
async def test_cell_resolves_to_response_over_suggestion(db):
    schema, version, q = await _schema_with_question(db)
    record = await V2RecordFactory.create(version=version, reference="doc-2")
    await V2SuggestionFactory.create(record=record, question=q, value="flu")
    user = await UserFactory.create()
    await V2ResponseFactory.create(record=record, user=user, status=ResponseStatus.submitted,
                                   values={"dx": {"value": "covid"}})

    view = await projection_ctx.build_reference_view(
        db, workspace_id=schema.workspace_id, reference="doc-2", user=user)
    cell = view.records[0].cells[0]
    assert cell.value == "covid" and cell.source == "response"
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_projection.py -q`
Expected: FAIL — `projection` module missing.

- [ ] **Step 4: Implement the projection context**

Create `src/extralit_server/contexts/v2/projection.py`:

```python
"""Projection view (spec §17.4): resolve each reviewable cell as
submitted-response(requesting user) -> suggestion, grouped by reference. Query-time,
Postgres-only. A future OLAP materialization can replace this without changing the API."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v2.projection import ProjectionCell, ProjectionRecord, ProjectionView
from extralit_server.contexts.v2 import records as records_ctx
from extralit_server.enums import ResponseStatus
from extralit_server.models.v2 import V2Question, V2Response, V2Suggestion


async def build_reference_view(db: AsyncSession, *, workspace_id: UUID, reference: str, user) -> ProjectionView:
    records = await records_ctx.list_records_by_reference(db, workspace_id=workspace_id, reference=reference)
    if not records:
        return ProjectionView(reference=reference, records=[], total_records=0)

    schema_ids = {r.schema_id for r in records}
    record_ids = [r.id for r in records]

    questions_by_schema: dict[UUID, list[V2Question]] = {}
    q_rows = (await db.execute(select(V2Question).where(V2Question.schema_id.in_(schema_ids)))).scalars().all()
    for q in q_rows:
        questions_by_schema.setdefault(q.schema_id, []).append(q)

    # (record_id, question_id) -> suggestion value
    sugg_rows = (await db.execute(select(V2Suggestion).where(V2Suggestion.record_id.in_(record_ids)))).scalars().all()
    suggestions = {(s.record_id, s.question_id): s.value for s in sugg_rows}

    # requesting user's submitted responses only: record_id -> {question_name: value}
    resp_rows = (
        await db.execute(
            select(V2Response).where(
                V2Response.record_id.in_(record_ids),
                V2Response.user_id == user.id,
                V2Response.status == ResponseStatus.submitted,
            )
        )
    ).scalars().all()
    responses = {r.record_id: (r.values or {}) for r in resp_rows}

    projection_records: list[ProjectionRecord] = []
    for record in records:
        cells: list[ProjectionCell] = []
        for question in questions_by_schema.get(record.schema_id, []):
            wrapped = responses.get(record.id, {}).get(question.name)
            if wrapped is not None:
                cells.append(ProjectionCell(question_name=question.name, value=wrapped.get("value"), source="response"))
            elif (record.id, question.id) in suggestions:
                cells.append(ProjectionCell(question_name=question.name,
                                            value=suggestions[(record.id, question.id)], source="suggestion"))
            else:
                cells.append(ProjectionCell(question_name=question.name, value=None, source=None))
        projection_records.append(
            ProjectionRecord(record_id=record.id, schema_id=record.schema_id, reference=record.reference, cells=cells)
        )

    return ProjectionView(reference=reference, records=projection_records, total_records=len(records))
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_projection.py -q`
Expected: 2 passed.

- [ ] **Step 6: Add the projection route**

Create `src/extralit_server/api/v2/projection.py`:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import SchemaPolicy, authorize
from extralit_server.api.schemas.v2.projection import ProjectionView
from extralit_server.contexts.v2 import projection as projection_ctx
from extralit_server.database import get_async_db
from extralit_server.models import User
from extralit_server.security import auth

router = APIRouter(tags=["v2: projection"])


# Distinct `/projection/...` prefix, NOT `/references/{reference:path}/view`: the greedy `:path`
# converter on the existing GET /references/{reference:path} (Phase 3) would otherwise shadow a
# `/view` suffix, and a real reference ending in "/view" would collide. See spec §17.4.
@router.get("/projection/references/{reference:path}", response_model=ProjectionView)
async def get_reference_projection(
    *,
    reference: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID, Query(description="Workspace to scope the view (required)")],
):
    await authorize(current_user, SchemaPolicy.list(workspace_id))
    return await projection_ctx.build_reference_view(
        db, workspace_id=workspace_id, reference=reference, user=current_user
    )
```

Add `from extralit_server.api.v2 import projection as projection_v2` and `api_v2.include_router(projection_v2.router)` in `api/v2/__init__.py`. The `/projection/...` prefix does not overlap the Phase 3 `/references/{reference:path}` route, so include order is irrelevant.

- [ ] **Step 7: Write the projection API test**

Create `tests/integration/api/v2/test_projection.py`: owner GETs `/api/v2/projection/references/doc-1?workspace_id=<id>` after seeding a suggestion, asserts 200 + the resolved cell; and an unknown reference returns 200 with `total_records == 0`.

- [ ] **Step 8: Run the tests**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_projection.py tests/integration/contexts/v2/test_projection.py -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "feat(v2): projection view (resolve response->suggestion per cell)"
```

---

## Task 11: Full-suite verification + no-Lance-import guard

**Files:**
- Test: `tests/unit/test_annotation_no_index_import.py`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write a guard test that annotation never imports the index engine**

Create `tests/unit/test_annotation_no_index_import.py`:

```python
import ast
from pathlib import Path

import extralit_server

ROOT = Path(extralit_server.__file__).parent
GUARDED = [
    ROOT / "contexts" / "v2" / "annotation.py",
    ROOT / "contexts" / "v2" / "projection.py",
    ROOT / "api" / "v2" / "annotation.py",
    ROOT / "api" / "v2" / "questions.py",
]


def test_annotation_modules_do_not_import_index_engine():
    for path in GUARDED:
        tree = ast.parse(path.read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert not any("index" in m and "extralit_server" in m for m in imported), f"{path} imports the index engine"
        assert not any(m.endswith("index_sync") for m in imported), f"{path} imports index_sync"
```

- [ ] **Step 2: Run the guard test**

Run: `cd extralit-server && uv run pytest tests/unit/test_annotation_no_index_import.py -q`
Expected: PASS.

- [ ] **Step 3: Run the full v2 + validator suite**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2 tests/integration/contexts/v2 tests/integration/models/v2 tests/unit/validators/v2 tests/unit/test_annotation_no_index_import.py -q`
Expected: all pass. Fix any regressions before committing.

- [ ] **Step 4: Lint**

Run: `cd extralit-server && uv run ruff check src/extralit_server/api/v2 src/extralit_server/contexts/v2 src/extralit_server/validators/v2 src/extralit_server/models/v2 && uv run ruff format --check src/extralit_server/api/v2 src/extralit_server/contexts/v2 src/extralit_server/validators/v2 src/extralit_server/models/v2`
Expected: clean (run `uv run ruff format` to fix formatting if needed).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test(v2): guard annotation against index-engine imports; suite green"
```

---

## Self-Review Notes (for the executor)

- **Spec coverage:** §17.1 three tables → Tasks 2–3; §17.3 keyed responses → Task 8; span deferral → Tasks 4–5; no status transitions → Task 8 test; binding validation → Task 4; settings-level validation → Task 5; §17.4 projection view → Task 10; §17.5 endpoints + own-response authz + no-Lance-sync → Tasks 6–8, 10, 11; single-version read → Task 9; §14 drop `kind` → Task 1.
- **Out of scope (do NOT build):** field↔question unification / chain-of-steps, consensus/multi-annotator reconciliation, OLAP materialization, span anchoring, `record.status` distribution transitions (Phase 5).
- **Before each task:** verify helper names against the real files named in the task (`DatabaseModel.get`/`get_or_raise`/`delete`, the async client + auth-header fixture in `tests/integration/api/v2/test_schemas.py`, `SchemaVersionRead` in `api/schemas/v2/schemas.py`). The plan flags each spot where a name must be confirmed rather than assumed.
