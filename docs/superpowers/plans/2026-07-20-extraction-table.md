# Extraction Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a workspace-level denormalized extraction table — new `GET /api/v2/projection` endpoint with enriched provenance cells, a `/extractions` page rendered by Perspective 4.x, an additive `list[dict]` table-value contract, and deletion of the superseded reference-review page.

**Delivery: two phases, two PRs.**
- **Phase 1 (Tasks 1–7, PR 1):** everything additive and low-risk — server contract (validator extension, enriched cells, workspace endpoint) plus the frontend data layer (gen:api, domain types, repository, grid adapter, use-case, storage, DI). No UI, no deletions, no new dependencies. Mergeable to `develop` on its own; SDK #231 and any other consumer can build against the endpoint immediately.
- **Phase 2 (Tasks 8–13, PR 2, stacked on Phase 1):** the integration-risk half — Perspective deps/WASM/Vite wiring, the custom-element grid wrapper, the `/extractions` page, deletion of the reference-review page, and the e2e gate. If Perspective 4.5.2 fights back (WASM boot, init API drift, custom-element quirks), Phase 1 is already merged and unaffected.

**Architecture:** The server performs the full denormalization (coalesce `submitted response → suggestion → empty`, table fan-out, independent stacking, scalar repetition) in `contexts/v2/projection.py` using batched queries; the client only pages, aggregates, and renders. Frontend follows the existing v2 DDD chain: `ProjectionRepository` → `GetWorkspaceProjectionUseCase` → Pinia storage → `useExtractionsViewModel` → `pages/extractions/index.vue`, with a Perspective web-component grid wrapped in `ExtractionsGrid.vue`.

**Tech Stack:** FastAPI + SQLAlchemy async (extralit-server), Vue 3 / Nuxt 4 / Pinia / ts-injecty (extralit-frontend), Perspective `@perspective-dev/*` 4.5.2 (WASM), openapi-typescript contract gate, pytest / vitest / Playwright.

**Spec:** `docs/superpowers/specs/2026-07-20-extraction-table-design.md` (this plan implements §3–§4 within the §6 scope boundary; §5 items are explicitly NOT built).

## Global Constraints

- Branching: Phase 1 lands on `feat/v2-ui-extraction-table` (based on `develop` @ `52eab556f`) and PRs to `develop`. Phase 2 starts on a stacked branch `feat/v2-ui-extraction-grid` created from the Phase 1 branch (rebase onto `develop` once PR 1 merges; PR 2 targets `develop`). Commit per task, conventional-commit style (`feat(server): …`, `feat(v2-ui): …`, `test(…): …`).
- Python: **uv only** (`uv run pytest`, `uv add`); never pip/poetry. All server commands run from `extralit-server/`. All frontend commands run from `extralit-frontend/`.
- Perspective packages: `@perspective-dev/client`, `@perspective-dev/server`, `@perspective-dev/viewer`, `@perspective-dev/viewer-datagrid` — all pinned **4.5.2**. `@finos/*` is forbidden (frozen at 3.8.0).
- **Reuse-don't-fork** (spec §2): reuse `ProjectionRepository`, `useStoreFor` (v1 store factory), `useResolve`/ts-injecty DI, `InternalPage`/`AppHeader` layout, `e2e/v2/fixtures.ts`. v0's Tabulator `RenderTable` lineage is NOT reused. Kept for the future review drawer (do not delete): `widget-adapters.ts`, `widget-mapping.ts`, `SuggestionHint.ts`, `response-values.ts`, `ReviewCellInput.vue`, `ReviewProvenance.vue`, `submit-reference-review-use-case.ts`, `save-review-draft-use-case.ts`, `discard-review-use-case.ts` (each with tests).
- **gen:api drift gate:** any server contract change requires `npm run gen:api` from `extralit-frontend/` and committing BOTH `v2/infrastructure/api/openapi.json` and `v2/infrastructure/api/generated/v2-api.ts`. Repositories must type against `components["schemas"][…]` from the generated file.
- Frontend TS: `isolatedModules` — type-only imports MUST use the inline form `import { type X } from "…"`.
- Pinia store key = the state class's constructor name (`useStoreFor(Ctor)` → `defineStore(Ctor.name, …)`); the class name must be unique across ALL v1+v2 stores.
- Server integration tests need live services. On the Orin host: Postgres :5432, MinIO :9000, Elasticsearch :9200 already publish to localhost; Redis does NOT — start a throwaway one first: `docker run -d --rm --name tmp-redis -p 6379:6379 redis:7` (the autouse `empty_job_queues` fixture needs it even for non-queue tests).
- Frontend unit tests: `npx vitest run <path>` for a single file, `npm run test` for the suite. Typecheck: `npx nuxi typecheck`. Lint: `npm run lint`.

## File Structure

**extralit-server (modify):**
- `src/extralit_server/validators/v2/values.py` — `_validate_table` accepts `list[dict]` additively (Task 1)
- `src/extralit_server/api/schemas/v2/projection.py` — enrich `ProjectionCell`; add `WorkspaceProjection*` models (Tasks 2, 3)
- `src/extralit_server/contexts/v2/projection.py` — enrich `build_reference_view`; add `build_workspace_view` + pure denormalization helpers (Tasks 2, 3)
- `src/extralit_server/api/v2/projection.py` — add `GET /projection` route (Task 4)
- `tests/unit/validators/v2/test_values.py`, `tests/integration/contexts/v2/test_projection.py`, `tests/integration/api/v2/test_projection.py` — extend; new `tests/integration/contexts/v2/test_workspace_projection.py`

**extralit-frontend (create):**
- `v2/domain/entities/projection/WorkspaceProjection.ts` — domain types (columns/cells/rows/aggregate)
- `v2/domain/entities/projection/grid-adapter.ts` (+`.test.ts`) — pure: manifest→flat rows, band parity, cell lookup, annotation-URL contract + guard
- `v2/domain/usecases/get-workspace-projection-use-case.ts` (+`.test.ts`) — pages through endpoint, saves to storage
- `v2/infrastructure/storage/ExtractionsStorage.ts` — `useExtractions` Pinia store
- `components/v2/extractions/perspective-bootstrap.ts` — WASM init singleton (`__mocks__/perspective-bootstrap.js` stub)
- `components/v2/extractions/ExtractionsGrid.vue` (+`.test.ts`) — Perspective viewer wrapper: load, banding, click plumbing
- `pages/extractions/index.vue`, `pages/extractions/useExtractionsViewModel.ts` (+`.test.ts`) — the `/extractions` route
- `e2e/v2/extractions-grid.spec.ts` — replacement e2e gate

**extralit-frontend (modify):** `v2/infrastructure/repositories/ProjectionRepository.ts` (+test), `v2/di/di.ts`, `nuxt.config.ts`, `vitest.config.ts`, `package.json`, `translation/{en,de,es,ja}.js`, `composables/useV2Breadcrumbs.ts`, `components/v2/schemas/V2RecordsTable.vue` (+test), `e2e/v2/fixtures.ts`, `e2e/v2/seed/seed_v2_e2e.py`, new `v2/domain/entities/review/ReviewCell.ts` + import updates in kept review files.

**extralit-frontend (delete, Task 11):** `pages/references/[...reference].vue`, `pages/references/useReferenceReviewViewModel.ts` (+`.test.ts`), `components/v2/review/ProjectionReviewForm.vue` (+`.test.ts` if present), `components/v2/review/ReviewRecordCard.vue` (+test if present), `v2/domain/entities/review/ReferenceReview.ts`, `v2/domain/usecases/get-reference-review-use-case.ts` (+`.test.ts`), `v2/infrastructure/storage/ReferenceReviewsStorage.ts`, `e2e/v2/{review-loop,draft-lifecycle,slashed-reference}.spec.ts`.

---

## Phase 1 — Contract + data layer (PR 1: additive, no UI, no deletions)

Tasks 1–7. Server-side table-value extension, enriched provenance, the workspace projection endpoint, and the frontend chain up through DI registration (`ProjectionRepository.getWorkspaceProjection` → grid adapter → `GetWorkspaceProjectionUseCase` → `ExtractionsStorage`). Nothing here touches Perspective, pages, or existing UI — every change is additive and independently shippable.

### Task 1: Table-value `list[dict]` contract extension (server)

**Files:**
- Modify: `extralit-server/src/extralit_server/validators/v2/values.py` (`_validate_table`, lines ~48–57)
- Test: `extralit-server/tests/unit/validators/v2/test_values.py`

**Interfaces:**
- Consumes: existing `V2ResponseValueValidator.validate(value, *, type, settings, columns)` dispatch (unchanged).
- Produces: `_validate_table` accepting `dict` (1-row case, unchanged) OR `list[dict]` (N rows); every row's keys validated against the `columns` binding. Task 3's fan-out relies on both shapes being storable.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/validators/v2/test_values.py` (it already has `TABLE_SETTINGS = {"type": "table"}` and imports `V2ResponseValueValidator`, `QuestionType`, `UnprocessableEntityError`, `pytest`):

```python
def test_table_value_accepts_list_of_row_dicts():
    V2ResponseValueValidator.validate(
        [{"a": 1}, {"a": 2, "b": "x"}], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"]
    )


def test_table_value_accepts_empty_list():
    V2ResponseValueValidator.validate([], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a"])


def test_table_value_list_rejects_unbound_keys_in_any_row():
    with pytest.raises(UnprocessableEntityError, match="not bound"):
        V2ResponseValueValidator.validate(
            [{"a": 1}, {"z": 2}], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"]
        )


def test_table_value_list_rejects_non_dict_rows():
    with pytest.raises(UnprocessableEntityError, match="dict of values per row"):
        V2ResponseValueValidator.validate(
            [{"a": 1}, 5], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a"]
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extralit-server && uv run pytest tests/unit/validators/v2/test_values.py -v`
Expected: the 4 new tests FAIL (`list` currently raises "table question expects a dict"); existing tests PASS.

- [ ] **Step 3: Implement**

Replace `_validate_table` in `src/extralit_server/validators/v2/values.py`:

```python
    @staticmethod
    def _validate_table(value, columns: list[str]) -> None:
        # Additive contract (spec §3.4): a bare dict is the 1-row case; list[dict] is N rows.
        rows = value if isinstance(value, list) else [value]
        bound = set(columns)
        for row in rows:
            if not isinstance(row, dict):
                raise UnprocessableEntityError(
                    f"table question expects a dict of values per row, found {type(row)}"
                )
            extra = sorted(k for k in row if k not in bound)
            if extra:
                raise UnprocessableEntityError(
                    f"table value keys {extra!r} are not bound columns; bound: {sorted(bound)!r}"
                )
```

- [ ] **Step 4: Run the full validator test file**

Run: `cd extralit-server && uv run pytest tests/unit/validators/v2/test_values.py -v`
Expected: ALL PASS (the pre-existing `test_table_value_keys_must_be_subset_of_columns` matches `"not bound"` and still passes; the pre-existing non-dict error message changed from "expects a dict of values, found" to "…per row, found" — if any existing test matched the old wording, update its `match=` to `"dict of values per row"`).

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/validators/v2/values.py extralit-server/tests/unit/validators/v2/test_values.py
git commit -m "feat(server): accept list[dict] table values additively (spec §3.4)"
```

---

### Task 2: Enrich per-reference `ProjectionCell` with provenance (server)

**Files:**
- Modify: `extralit-server/src/extralit_server/api/schemas/v2/projection.py`
- Modify: `extralit-server/src/extralit_server/contexts/v2/projection.py` (`build_reference_view`)
- Test: `extralit-server/tests/integration/contexts/v2/test_projection.py`, `extralit-server/tests/integration/api/v2/test_projection.py`

**Interfaces:**
- Produces: `ProjectionCell` gains optional `record_id: UUID | None`, `agent: str | None`, `score: float | list[float] | None` — **additive**, so SDK #231 stays backward-compatible. Populated: response cells → `record_id`; suggestion cells → `record_id` + `agent` + `score`; empty cells → all `None`.

- [ ] **Step 1: Write the failing tests**

In `tests/integration/contexts/v2/test_projection.py`, extend the existing suggestion-cell test's assertions (find the test asserting `source == "suggestion"`) and add assertions to the response-precedence test. Add to the suggestion test (the factory default agent/score come from the explicit kwargs you pass — pass them):

```python
    # in the suggestion-cell test, create the suggestion with explicit provenance:
    await V2SuggestionFactory.create(record=record, question=q, value="flu", agent="gpt-x", score=0.92)
    ...
    assert cell.record_id == record.id
    assert cell.agent == "gpt-x"
    assert cell.score == 0.92
```

In the response-over-suggestion test add:

```python
    assert cell.record_id == record.id
    assert cell.agent is None and cell.score is None
```

In `tests/integration/api/v2/test_projection.py`, extend `test_projection_view_resolves_suggestion_cell`: pass `agent="e2e-agent", score=0.5` to `V2SuggestionFactory.create(...)` and assert on the JSON cell:

```python
    assert cell["record_id"] == str(record.id)
    assert cell["agent"] == "e2e-agent"
    assert cell["score"] == 0.5
```

- [ ] **Step 2: Run to verify failure**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_projection.py tests/integration/api/v2/test_projection.py -v`
Expected: FAIL — `ProjectionCell` has no attribute `record_id`. (Needs services up; see Global Constraints for the throwaway redis.)

- [ ] **Step 3: Implement**

`src/extralit_server/api/schemas/v2/projection.py` — extend `ProjectionCell`:

```python
class ProjectionCell(BaseModel):
    question_name: str
    value: Any | None = None
    source: Literal["response", "suggestion"] | None = None  # None => neither exists yet
    # Enriched provenance (spec §3.2): consumers link and attribute with zero extra calls.
    record_id: UUID | None = None
    agent: str | None = None
    score: float | list[float] | None = None
```

`src/extralit_server/contexts/v2/projection.py` — in `build_reference_view`, keep whole suggestion rows instead of just values, and populate the new fields. Change the suggestions dict comprehension:

```python
    suggestions = {(s.record_id, s.question_id): s for s in sugg_rows}
```

and the cell-building branches:

```python
            wrapped = responses.get(record.id, {}).get(question.name)
            if wrapped is not None:
                cells.append(
                    ProjectionCell(
                        question_name=question.name,
                        value=wrapped.get("value"),
                        source="response",
                        record_id=record.id,
                    )
                )
            elif (record.id, question.id) in suggestions:
                suggestion = suggestions[(record.id, question.id)]
                cells.append(
                    ProjectionCell(
                        question_name=question.name,
                        value=suggestion.value,
                        source="suggestion",
                        record_id=record.id,
                        agent=suggestion.agent,
                        score=suggestion.score,
                    )
                )
            else:
                cells.append(ProjectionCell(question_name=question.name, value=None, source=None))
```

- [ ] **Step 4: Run to verify pass**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_projection.py tests/integration/api/v2/test_projection.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/api/schemas/v2/projection.py extralit-server/src/extralit_server/contexts/v2/projection.py extralit-server/tests/integration/contexts/v2/test_projection.py extralit-server/tests/integration/api/v2/test_projection.py
git commit -m "feat(server): enrich ProjectionCell with record_id/agent/score provenance"
```

---

### Task 3: Workspace-level denormalized projection context (server)

**Files:**
- Modify: `extralit-server/src/extralit_server/api/schemas/v2/projection.py` (add 4 models)
- Modify: `extralit-server/src/extralit_server/contexts/v2/projection.py` (add `build_workspace_view` + helpers)
- Create: `extralit-server/tests/integration/contexts/v2/test_workspace_projection.py`

**Interfaces:**
- Consumes: `Schema`, `V2Question` (`.columns` binding, `.type`), `V2Record` (`.reference`), `V2Suggestion`, `V2Response` ORM models; `ResponseStatus`, `QuestionType` enums.
- Produces: `async def build_workspace_view(db: AsyncSession, *, workspace_id: UUID, offset: int, limit: int) -> WorkspaceProjection` — Task 4's route calls exactly this. Pydantic models `WorkspaceProjectionColumn`, `WorkspaceProjectionCell`, `WorkspaceProjectionRow`, `WorkspaceProjection` (names Task 4 and gen:api rely on).
- Semantics locked here: `limit`/`offset` count **references** (not fan-out rows); cell coalesce = **latest submitted response by any user** (by `updated_at`) `??` suggestion `??` omitted; one **effective record** per (reference, schema) = latest `inserted_at`; table fan-out with **independent stacking** (row count = max fan-out, min 1) and **scalar repetition**; absent cells omitted from `cells`.

- [ ] **Step 1: Add the Pydantic models**

Append to `src/extralit_server/api/schemas/v2/projection.py`:

```python
class WorkspaceProjectionColumn(BaseModel):
    name: str  # flat "Schema.question" / "Schema.question.subcol" (spec §3.1)
    schema_id: UUID
    schema_name: str
    question_name: str
    sub_column: str | None = None
    dtype: str  # the question type value; the grid treats it as informational


class WorkspaceProjectionCell(BaseModel):
    value: Any | None = None
    source: Literal["response", "suggestion"]
    record_id: UUID
    agent: str | None = None
    score: float | list[float] | None = None


class WorkspaceProjectionRow(BaseModel):
    reference: str
    row_index: int
    cells: dict[str, WorkspaceProjectionCell]  # keyed by column name; absent cells omitted


class WorkspaceProjection(BaseModel):
    columns: list[WorkspaceProjectionColumn]
    rows: list[WorkspaceProjectionRow]
    total_references: int
```

- [ ] **Step 2: Write the failing tests**

Create `tests/integration/contexts/v2/test_workspace_projection.py`:

```python
import pytest

from extralit_server.contexts.v2 import projection as projection_ctx
from extralit_server.enums import QuestionType, ResponseStatus

from tests.factories import (
    SchemaFactory,
    SchemaVersionFactory,
    UserFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2ResponseFactory,
    V2SuggestionFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.asyncio


async def _make_schema(workspace, name: str):
    schema = await SchemaFactory.create(workspace=workspace, name=name)
    version = await SchemaVersionFactory.create(schema=schema)
    return schema, version


async def _add_question(schema, name: str, *, qtype=QuestionType.text, columns=None):
    return await V2QuestionFactory.create(schema=schema, name=name, type=qtype, columns=columns or [name])


async def test_columns_manifest_covers_all_schemas_and_fans_out_table_bindings(db):
    workspace = await WorkspaceFactory.create()
    design, _ = await _make_schema(workspace, "Design")
    outcomes, _ = await _make_schema(workspace, "Outcomes")
    await _add_question(design, "type")
    await _add_question(outcomes, "results", qtype=QuestionType.table, columns=["value", "unit"])

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    names = [c.name for c in view.columns]
    assert names == ["Design.type", "Outcomes.results.value", "Outcomes.results.unit"]
    table_col = view.columns[1]
    assert table_col.schema_name == "Outcomes"
    assert table_col.question_name == "results"
    assert table_col.sub_column == "value"
    assert table_col.dtype == "table"


async def test_row_universe_is_union_of_references_with_coverage_gaps(db):
    workspace = await WorkspaceFactory.create()
    design, design_v = await _make_schema(workspace, "Design")
    outcomes, outcomes_v = await _make_schema(workspace, "Outcomes")
    dq = await _add_question(design, "type")
    await _add_question(outcomes, "summary")
    rec = await V2RecordFactory.create(version=design_v, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=dq, value="RCT")
    await V2RecordFactory.create(version=outcomes_v, reference="10.1/b")

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.total_references == 2
    assert [(r.reference, r.row_index) for r in view.rows] == [("10.1/a", 0), ("10.1/b", 0)]
    row_a, row_b = view.rows
    assert row_a.cells["Design.type"].value == "RCT"
    assert "Outcomes.summary" not in row_a.cells  # no Outcomes record: coverage gap, cell omitted
    assert row_b.cells == {}  # record exists but neither response nor suggestion


async def test_latest_submitted_response_any_user_beats_suggestion(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=q, value="cohort", agent="gpt-x", score=0.9)
    user1 = await UserFactory.create()
    user2 = await UserFactory.create()
    await V2ResponseFactory.create(
        record=rec, user=user1, values={"type": {"value": "RCT-old"}}, status=ResponseStatus.submitted
    )
    await V2ResponseFactory.create(
        record=rec, user=user2, values={"type": {"value": "RCT"}}, status=ResponseStatus.submitted
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cell = view.rows[0].cells["Design.type"]
    assert cell.value == "RCT"  # later updated_at wins across users
    assert cell.source == "response"
    assert cell.record_id == rec.id
    assert cell.agent is None and cell.score is None


async def test_draft_responses_never_appear(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=q, value="cohort", agent="gpt-x", score=0.9)
    user = await UserFactory.create()
    await V2ResponseFactory.create(
        record=rec, user=user, values={"type": {"value": "draft-val"}}, status=ResponseStatus.draft
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cell = view.rows[0].cells["Design.type"]
    assert cell.value == "cohort"
    assert cell.source == "suggestion"
    assert cell.agent == "gpt-x"
    assert cell.score == 0.9


async def test_table_fanout_independent_stacking_and_scalar_repetition(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Outcomes")
    scalar_q = await _add_question(schema, "design")
    t1 = await _add_question(schema, "results", qtype=QuestionType.table, columns=["value", "unit"])
    t2 = await _add_question(schema, "arms", qtype=QuestionType.table, columns=["arm"])
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=scalar_q, value="RCT")
    await V2SuggestionFactory.create(
        record=rec,
        question=t1,
        value=[{"value": "12%", "unit": "pct"}, {"value": "8%", "unit": "pct"}, {"value": "3%"}],
    )
    await V2SuggestionFactory.create(record=rec, question=t2, value=[{"arm": "control"}, {"arm": "treated"}])

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.total_references == 1
    assert len(view.rows) == 3  # max(3, 2), NOT 3*2 (no cartesian product)
    assert [r.row_index for r in view.rows] == [0, 1, 2]
    # scalars repeat on every fan-out row (true denormalized rows)
    assert all(r.cells["Outcomes.design"].value == "RCT" for r in view.rows)
    assert [r.cells["Outcomes.results.value"].value for r in view.rows] == ["12%", "8%", "3%"]
    # shorter table just ends (independent stacking): row 2 has no arms cell
    assert [r.cells.get("Outcomes.arms.arm") and r.cells["Outcomes.arms.arm"].value for r in view.rows] == [
        "control",
        "treated",
        None,
    ]
    # missing sub-key on a row dict is omitted
    assert "Outcomes.results.unit" not in view.rows[2].cells


async def test_single_dict_table_value_is_one_row(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Outcomes")
    t = await _add_question(schema, "results", qtype=QuestionType.table, columns=["value"])
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=t, value={"value": "12%"})

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 1
    assert view.rows[0].cells["Outcomes.results.value"].value == "12%"


async def test_effective_record_is_latest_inserted_per_reference_schema(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    old = await V2RecordFactory.create(version=version, reference="10.1/a")
    new = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=old, question=q, value="old")
    await V2SuggestionFactory.create(record=new, question=q, value="new")

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 1
    assert view.rows[0].cells["Design.type"].value == "new"
    assert view.rows[0].cells["Design.type"].record_id == new.id


async def test_pagination_counts_references_not_rows(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    await _add_question(schema, "type")
    for i in range(5):
        await V2RecordFactory.create(version=version, reference=f"10.1/{i}")

    page = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=2, limit=2)

    assert page.total_references == 5
    assert [r.reference for r in page.rows] == ["10.1/2", "10.1/3"]  # ordered by reference


async def test_query_count_is_constant_regardless_of_reference_count(db, monkeypatch):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    for i in range(6):
        rec = await V2RecordFactory.create(version=version, reference=f"10.1/{i}")
        await V2SuggestionFactory.create(record=rec, question=q, value=f"v{i}")

    executed: list[object] = []
    original_execute = db.execute

    async def counting_execute(*args, **kwargs):
        executed.append(args[0])
        return await original_execute(*args, **kwargs)

    monkeypatch.setattr(db, "execute", counting_execute)
    await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)
    # schemas, questions, ref-count, ref-page, records, suggestions, responses => 7 max
    assert len(executed) <= 7, f"N+1 regression: {len(executed)} statements"
```

Note: if `V2ResponseFactory`/`V2QuestionFactory` kwargs differ (check `tests/factories.py` lines ~655–764), adapt the factory calls — the factories use custom async `_create` that awaits SubFactory coroutines; passing explicit `record=`/`question=`/`user=`/`schema=`/`version=` instances is the established pattern in `tests/integration/contexts/v2/test_projection.py`.

- [ ] **Step 3: Run to verify failure**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_workspace_projection.py -v`
Expected: FAIL — `module … has no attribute 'build_workspace_view'`.

- [ ] **Step 4: Implement**

In `src/extralit_server/contexts/v2/projection.py`, extend the imports (keep existing ones):

```python
from sqlalchemy import func, select

from extralit_server.api.schemas.v2.projection import (
    ProjectionCell,
    ProjectionRecord,
    ProjectionView,
    WorkspaceProjection,
    WorkspaceProjectionCell,
    WorkspaceProjectionColumn,
    WorkspaceProjectionRow,
)
from extralit_server.enums import QuestionType, ResponseStatus
from extralit_server.models.v2 import Schema, V2Question, V2Record, V2Response, V2Suggestion
```

Append:

```python
def _build_columns(
    schemas: list[Schema], questions_by_schema: dict,
) -> list[WorkspaceProjectionColumn]:
    columns: list[WorkspaceProjectionColumn] = []
    for schema in schemas:
        for question in questions_by_schema.get(schema.id, []):
            if question.type == QuestionType.table:
                # sub-columns are the question's `columns` binding (spec §3.4)
                for sub in question.columns:
                    columns.append(
                        WorkspaceProjectionColumn(
                            name=f"{schema.name}.{question.name}.{sub}",
                            schema_id=schema.id,
                            schema_name=schema.name,
                            question_name=question.name,
                            sub_column=sub,
                            dtype=question.type.value,
                        )
                    )
            else:
                columns.append(
                    WorkspaceProjectionColumn(
                        name=f"{schema.name}.{question.name}",
                        schema_id=schema.id,
                        schema_name=schema.name,
                        question_name=question.name,
                        sub_column=None,
                        dtype=question.type.value,
                    )
                )
    return columns


def _resolve(record, question, suggestions, responses):
    """Coalesce (spec §3.1): latest submitted response (any user) ?? suggestion ?? None.
    Returns (value, source, agent, score) or None. Drafts never reach `responses`."""
    wrapped = responses.get(record.id, {}).get(question.name)
    if wrapped is not None:
        return (wrapped.get("value"), "response", None, None)
    suggestion = suggestions.get((record.id, question.id))
    if suggestion is not None:
        return (suggestion.value, "suggestion", suggestion.agent, suggestion.score)
    return None


def _table_rows(value) -> list[dict]:
    # §3.4 normalization: bare dict is the 1-row case; list[dict] is N rows.
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _denormalize_reference(
    reference: str,
    *,
    schemas: list[Schema],
    questions_by_schema: dict,
    effective: dict,
    suggestions: dict,
    responses: dict,
) -> list[WorkspaceProjectionRow]:
    scalar_cells: dict[str, WorkspaceProjectionCell] = {}
    table_values: list[tuple] = []  # (schema_name, question, rows, record, (source, agent, score))
    fan_out = 1
    for schema in schemas:
        record = effective.get((reference, schema.id))
        if record is None:
            continue  # coverage gap: this schema's columns stay empty for the reference
        for question in questions_by_schema.get(schema.id, []):
            resolved = _resolve(record, question, suggestions, responses)
            if resolved is None:
                continue  # absent cells are omitted; the client renders them as null
            value, source, agent, score = resolved
            if question.type == QuestionType.table:
                rows = _table_rows(value)
                if not rows:
                    continue
                fan_out = max(fan_out, len(rows))
                table_values.append((schema.name, question, rows, record, (source, agent, score)))
            elif value is not None:
                scalar_cells[f"{schema.name}.{question.name}"] = WorkspaceProjectionCell(
                    value=value, source=source, record_id=record.id, agent=agent, score=score
                )

    out: list[WorkspaceProjectionRow] = []
    for row_index in range(fan_out):
        cells = dict(scalar_cells)  # scalars repeat on every fan-out row (denormalized, §3.1)
        for schema_name, question, rows, record, (source, agent, score) in table_values:
            if row_index >= len(rows):
                continue  # independent stacking: shorter tables just end, no fabricated pairing
            for sub in question.columns:
                sub_value = rows[row_index].get(sub)
                if sub_value is None:
                    continue
                cells[f"{schema_name}.{question.name}.{sub}"] = WorkspaceProjectionCell(
                    value=sub_value, source=source, record_id=record.id, agent=agent, score=score
                )
        out.append(WorkspaceProjectionRow(reference=reference, row_index=row_index, cells=cells))
    return out


async def build_workspace_view(
    db: AsyncSession, *, workspace_id: UUID, offset: int, limit: int
) -> WorkspaceProjection:
    """Workspace-level denormalized projection (spec §3.2). Batched: a fixed number of
    queries regardless of reference/record count. `offset`/`limit` count references."""
    schemas = (
        (await db.execute(select(Schema).where(Schema.workspace_id == workspace_id).order_by(Schema.name)))
        .scalars()
        .all()
    )
    schema_ids = [s.id for s in schemas]

    questions_by_schema: dict[UUID, list[V2Question]] = {}
    if schema_ids:
        question_rows = (
            (
                await db.execute(
                    select(V2Question)
                    .where(V2Question.schema_id.in_(schema_ids))
                    .order_by(V2Question.inserted_at)
                )
            )
            .scalars()
            .all()
        )
        for question in question_rows:
            questions_by_schema.setdefault(question.schema_id, []).append(question)

    columns = _build_columns(schemas, questions_by_schema)

    if not schema_ids:
        return WorkspaceProjection(columns=columns, rows=[], total_references=0)

    # Row universe: every distinct reference across the workspace's records (§3.1).
    ref_query = select(V2Record.reference).where(V2Record.schema_id.in_(schema_ids)).distinct()
    total_references = (
        await db.execute(select(func.count()).select_from(ref_query.subquery()))
    ).scalar_one()
    references = (
        (await db.execute(ref_query.order_by(V2Record.reference).offset(offset).limit(limit)))
        .scalars()
        .all()
    )
    if not references:
        return WorkspaceProjection(columns=columns, rows=[], total_references=total_references)

    record_rows = (
        (
            await db.execute(
                select(V2Record)
                .where(V2Record.schema_id.in_(schema_ids), V2Record.reference.in_(references))
                .order_by(V2Record.inserted_at)
            )
        )
        .scalars()
        .all()
    )
    # One effective record per (reference, schema): latest inserted_at wins (§3.1).
    effective: dict[tuple[str, UUID], V2Record] = {}
    for record in record_rows:
        effective[(record.reference, record.schema_id)] = record
    record_ids = [r.id for r in effective.values()]

    suggestions: dict[tuple[UUID, UUID], V2Suggestion] = {}
    responses: dict[UUID, dict] = {}
    if record_ids:
        sugg_rows = (
            (await db.execute(select(V2Suggestion).where(V2Suggestion.record_id.in_(record_ids))))
            .scalars()
            .all()
        )
        suggestions = {(s.record_id, s.question_id): s for s in sugg_rows}
        # Latest submitted per record across ALL users — endpoint is user-agnostic and
        # cacheable (§3.1); ordering by updated_at lets the dict overwrite older entries.
        resp_rows = (
            (
                await db.execute(
                    select(V2Response)
                    .where(
                        V2Response.record_id.in_(record_ids),
                        V2Response.status == ResponseStatus.submitted,
                    )
                    .order_by(V2Response.updated_at)
                )
            )
            .scalars()
            .all()
        )
        for resp in resp_rows:
            responses[resp.record_id] = resp.values or {}

    rows: list[WorkspaceProjectionRow] = []
    for reference in references:
        rows.extend(
            _denormalize_reference(
                reference,
                schemas=schemas,
                questions_by_schema=questions_by_schema,
                effective=effective,
                suggestions=suggestions,
                responses=responses,
            )
        )
    return WorkspaceProjection(columns=columns, rows=rows, total_references=total_references)
```

Note: `build_reference_view`'s existing imports already cover most of this; merge rather than duplicate import lines. `AsyncSession`/`UUID` are already imported at the top of the module.

- [ ] **Step 5: Run to verify pass**

Run: `cd extralit-server && uv run pytest tests/integration/contexts/v2/test_workspace_projection.py tests/integration/contexts/v2/test_projection.py -v`
Expected: ALL PASS (including the ≤7-statement query-count guard).

- [ ] **Step 6: Commit**

```bash
git add extralit-server/src/extralit_server/api/schemas/v2/projection.py extralit-server/src/extralit_server/contexts/v2/projection.py extralit-server/tests/integration/contexts/v2/test_workspace_projection.py
git commit -m "feat(server): workspace-level denormalized projection with table fan-out"
```

---

### Task 4: `GET /api/v2/projection` route (server)

**Files:**
- Modify: `extralit-server/src/extralit_server/api/v2/projection.py`
- Test: `extralit-server/tests/integration/api/v2/test_projection.py`

**Interfaces:**
- Consumes: `build_workspace_view` (Task 3), existing `auth`/`authorize`/`SchemaPolicy.list` pattern.
- Produces: `GET /api/v2/projection?workspace_id=…&offset=0&limit=50` → `WorkspaceProjection` JSON (`columns`, `rows`, `total_references`). `limit` ∈ [1, 100], default 50. This is the contract the frontend types against after gen:api.

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/api/v2/test_projection.py` (reuse its existing `_schema_with_question` helper and imports; add `V2ResponseFactory`, `UserFactory` imports if not present):

```python
async def test_workspace_projection_returns_manifest_rows_and_total(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    schema, version, q = await _schema_with_question(workspace)
    record = await V2RecordFactory.create(version=version, reference="doc-1")
    await V2SuggestionFactory.create(record=record, question=q, value="flu", agent="gpt-x", score=0.92)

    resp = await async_client.get(
        f"/api/v2/projection?workspace_id={workspace.id}", headers=owner_auth_header
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_references"] == 1
    [column] = [c for c in body["columns"] if c["question_name"] == q.name]
    assert column["schema_id"] == str(schema.id)
    assert column["sub_column"] is None
    [row] = body["rows"]
    assert row["reference"] == "doc-1"
    assert row["row_index"] == 0
    cell = row["cells"][column["name"]]
    assert cell == {
        "value": "flu",
        "source": "suggestion",
        "record_id": str(record.id),
        "agent": "gpt-x",
        "score": 0.92,
    }


async def test_workspace_projection_paginates_references(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    schema, version, q = await _schema_with_question(workspace)
    for i in range(3):
        await V2RecordFactory.create(version=version, reference=f"doc-{i}")

    resp = await async_client.get(
        f"/api/v2/projection?workspace_id={workspace.id}&offset=1&limit=1", headers=owner_auth_header
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_references"] == 3
    assert [r["reference"] for r in body["rows"]] == ["doc-1"]


async def test_workspace_projection_rejects_limit_over_100(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    resp = await async_client.get(
        f"/api/v2/projection?workspace_id={workspace.id}&limit=101", headers=owner_auth_header
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to verify failure**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_projection.py -v`
Expected: new tests FAIL with 404 (route absent); Task 2's tests still PASS.

- [ ] **Step 3: Implement**

In `src/extralit_server/api/v2/projection.py`, import `WorkspaceProjection` alongside `ProjectionView`, and add ABOVE the existing per-reference route (order is not load-bearing — the paths don't overlap — but keeps the file readable):

```python
@router.get("/projection", response_model=WorkspaceProjection)
async def get_workspace_projection(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID, Query(description="Workspace to scope the view (required)")],
    offset: Annotated[int, Query(ge=0, description="Reference offset (not fan-out rows)")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="References per page")] = 50,
):
    await authorize(current_user, SchemaPolicy.list(workspace_id))
    return await projection_ctx.build_workspace_view(
        db, workspace_id=workspace_id, offset=offset, limit=limit
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd extralit-server && uv run pytest tests/integration/api/v2/test_projection.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add extralit-server/src/extralit_server/api/v2/projection.py extralit-server/tests/integration/api/v2/test_projection.py
git commit -m "feat(server): GET /api/v2/projection workspace endpoint"
```

---

### Task 5: gen:api + domain types + `ProjectionRepository.getWorkspaceProjection` (frontend)

**Files:**
- Create: `extralit-frontend/v2/domain/entities/projection/WorkspaceProjection.ts`
- Modify: `extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.ts`
- Modify (generated): `extralit-frontend/v2/infrastructure/api/openapi.json`, `extralit-frontend/v2/infrastructure/api/generated/v2-api.ts`
- Test: `extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.test.ts`

**Interfaces:**
- Consumes: generated `components["schemas"]["WorkspaceProjection"]` from Task 4's contract.
- Produces (used by Tasks 6–10):
  - `ProjectionColumn { name; schemaId; schemaName; questionName; subColumn: string | null; dtype: string }`
  - `ProjectionGridCell { value: unknown; source: "response" | "suggestion"; recordId: string; agent: string | null; score: number | number[] | null }`
  - `ProjectionGridRow { reference: string; rowIndex: number; cells: Record<string, ProjectionGridCell> }`
  - `class WorkspaceProjection { columns: ProjectionColumn[]; rows: ProjectionGridRow[]; totalReferences: number }`
  - `ProjectionRepository.getWorkspaceProjection(workspaceId: string, offset?: number, limit?: number): Promise<WorkspaceProjectionPageDto>` where `WorkspaceProjectionPageDto { columns: ProjectionColumn[]; rows: ProjectionGridRow[]; totalReferences: number }`

- [ ] **Step 1: Regenerate the API contract**

```bash
cd extralit-frontend && npm run gen:api
git diff --stat v2/infrastructure/api
```
Expected: both `openapi.json` and `generated/v2-api.ts` change; `v2-api.ts` gains `WorkspaceProjection`, `WorkspaceProjectionColumn`, `WorkspaceProjectionCell`, `WorkspaceProjectionRow` schemas plus `record_id`/`agent`/`score` on `ProjectionCell`.

- [ ] **Step 2: Create the domain types**

Create `v2/domain/entities/projection/WorkspaceProjection.ts`:

```ts
export interface ProjectionColumn {
  name: string; // flat "Schema.question" / "Schema.question.subcol"
  schemaId: string;
  schemaName: string;
  questionName: string;
  subColumn: string | null;
  dtype: string;
}

export interface ProjectionGridCell {
  value: unknown;
  source: "response" | "suggestion";
  recordId: string;
  agent: string | null;
  score: number | number[] | null;
}

export interface ProjectionGridRow {
  reference: string;
  rowIndex: number;
  cells: Record<string, ProjectionGridCell>;
}

export class WorkspaceProjection {
  constructor(
    public readonly columns: ProjectionColumn[],
    public readonly rows: ProjectionGridRow[],
    public readonly totalReferences: number
  ) {}
}
```

- [ ] **Step 3: Write the failing repository test**

Append to `v2/infrastructure/repositories/ProjectionRepository.test.ts` (keep the existing per-reference test untouched):

```ts
const BACKEND_WORKSPACE = {
  columns: [
    {
      name: "Design.type",
      schema_id: "s-1",
      schema_name: "Design",
      question_name: "type",
      sub_column: null,
      dtype: "text",
    },
  ],
  rows: [
    {
      reference: "10.1000/j.x",
      row_index: 0,
      cells: {
        "Design.type": { value: "RCT", source: "response", record_id: "r-1", agent: null, score: null },
      },
    },
  ],
  total_references: 213,
};

describe("getWorkspaceProjection", () => {
  it("pages the workspace projection and maps snake_case to the domain shape", async () => {
    const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
    const page = await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1", 50, 25);

    expect(axios.get).toHaveBeenCalledWith("/v2/projection", {
      params: { workspace_id: "w-1", offset: 50, limit: 25 },
    });
    expect(page.totalReferences).toBe(213);
    expect(page.columns[0]).toEqual({
      name: "Design.type",
      schemaId: "s-1",
      schemaName: "Design",
      questionName: "type",
      subColumn: null,
      dtype: "text",
    });
    expect(page.rows[0].reference).toBe("10.1000/j.x");
    expect(page.rows[0].rowIndex).toBe(0);
    expect(page.rows[0].cells["Design.type"]).toEqual({
      value: "RCT",
      source: "response",
      recordId: "r-1",
      agent: null,
      score: null,
    });
  });

  it("defaults to offset 0, limit 50", async () => {
    const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
    await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1");
    expect(axios.get).toHaveBeenCalledWith("/v2/projection", {
      params: { workspace_id: "w-1", offset: 0, limit: 50 },
    });
  });
});
```

- [ ] **Step 4: Run to verify failure**

Run: `cd extralit-frontend && npx vitest run v2/infrastructure/repositories/ProjectionRepository.test.ts`
Expected: FAIL — `getWorkspaceProjection is not a function`.

- [ ] **Step 5: Implement the repository method**

In `v2/infrastructure/repositories/ProjectionRepository.ts` add (keeping the existing `getProjection` untouched):

```ts
import {
  type ProjectionColumn,
  type ProjectionGridCell,
  type ProjectionGridRow,
} from "~/v2/domain/entities/projection/WorkspaceProjection";

type BackendWorkspaceProjection = components["schemas"]["WorkspaceProjection"];

export interface WorkspaceProjectionPageDto {
  columns: ProjectionColumn[];
  rows: ProjectionGridRow[];
  totalReferences: number;
}
```

and inside the class:

```ts
  async getWorkspaceProjection(
    workspaceId: string,
    offset = 0,
    limit = 50
  ): Promise<WorkspaceProjectionPageDto> {
    const { data } = await this.axios.get<BackendWorkspaceProjection>("/v2/projection", {
      params: { workspace_id: workspaceId, offset, limit },
    });
    return {
      totalReferences: data.total_references,
      columns: data.columns.map((c) => ({
        name: c.name,
        schemaId: c.schema_id,
        schemaName: c.schema_name,
        questionName: c.question_name,
        subColumn: c.sub_column ?? null,
        dtype: c.dtype,
      })),
      rows: data.rows.map((r) => ({
        reference: r.reference,
        rowIndex: r.row_index,
        cells: Object.fromEntries(
          Object.entries(r.cells).map(([name, cell]) => [
            name,
            {
              value: cell.value ?? null,
              source: cell.source,
              recordId: cell.record_id,
              agent: cell.agent ?? null,
              score: cell.score ?? null,
            } satisfies ProjectionGridCell,
          ])
        ),
      })),
    };
  }
```

- [ ] **Step 6: Run to verify pass**

Run: `cd extralit-frontend && npx vitest run v2/infrastructure/repositories/ProjectionRepository.test.ts`
Expected: ALL PASS (old + new).

- [ ] **Step 7: Commit**

```bash
git add extralit-frontend/v2/infrastructure/api extralit-frontend/v2/domain/entities/projection/WorkspaceProjection.ts extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.ts extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.test.ts
git commit -m "feat(v2-ui): workspace projection contract, domain types, repository method"
```

---

### Task 6: Grid adapter — pure denormalized-rows → Perspective mapping (frontend)

**Files:**
- Create: `extralit-frontend/v2/domain/entities/projection/grid-adapter.ts`
- Test: `extralit-frontend/v2/domain/entities/projection/grid-adapter.test.ts`

**Interfaces:**
- Consumes: `WorkspaceProjection`, `ProjectionGridCell` (Task 5).
- Produces (used by Tasks 9–10):
  - `REFERENCE_COLUMN = "reference"`
  - `toPerspectiveData(projection: WorkspaceProjection): Record<string, unknown>[]` — one flat object per row, EVERY manifest column present (`null` when absent) so the inferred Perspective schema is stable
  - `cellAt(projection: WorkspaceProjection, rowIndex: number, columnName: string): ProjectionGridCell | null`
  - `bandParity(projection: WorkspaceProjection): number[]` — 0/1 per row, flips when `reference` changes
  - `ANNOTATION_CELL_LINKS_ENABLED = false` (spec §3.3 guard)
  - `buildAnnotationUrl(schemaId: string, reference: string): string` → `/dataset/{schemaId}/annotation-mode?_search={encoded reference}`

- [ ] **Step 1: Write the failing tests**

Create `v2/domain/entities/projection/grid-adapter.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  ANNOTATION_CELL_LINKS_ENABLED,
  bandParity,
  buildAnnotationUrl,
  cellAt,
  REFERENCE_COLUMN,
  toPerspectiveData,
} from "./grid-adapter";
import { WorkspaceProjection, type ProjectionGridCell } from "./WorkspaceProjection";

const cell = (value: unknown): ProjectionGridCell => ({
  value,
  source: "suggestion",
  recordId: "r-1",
  agent: "gpt-x",
  score: 0.9,
});

const COLUMNS = [
  { name: "Design.type", schemaId: "s-1", schemaName: "Design", questionName: "type", subColumn: null, dtype: "text" },
  {
    name: "Outcomes.results.value",
    schemaId: "s-2",
    schemaName: "Outcomes",
    questionName: "results",
    subColumn: "value",
    dtype: "table",
  },
];

const PROJECTION = new WorkspaceProjection(
  COLUMNS,
  [
    { reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell("RCT") } },
    { reference: "10.1/a", rowIndex: 1, cells: { "Outcomes.results.value": cell("12%") } },
    { reference: "10.1/b", rowIndex: 0, cells: {} },
  ],
  2
);

describe("toPerspectiveData", () => {
  it("emits one flat record per row with every manifest column (null when absent)", () => {
    expect(toPerspectiveData(PROJECTION)).toEqual([
      { [REFERENCE_COLUMN]: "10.1/a", "Design.type": "RCT", "Outcomes.results.value": null },
      { [REFERENCE_COLUMN]: "10.1/a", "Design.type": null, "Outcomes.results.value": "12%" },
      { [REFERENCE_COLUMN]: "10.1/b", "Design.type": null, "Outcomes.results.value": null },
    ]);
  });
});

describe("cellAt", () => {
  it("returns the enriched cell for the loaded row order", () => {
    expect(cellAt(PROJECTION, 0, "Design.type")?.recordId).toBe("r-1");
  });

  it("returns null for empty cells and out-of-range rows", () => {
    expect(cellAt(PROJECTION, 2, "Design.type")).toBeNull();
    expect(cellAt(PROJECTION, 99, "Design.type")).toBeNull();
  });
});

describe("bandParity", () => {
  it("flips parity when the reference changes, not per row", () => {
    expect(bandParity(PROJECTION)).toEqual([0, 0, 1]);
  });
});

describe("annotation URL contract (spec §3.3)", () => {
  it("stays guarded off in this build", () => {
    expect(ANNOTATION_CELL_LINKS_ENABLED).toBe(false);
  });

  it("puts the schema id in the dataset slot and encodes the reference", () => {
    expect(buildAnnotationUrl("s-1", "10.1/a b")).toBe("/dataset/s-1/annotation-mode?_search=10.1%2Fa%20b");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd extralit-frontend && npx vitest run v2/domain/entities/projection/grid-adapter.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `v2/domain/entities/projection/grid-adapter.ts`:

```ts
import { type ProjectionGridCell, type WorkspaceProjection } from "./WorkspaceProjection";

export const REFERENCE_COLUMN = "reference";

// Flat denormalized records for `client.table(data)`. Every manifest column is present
// on every row (null when absent) so Perspective infers a stable schema.
export const toPerspectiveData = (projection: WorkspaceProjection): Record<string, unknown>[] =>
  projection.rows.map((row) => {
    const flat: Record<string, unknown> = { [REFERENCE_COLUMN]: row.reference };
    for (const column of projection.columns) {
      flat[column.name] = row.cells[column.name]?.value ?? null;
    }
    return flat;
  });

// Click plumbing (spec §3.3): rows load in projection order and the grid is static
// (no sort/filter), so a datagrid row index maps 1:1 onto projection.rows.
export const cellAt = (
  projection: WorkspaceProjection,
  rowIndex: number,
  columnName: string
): ProjectionGridCell | null => projection.rows[rowIndex]?.cells[columnName] ?? null;

// Row-banding by reference (spec §3.1) — Perspective is flat-columnar and cannot merge
// cells, so visual grouping is alternating bands per reference block.
export const bandParity = (projection: WorkspaceProjection): number[] => {
  let parity = 0;
  let previous: string | null = null;
  return projection.rows.map((row) => {
    if (previous !== null && row.reference !== previous) parity ^= 1;
    previous = row.reference;
    return parity;
  });
};

// Future annotation URL contract (spec §3.3): schema id occupies the dataset slot.
// Guarded OFF until annotation-mode resolves v2 schema ids (ledger §5).
export const ANNOTATION_CELL_LINKS_ENABLED = false;

export const buildAnnotationUrl = (schemaId: string, reference: string): string =>
  `/dataset/${schemaId}/annotation-mode?_search=${encodeURIComponent(reference)}`;
```

- [ ] **Step 4: Run to verify pass**

Run: `cd extralit-frontend && npx vitest run v2/domain/entities/projection/grid-adapter.test.ts`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add extralit-frontend/v2/domain/entities/projection/grid-adapter.ts extralit-frontend/v2/domain/entities/projection/grid-adapter.test.ts
git commit -m "feat(v2-ui): pure grid adapter — flat rows, banding, click-URL contract"
```

---

### Task 7: `GetWorkspaceProjectionUseCase` + `ExtractionsStorage` + DI (frontend)

**Files:**
- Create: `extralit-frontend/v2/infrastructure/storage/ExtractionsStorage.ts`
- Create: `extralit-frontend/v2/domain/usecases/get-workspace-projection-use-case.ts`
- Modify: `extralit-frontend/v2/di/di.ts`
- Test: `extralit-frontend/v2/domain/usecases/get-workspace-projection-use-case.test.ts`

**Interfaces:**
- Consumes: `ProjectionRepository.getWorkspaceProjection` (Task 5), `useStoreFor` from `@/v1/store/create`.
- Produces: `GetWorkspaceProjectionUseCase.execute(workspaceId: string): Promise<WorkspaceProjection>` (pages through ALL references at `PROJECTION_PAGE_SIZE = 100` per call, aggregates rows into ONE `WorkspaceProjection`, saves to storage); `useExtractions()` store with `saveProjection(projection)` and `get(): Extractions` where `Extractions.projection: WorkspaceProjection | null`. Task 10's view-model resolves the use-case via `useResolve`.

- [ ] **Step 1: Create the storage**

Create `v2/infrastructure/storage/ExtractionsStorage.ts`:

```ts
import { useStoreFor } from "@/v1/store/create";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

// Class name is the Pinia store key — must stay unique vs every v1/v2 useStoreFor class.
class Extractions {
  constructor(public readonly projection: WorkspaceProjection | null = null) {}
}

interface IExtractionsStorage {
  saveProjection(projection: WorkspaceProjection): void;
}

const useStoreForExtractions = useStoreFor<Extractions, IExtractionsStorage>(Extractions);

export const useExtractions = () => {
  const store = useStoreForExtractions();

  const saveProjection = (projection: WorkspaceProjection) => {
    store.save(new Extractions(projection));
  };

  return { ...store, saveProjection };
};
```

- [ ] **Step 2: Write the failing use-case test**

Create `v2/domain/usecases/get-workspace-projection-use-case.test.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GetWorkspaceProjectionUseCase, PROJECTION_PAGE_SIZE } from "./get-workspace-projection-use-case";
import { useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";

const COLUMN = {
  name: "Design.type",
  schemaId: "s-1",
  schemaName: "Design",
  questionName: "type",
  subColumn: null,
  dtype: "text",
};

const row = (reference: string) => ({ reference, rowIndex: 0, cells: {} });

describe("GetWorkspaceProjectionUseCase", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads every page into one projection and saves it to storage", async () => {
    const repository = {
      getWorkspaceProjection: vi
        .fn()
        .mockResolvedValueOnce({ columns: [COLUMN], rows: [row("10.1/a")], totalReferences: 150 })
        .mockResolvedValueOnce({ columns: [COLUMN], rows: [row("10.1/b")], totalReferences: 150 }),
    };
    const useCase = new GetWorkspaceProjectionUseCase(repository as never, useExtractions());

    const projection = await useCase.execute("w-1");

    expect(repository.getWorkspaceProjection).toHaveBeenNthCalledWith(1, "w-1", 0, PROJECTION_PAGE_SIZE);
    expect(repository.getWorkspaceProjection).toHaveBeenNthCalledWith(2, "w-1", 100, PROJECTION_PAGE_SIZE);
    expect(repository.getWorkspaceProjection).toHaveBeenCalledTimes(2);
    expect(projection.rows.map((r) => r.reference)).toEqual(["10.1/a", "10.1/b"]);
    expect(projection.totalReferences).toBe(150);
    expect(useExtractions().get().projection).toEqual(projection);
  });

  it("makes a single call when everything fits in one page", async () => {
    const repository = {
      getWorkspaceProjection: vi
        .fn()
        .mockResolvedValue({ columns: [COLUMN], rows: [row("10.1/a")], totalReferences: 1 }),
    };
    const useCase = new GetWorkspaceProjectionUseCase(repository as never, useExtractions());
    await useCase.execute("w-1");
    expect(repository.getWorkspaceProjection).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd extralit-frontend && npx vitest run v2/domain/usecases/get-workspace-projection-use-case.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the use-case**

Create `v2/domain/usecases/get-workspace-projection-use-case.ts`:

```ts
import { WorkspaceProjection } from "../entities/projection/WorkspaceProjection";
import { ProjectionRepository } from "~/v2/infrastructure/repositories/ProjectionRepository";
import { type useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";

// Server caps limit at 100; the client loads all pages into ONE Perspective table
// (spec §3.3 data path — Arrow IPC streaming is a recorded follow-up, §5).
export const PROJECTION_PAGE_SIZE = 100;

export class GetWorkspaceProjectionUseCase {
  constructor(
    private readonly projectionRepository: ProjectionRepository,
    // ts-injecty resolves the hook by calling it; the injected value is the store object.
    private readonly extractionsStorage: ReturnType<typeof useExtractions>
  ) {}

  async execute(workspaceId: string): Promise<WorkspaceProjection> {
    const first = await this.projectionRepository.getWorkspaceProjection(
      workspaceId,
      0,
      PROJECTION_PAGE_SIZE
    );
    const rows = [...first.rows];
    for (let offset = PROJECTION_PAGE_SIZE; offset < first.totalReferences; offset += PROJECTION_PAGE_SIZE) {
      const page = await this.projectionRepository.getWorkspaceProjection(
        workspaceId,
        offset,
        PROJECTION_PAGE_SIZE
      );
      rows.push(...page.rows);
    }
    const projection = new WorkspaceProjection(first.columns, rows, first.totalReferences);
    this.extractionsStorage.saveProjection(projection);
    return projection;
  }
}
```

- [ ] **Step 5: Run to verify pass**

Run: `cd extralit-frontend && npx vitest run v2/domain/usecases/get-workspace-projection-use-case.test.ts`
Expected: ALL PASS.

- [ ] **Step 6: Register in DI**

In `v2/di/di.ts` add the imports:

```ts
import { GetWorkspaceProjectionUseCase } from "~/v2/domain/usecases/get-workspace-projection-use-case";
import { useExtractions } from "~/v2/infrastructure/storage/ExtractionsStorage";
```

and, in the `dependencies` array right after the existing `register(ProjectionRepository)…` line:

```ts
    register(GetWorkspaceProjectionUseCase).withDependencies(ProjectionRepository, useExtractions).build(),
```

- [ ] **Step 7: Verify the suite still passes and commit**

Run: `cd extralit-frontend && npm run test`
Expected: ALL PASS.

```bash
git add extralit-frontend/v2/infrastructure/storage/ExtractionsStorage.ts extralit-frontend/v2/domain/usecases/get-workspace-projection-use-case.ts extralit-frontend/v2/domain/usecases/get-workspace-projection-use-case.test.ts extralit-frontend/v2/di/di.ts
git commit -m "feat(v2-ui): workspace-projection use-case, extractions storage, DI wiring"
```

---

### Phase 1 exit gate — verify and open PR 1

- [ ] **Step 1: Server suites**

```bash
docker run -d --rm --name tmp-redis -p 6379:6379 redis:7   # if not already running
cd extralit-server && uv run pytest tests/unit/validators/v2 tests/integration/contexts/v2 tests/integration/api/v2 -q
```
Expected: ALL PASS.

- [ ] **Step 2: Contract drift gate**

```bash
cd extralit-frontend && npm run gen:api && git diff --exit-code v2/infrastructure/api
```
Expected: exit 0 — the snapshot committed in Task 5 matches the server.

- [ ] **Step 3: Frontend gates**

```bash
cd extralit-frontend && npm run test && npx nuxi typecheck && npm run lint
```
Expected: all green. (No `npm run build` needed yet — no new build-affecting config in this phase.)

- [ ] **Step 4: Scope audit**

Confirm Phase 1 is purely additive: no `package.json` dependency changes, no `nuxt.config.ts`/`vitest.config.ts` changes, no page/component/e2e changes, no deletions. Existing v2 e2e specs (`review-loop`, `draft-lifecycle`, `slashed-reference`, `auth-smoke`, `search-roundtrip`) are untouched and still the active gate.

- [ ] **Step 5: Open PR 1**

Use superpowers:finishing-a-development-branch — PR from `feat/v2-ui-extraction-table` to `develop`: "feat(v2): workspace projection endpoint + extraction-table data layer". Then branch Phase 2:

```bash
git checkout -b feat/v2-ui-extraction-grid
```

---

## Phase 2 — Perspective grid + page + review-page retirement (PR 2, stacked on Phase 1)

Tasks 8–13, on `feat/v2-ui-extraction-grid`. This phase carries the integration risk this split exists to isolate: the `@perspective-dev/*` 4.5.2 WASM boot, Vite/esbuild config, the `<perspective-viewer>` custom element under Vue, and the regular-table styling/click hooks — plus the destructive change (review-page deletion) and its replacement e2e gate. Task 12's e2e spec is the acceptance gate for the whole Perspective wiring; if 4.5.2 fights back, nothing in the merged Phase 1 needs to move.

### Task 8: Perspective dependencies, Nuxt/Vite config, WASM bootstrap + test stub (frontend)

**Files:**
- Modify: `extralit-frontend/package.json` (+ lockfile)
- Modify: `extralit-frontend/nuxt.config.ts`
- Modify: `extralit-frontend/vitest.config.ts`
- Create: `extralit-frontend/components/v2/extractions/perspective-bootstrap.ts`
- Create: `extralit-frontend/__mocks__/perspective-bootstrap.js`

**Interfaces:**
- Produces: `initPerspective(): Promise<PerspectiveModule>` — module-level singleton; resolves once WASM is initialized and returns the `@perspective-dev/client` default export (so callers do `const perspective = await initPerspective(); const client = await perspective.worker();`). Task 9 imports it via the alias-stable specifier `~/components/v2/extractions/perspective-bootstrap`.
- The vitest stub replaces the whole bootstrap module, so unit tests never touch WASM/custom elements (mirrors the `tabulator-tables` mock precedent).

- [ ] **Step 1: Install pinned packages**

```bash
cd extralit-frontend && npm install --save-exact @perspective-dev/client@4.5.2 @perspective-dev/server@4.5.2 @perspective-dev/viewer@4.5.2 @perspective-dev/viewer-datagrid@4.5.2
```

- [ ] **Step 2: Verify the WASM asset paths** (verified against the 4.5.2 tarballs on 2026-07-20, but confirm locally)

```bash
ls node_modules/@perspective-dev/server/dist/wasm/perspective-server.wasm node_modules/@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm
```
Expected: both files listed. If a path differs, use the actual path in Step 4's `?url` imports.

- [ ] **Step 3: Nuxt/Vite config**

In `nuxt.config.ts` add a top-level `vue` key (there is none today) and extend the existing `vite` block (currently ~lines 88–107; keep the existing `plugins`, `server`, `css`, and `optimizeDeps.include` entries):

```ts
  vue: {
    compilerOptions: {
      // <perspective-viewer> is a web Custom Element, not a Vue component (spec §3.3).
      isCustomElement: (tag: string) => tag.startsWith("perspective-"),
    },
  },
```

```ts
  vite: {
    // …existing entries stay…
    build: {
      target: "esnext", // Perspective 4.x ESM/WASM requirement
    },
    optimizeDeps: {
      include: [/* …existing entries stay… */],
      // WASM ESM packages break under esbuild pre-bundling; load them as-is.
      exclude: [
        "@perspective-dev/client",
        "@perspective-dev/server",
        "@perspective-dev/viewer",
        "@perspective-dev/viewer-datagrid",
      ],
      esbuildOptions: {
        target: "esnext",
      },
    },
  },
```

- [ ] **Step 4: Create the bootstrap module**

Create `components/v2/extractions/perspective-bootstrap.ts`:

```ts
import perspective from "@perspective-dev/client";
import perspective_viewer from "@perspective-dev/viewer";
import "@perspective-dev/viewer-datagrid";
import SERVER_WASM from "@perspective-dev/server/dist/wasm/perspective-server.wasm?url";
import CLIENT_WASM from "@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm?url";

// SPA (ssr: false): this runs client-side only. Module-level guard so the WASM
// engines initialize exactly once no matter how often the page remounts (spec §3.3).
let ready: Promise<typeof perspective> | null = null;

export const initPerspective = () => {
  ready ??= Promise.all([
    perspective.init_server(fetch(SERVER_WASM)),
    perspective_viewer.init_client(fetch(CLIENT_WASM)),
  ]).then(() => perspective);
  return ready;
};
```

If TypeScript rejects the `?url` imports, add a declaration file `types/wasm-url.d.ts`:

```ts
declare module "*.wasm?url" {
  const url: string;
  export default url;
}
```

If `init_server`/`init_client` names differ in 4.5.2, check `node_modules/@perspective-dev/client/dist/esm/perspective.d.ts` and `node_modules/@perspective-dev/viewer/dist/esm/perspective-viewer.d.ts` for the actual exported init functions and use those — the shape above matches <https://perspective-dev.github.io/guide/how_to/javascript/importing.html>.

- [ ] **Step 5: Create the vitest stub and alias it**

Create `__mocks__/perspective-bootstrap.js`:

```js
// Perspective touches WASM + custom elements at import time; specs use this stub
// (same rationale as __mocks__/tabulator-tables.js).
export const initPerspective = async () => ({
  worker: async () => ({
    table: async (data) => ({
      __data: data,
      size: async () => data.length,
      delete: async () => undefined,
    }),
  }),
});
```

In `vitest.config.ts`, add to the `resolve.alias` object ABOVE the `"~~"` entry (longer keys must win before `"~"` matches):

```ts
      // Perspective boots WASM at import; specs use the stub (see __mocks__/).
      "~/components/v2/extractions/perspective-bootstrap": r("./__mocks__/perspective-bootstrap.js"),
```

- [ ] **Step 6: Verify config health**

Run: `cd extralit-frontend && npm run test && npx nuxi typecheck`
Expected: suite still green; typecheck clean (nothing imports the bootstrap yet — this proves the config alone breaks nothing).

- [ ] **Step 7: Commit**

```bash
git add extralit-frontend/package.json extralit-frontend/package-lock.json extralit-frontend/nuxt.config.ts extralit-frontend/vitest.config.ts extralit-frontend/components/v2/extractions/perspective-bootstrap.ts extralit-frontend/__mocks__/perspective-bootstrap.js
# plus extralit-frontend/types/wasm-url.d.ts if you created it in Step 4
git commit -m "feat(v2-ui): Perspective 4.5.2 deps, WASM bootstrap, Vite/vitest wiring"
```

---

### Task 9: `ExtractionsGrid.vue` — viewer wrapper with banding + click plumbing (frontend)

**Files:**
- Create: `extralit-frontend/components/v2/extractions/ExtractionsGrid.vue`
- Test: `extralit-frontend/components/v2/extractions/ExtractionsGrid.test.ts`

**Interfaces:**
- Consumes: `initPerspective` (Task 8), `toPerspectiveData`/`cellAt`/`bandParity` (Task 6), `WorkspaceProjection` (Task 5).
- Produces: `<ExtractionsGrid :projection="…" @cell-click="…" />` (auto-imported by name — `components` config uses `pathPrefix: false`). Emits `cell-click` with `{ cell: ProjectionGridCell; reference: string; schemaId: string; columnName: string }`. Task 10's page listens to this.
- Lazy chunking (spec §3.3): Nuxt code-splits per page and auto-imported components bundle into the chunks that use them — since only `pages/extractions/index.vue` uses this component, the Perspective JS/WASM cost is paid only on `/extractions`. Verify in Task 13's `npm run build` output: the perspective modules must NOT appear in the entry chunk.
- Note: the custom-element/regular-table interactions cannot be exercised under happy-dom; the unit test covers mount → bootstrap → table creation → viewer load. The real rendering gate is Task 12's e2e spec.

- [ ] **Step 1: Write the failing component test**

Create `components/v2/extractions/ExtractionsGrid.test.ts`:

```ts
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import ExtractionsGrid from "./ExtractionsGrid.vue";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

const tableSpy = vi.fn(async (data: unknown) => ({ __data: data, delete: async () => undefined }));
const initSpy = vi.fn(async () => ({ worker: async () => ({ table: tableSpy }) }));

vi.mock("~/components/v2/extractions/perspective-bootstrap", () => ({
  initPerspective: (...args: unknown[]) => initSpy(...args),
}));

const PROJECTION = new WorkspaceProjection(
  [{ name: "Design.type", schemaId: "s-1", schemaName: "Design", questionName: "type", subColumn: null, dtype: "text" }],
  [
    {
      reference: "10.1/a",
      rowIndex: 0,
      cells: {
        "Design.type": { value: "RCT", source: "response", recordId: "r-1", agent: null, score: null },
      },
    },
  ],
  1
);

describe("ExtractionsGrid", () => {
  it("boots perspective once and loads the flat projection rows into a table", async () => {
    mount(ExtractionsGrid, {
      props: { projection: PROJECTION },
      global: {
        config: { compilerOptions: { isCustomElement: (tag: string) => tag.startsWith("perspective-") } },
      },
    });
    await flushPromises();

    expect(initSpy).toHaveBeenCalledTimes(1);
    expect(tableSpy).toHaveBeenCalledWith([{ reference: "10.1/a", "Design.type": "RCT" }]);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd extralit-frontend && npx vitest run components/v2/extractions/ExtractionsGrid.test.ts`
Expected: FAIL — component file not found.

- [ ] **Step 3: Implement the component**

Create `components/v2/extractions/ExtractionsGrid.vue`:

```vue
<template>
  <perspective-viewer ref="viewerEl" class="extractions-grid" data-testid="extractions-grid" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { initPerspective } from "~/components/v2/extractions/perspective-bootstrap";
import {
  bandParity,
  cellAt,
  toPerspectiveData,
} from "~/v2/domain/entities/projection/grid-adapter";
import {
  type ProjectionGridCell,
  type WorkspaceProjection,
} from "~/v2/domain/entities/projection/WorkspaceProjection";

interface PerspectiveViewerElement extends HTMLElement {
  load(table: unknown): Promise<void>;
  restore(config: Record<string, unknown>): Promise<void>;
  delete(): Promise<void>;
}

interface RegularTableElement extends HTMLElement {
  addStyleListener(callback: () => void): void;
  getMeta(td: HTMLElement): { x?: number; y?: number; column_header?: unknown[] };
}

const props = defineProps<{ projection: WorkspaceProjection }>();

const emit = defineEmits<{
  (
    e: "cell-click",
    payload: { cell: ProjectionGridCell; reference: string; schemaId: string; columnName: string }
  ): void;
}>();

const viewerEl = ref<PerspectiveViewerElement | null>(null);
let table: { delete(options?: Record<string, unknown>): Promise<void> } | null = null;

const regularTable = (): RegularTableElement | null =>
  (viewerEl.value?.querySelector("regular-table") as RegularTableElement | null) ?? null;

// Band + pointer styling via the datagrid's regular-table style hook: the grid is
// static (no sort/filter), so datagrid row index y maps 1:1 onto projection.rows.
const applyStyles = () => {
  const grid = regularTable();
  if (!grid) return;
  const parity = bandParity(props.projection);
  grid.addStyleListener(() => {
    for (const td of Array.from(grid.querySelectorAll("td"))) {
      const meta = grid.getMeta(td as HTMLElement);
      if (meta.y === undefined) continue;
      (td as HTMLElement).classList.toggle("extractions-grid__band", parity[meta.y] === 1);
      const columnName = String(meta.column_header?.at(-1) ?? "");
      (td as HTMLElement).classList.toggle(
        "extractions-grid__linkable",
        cellAt(props.projection, meta.y, columnName) !== null
      );
    }
  });
};

const onViewerClick = (event: Event) => {
  const grid = regularTable();
  const td = event
    .composedPath()
    .find((el): el is HTMLElement => el instanceof HTMLElement && el.tagName === "TD");
  if (!grid || !td) return;
  const meta = grid.getMeta(td);
  if (meta.y === undefined) return;
  const columnName = String(meta.column_header?.at(-1) ?? "");
  const cell = cellAt(props.projection, meta.y, columnName);
  const row = props.projection.rows[meta.y];
  const schemaId = props.projection.columns.find((c) => c.name === columnName)?.schemaId;
  if (!cell || !row || !schemaId) return;
  emit("cell-click", { cell, reference: row.reference, schemaId, columnName });
};

onMounted(async () => {
  const perspective = await initPerspective();
  const client = await perspective.worker();
  table = await client.table(toPerspectiveData(props.projection));
  const viewer = viewerEl.value;
  if (!viewer?.load) return; // unit tests stub the element away
  await viewer.load(table);
  // Static grid (spec §3.1): datagrid plugin, toolbar/settings hidden, natural order.
  await viewer.restore({ plugin: "Datagrid", settings: false });
  applyStyles();
  viewer.addEventListener("click", onViewerClick);
});

onBeforeUnmount(async () => {
  viewerEl.value?.removeEventListener("click", onViewerClick);
  // Order matters: table.delete() fails while a viewer still references it.
  await viewerEl.value?.delete?.().catch(() => undefined);
  await table?.delete().catch(() => undefined);
  table = null;
});
</script>

<style lang="scss" scoped>
.extractions-grid {
  display: block;
  height: calc(100vh - 200px);
  min-height: 400px;

  :deep(td.extractions-grid__band) {
    background: var(--bg-opacity-4, rgba(0, 0, 0, 0.04));
  }

  :deep(td.extractions-grid__linkable) {
    cursor: pointer;
  }
}
</style>
```

Note: if `restore({ plugin: "Datagrid" })` names the plugin differently in 4.5.2, the accepted values are listed by `viewer.restore` typings in `node_modules/@perspective-dev/viewer/dist/esm/perspective-viewer.d.ts` — the datagrid plugin registers as `"Datagrid"`. The `:deep()` selectors only apply if the datagrid renders in light DOM (it is slotted into the viewer); if banding doesn't show in Task 12's e2e run, move the two rules to an unscoped `<style lang="scss">` block keyed on `.extractions-grid`.

- [ ] **Step 4: Run to verify pass**

Run: `cd extralit-frontend && npx vitest run components/v2/extractions/ExtractionsGrid.test.ts`
Expected: PASS (a "Failed to resolve component: perspective-viewer" warning is acceptable under happy-dom if the test-utils compilerOptions don't reach the SFC compiler; the assertions still hold because the component guards on `viewer?.load`).

- [ ] **Step 5: Commit**

```bash
git add extralit-frontend/components/v2/extractions/ExtractionsGrid.vue extralit-frontend/components/v2/extractions/ExtractionsGrid.test.ts
git commit -m "feat(v2-ui): ExtractionsGrid Perspective wrapper with banding and click plumbing"
```

---

### Task 10: `/extractions` page + view-model + i18n + breadcrumbs (frontend)

**Files:**
- Create: `extralit-frontend/pages/extractions/index.vue`
- Create: `extralit-frontend/pages/extractions/useExtractionsViewModel.ts`
- Test: `extralit-frontend/pages/extractions/useExtractionsViewModel.test.ts`
- Modify: `extralit-frontend/composables/useV2Breadcrumbs.ts`
- Modify: `extralit-frontend/translation/en.js`, `translation/de.js`, `translation/es.js`, `translation/ja.js`

**Interfaces:**
- Consumes: `GetWorkspaceProjectionUseCase` via `useResolve` (Task 7), `useWorkspaces` (v1 store — documented exception), `ExtractionsGrid` (Task 9), `buildAnnotationUrl`/`ANNOTATION_CELL_LINKS_ENABLED` (Task 6), `useEnsureWorkspaces`, `InternalPage`/`AppHeader`.
- Produces: route `/extractions` (full-page standalone; NOT added to `index.vue`/nav — ledger §5). `useExtractionsViewModel(workspaceIdOverride?: string | null)` returning `{ projection, isLoading, loadFailed, workspaceId, load, onCellClick }`. `?workspace_id=` query overrides the selected workspace (deep-load/e2e determinism — the known workspace-hydration gap).
- Nuxt strips co-located non-`.vue` files from the route table (`pages:extend` hook), so the view-model/test files are safe next to the page.

- [ ] **Step 1: Write the failing view-model test**

Create `pages/extractions/useExtractionsViewModel.ts` consumers first — the test, `pages/extractions/useExtractionsViewModel.test.ts`:

```ts
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

const executeMock = vi.fn();
vi.mock("ts-injecty", () => ({
  useResolve: () => ({ execute: executeMock }),
}));

import { useExtractionsViewModel } from "./useExtractionsViewModel";

describe("useExtractionsViewModel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    executeMock.mockReset();
  });

  it("loads the projection for the override workspace id", async () => {
    const projection = new WorkspaceProjection([], [], 0);
    executeMock.mockResolvedValue(projection);

    const vm = useExtractionsViewModel("w-1");
    await vm.load();

    expect(executeMock).toHaveBeenCalledWith("w-1");
    expect(vm.projection.value).toBe(projection);
    expect(vm.loadFailed.value).toBe(false);
    expect(vm.isLoading.value).toBe(false);
  });

  it("does nothing without a workspace id", async () => {
    const vm = useExtractionsViewModel(null);
    await vm.load();
    expect(executeMock).not.toHaveBeenCalled();
  });

  it("flags load failure", async () => {
    executeMock.mockRejectedValue(new Error("boom"));
    const vm = useExtractionsViewModel("w-1");
    await vm.load();
    expect(vm.loadFailed.value).toBe(true);
  });

  it("builds the annotation URL on cell click but does not navigate (guard off)", () => {
    const vm = useExtractionsViewModel("w-1");
    const url = vm.onCellClick({ schemaId: "s-1", reference: "10.1/a b" });
    expect(url).toBe("/dataset/s-1/annotation-mode?_search=10.1%2Fa%20b");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd extralit-frontend && npx vitest run pages/extractions/useExtractionsViewModel.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the view-model**

Create `pages/extractions/useExtractionsViewModel.ts`:

```ts
import { computed, ref, watch } from "vue";
import { useResolve } from "ts-injecty";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import {
  ANNOTATION_CELL_LINKS_ENABLED,
  buildAnnotationUrl,
} from "~/v2/domain/entities/projection/grid-adapter";
import { type WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";
import { GetWorkspaceProjectionUseCase } from "~/v2/domain/usecases/get-workspace-projection-use-case";

export const useExtractionsViewModel = (workspaceIdOverride: string | null = null) => {
  const getWorkspaceProjectionUseCase = useResolve(GetWorkspaceProjectionUseCase);
  // v1 store — the documented exception, same as useSchemasViewModel.
  const workspacesStore = useWorkspaces();

  const projection = ref<WorkspaceProjection | null>(null);
  const isLoading = ref(false);
  const loadFailed = ref(false);

  const workspaceId = computed(
    () => workspaceIdOverride ?? workspacesStore.get().selectedWorkspace?.id ?? null
  );

  const load = async () => {
    if (!workspaceId.value) return;
    isLoading.value = true;
    loadFailed.value = false;
    try {
      projection.value = await getWorkspaceProjectionUseCase.execute(workspaceId.value);
    } catch {
      loadFailed.value = true;
    } finally {
      isLoading.value = false;
    }
  };

  const onCellClick = (payload: { schemaId: string; reference: string }): string => {
    const url = buildAnnotationUrl(payload.schemaId, payload.reference);
    // Guard (spec §3.3): navigation flips on when annotation-mode resolves v2 schema
    // ids (ledger §5). Until then the URL contract ships and is testable, unnavigated.
    if (ANNOTATION_CELL_LINKS_ENABLED) window.location.assign(url);
    return url;
  };

  watch(workspaceId, load);

  return { projection, isLoading, loadFailed, workspaceId, load, onCellClick };
};
```

- [ ] **Step 4: Run to verify pass**

Run: `cd extralit-frontend && npx vitest run pages/extractions/useExtractionsViewModel.test.ts`
Expected: ALL PASS.

- [ ] **Step 5: Breadcrumbs + i18n**

In `composables/useV2Breadcrumbs.ts`, add inside `useV2Breadcrumbs` (mirroring `schemasBreadcrumbs`) and export it:

```ts
  const extractionsBreadcrumbs = (): BreadcrumbItem[] => {
    const selected = workspacesStore.get().selectedWorkspace;
    const crumbs: BreadcrumbItem[] = [{ name: "Home", link: "/" }];
    if (selected) {
      crumbs.push({ name: selected.name, isWorkspace: true, workspaceId: selected.id });
    }
    crumbs.push({ name: "Extractions", link: "/extractions" });
    return crumbs;
  };

  return { schemasBreadcrumbs, extractionsBreadcrumbs };
```

In `translation/en.js`, next to the existing top-level `schemas:` block (~line 111), add:

```js
  extractions: {
    title: "Extractions",
    loading: "Loading extractions…",
    empty: "No extracted references in this workspace yet.",
    noWorkspace: "Select a workspace to view its extraction table.",
    loadError: "Could not load the extraction table.",
  },
```

Mirror the same block (same keys; translate values or keep English placeholders consistent with how the `schemas` block was handled) into `translation/de.js`, `translation/es.js`, `translation/ja.js`.

- [ ] **Step 6: Create the page**

Create `pages/extractions/index.vue` (same shape as `pages/schemas/index.vue`):

```vue
<template>
  <InternalPage>
    <template #header>
      <AppHeader :breadcrumbs="breadcrumbs" />
    </template>
    <template #page-content>
      <div class="extractions__content">
        <h1 v-text="$t('extractions.title')" />
        <p v-if="!workspaceId" v-text="$t('extractions.noWorkspace')" />
        <p v-else-if="loadFailed" v-text="$t('extractions.loadError')" />
        <p v-else-if="isLoading" v-text="$t('extractions.loading')" />
        <p v-else-if="projection && projection.rows.length === 0" v-text="$t('extractions.empty')" />
        <ExtractionsGrid v-else-if="projection" :projection="projection" @cell-click="onCellClick" />
      </div>
    </template>
  </InternalPage>
</template>

<script lang="ts">
import { computed, defineComponent, onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import { useExtractionsViewModel } from "./useExtractionsViewModel";

export default defineComponent({
  name: "ExtractionsPage",
  setup() {
    const route = useRoute();
    const workspaceIdOverride =
      typeof route.query.workspace_id === "string" ? route.query.workspace_id : null;
    const viewModel = useExtractionsViewModel(workspaceIdOverride);
    const { ensureWorkspaces } = useEnsureWorkspaces();
    const { extractionsBreadcrumbs } = useV2Breadcrumbs();
    const breadcrumbs = computed(() => extractionsBreadcrumbs());

    onBeforeMount(async () => {
      await ensureWorkspaces();
      await viewModel.load();
    });

    return { ...viewModel, breadcrumbs };
  },
});
</script>

<style lang="scss" scoped>
.extractions__content {
  padding: $base-space * 3;
}
</style>
```

(`useEnsureWorkspaces` and `useV2Breadcrumbs` are Nuxt auto-imported composables — match how `pages/schemas/index.vue` references them; if that file imports them explicitly, do the same here.)

- [ ] **Step 7: Full check + smoke**

Run: `cd extralit-frontend && npm run test && npx nuxi typecheck && npm run lint`
Expected: all green.

Optional smoke (backend on :6900): `npm run dev` → open `http://localhost:3000/extractions` → page renders (empty state or grid).

- [ ] **Step 8: Commit**

```bash
git add extralit-frontend/pages/extractions extralit-frontend/composables/useV2Breadcrumbs.ts extralit-frontend/translation
git commit -m "feat(v2-ui): /extractions page with Perspective grid and workspace override"
```

---

### Task 11: Delete the reference-review page (frontend)

**Files:**
- Create: `extralit-frontend/v2/domain/entities/review/ReviewCell.ts` (type extraction so kept files survive)
- Modify: `components/v2/review/ReviewCellInput.vue`, `components/v2/review/ReviewCellInput.test.ts`, `components/v2/review/ReviewProvenance.vue`, `v2/domain/entities/review/widget-adapters.ts`, `v2/domain/entities/review/widget-adapters.test.ts`, `v2/di/di.ts`, `components/v2/schemas/V2RecordsTable.vue` (+ its `.test.ts` if it asserts the link)
- Delete: `pages/references/[...reference].vue`, `pages/references/useReferenceReviewViewModel.ts`, `pages/references/useReferenceReviewViewModel.test.ts`, `components/v2/review/ProjectionReviewForm.vue` (+ co-located `.test.ts`), `components/v2/review/ReviewRecordCard.vue` (+ co-located `.test.ts` if present), `v2/domain/entities/review/ReferenceReview.ts`, `v2/domain/usecases/get-reference-review-use-case.ts`, `v2/domain/usecases/get-reference-review-use-case.test.ts`, `v2/infrastructure/storage/ReferenceReviewsStorage.ts`, `e2e/v2/review-loop.spec.ts`, `e2e/v2/draft-lifecycle.spec.ts`, `e2e/v2/slashed-reference.spec.ts`

**Interfaces:**
- Produces: `v2/domain/entities/review/ReviewCell.ts` exporting `Provenance` and `ReviewCell` — the ONLY review types the kept drawer-reuse files need (`ReviewRecord`/`ReferenceReview`/`ContextField`/`OrphanedValue` die with the page). Kept and still registered in DI: `SubmitReferenceReviewUseCase`, `SaveReviewDraftUseCase`, `DiscardReviewUseCase`, `ProjectionRepository`.

- [ ] **Step 1: Extract the kept types**

Create `v2/domain/entities/review/ReviewCell.ts` (moved verbatim from `ReferenceReview.ts`):

```ts
import { Question } from "../question/Question";

export interface Provenance {
  agent: string | null;
  score: number | null;
  suggestedValue: unknown;
}

export class ReviewCell {
  constructor(
    public readonly question: Question,
    public readonly value: unknown,
    public readonly source: "response" | "suggestion" | null,
    public readonly provenance: Provenance | null,
    // The question binds a column absent from this record's pinned version cache (§17.3).
    public readonly notApplicable: boolean
  ) {}
}
```

- [ ] **Step 2: Repoint the kept importers**

- `components/v2/review/ReviewCellInput.vue` line ~55: `import { type ReviewCell } from "~/v2/domain/entities/review/ReviewCell";`
- `components/v2/review/ReviewCellInput.test.ts` line ~5: same repoint (import `ReviewCell` — and `Provenance` if it uses it — from `~/v2/domain/entities/review/ReviewCell`).
- `components/v2/review/ReviewProvenance.vue` line ~13: `import { type Provenance } from "~/v2/domain/entities/review/ReviewCell";`
- `v2/domain/entities/review/widget-adapters.ts` line ~2: `import { type ReviewCell } from "./ReviewCell";`
- `v2/domain/entities/review/widget-adapters.test.ts` line ~3: same repoint.

- [ ] **Step 3: Delete the superseded files**

```bash
cd extralit-frontend
git rm pages/references/[...reference].vue pages/references/useReferenceReviewViewModel.ts pages/references/useReferenceReviewViewModel.test.ts
git rm components/v2/review/ProjectionReviewForm.vue components/v2/review/ReviewRecordCard.vue
git rm --ignore-unmatch components/v2/review/ProjectionReviewForm.test.ts components/v2/review/ReviewRecordCard.test.ts
git rm v2/domain/entities/review/ReferenceReview.ts
git rm v2/domain/usecases/get-reference-review-use-case.ts v2/domain/usecases/get-reference-review-use-case.test.ts
git rm v2/infrastructure/storage/ReferenceReviewsStorage.ts
git rm e2e/v2/review-loop.spec.ts e2e/v2/draft-lifecycle.spec.ts e2e/v2/slashed-reference.spec.ts
```

- [ ] **Step 4: Clean DI**

In `v2/di/di.ts` remove the imports of `GetReferenceReviewUseCase` and `useReferenceReviews`, and remove the whole `register(GetReferenceReviewUseCase).withDependencies(…).build(),` entry. KEEP `SubmitReferenceReviewUseCase`, `SaveReviewDraftUseCase`, `DiscardReviewUseCase`, and `ProjectionRepository` registrations (they power the future embedded drawer).

- [ ] **Step 5: Retarget the records-table reference cell**

In `components/v2/schemas/V2RecordsTable.vue` (lines ~13–19) replace the `NuxtLink` with plain text, keeping `data-reference` (e2e hooks use it):

```vue
        <td>
          <span :data-reference="record.reference">{{ record.reference }}</span>
        </td>
```

If `components/v2/schemas/V2RecordsTable.test.ts` asserts the link/href, update those assertions to the span + `data-reference` attribute.

- [ ] **Step 6: Sweep for dead references**

```bash
cd extralit-frontend && grep -rn "references/" pages components v2 e2e composables --include="*.ts" --include="*.vue" | grep -v "projection/references" | grep -v node_modules
grep -rn "ReferenceReview\|useReferenceReviews\|ProjectionReviewForm\|ReviewRecordCard" pages components v2 e2e --include="*.ts" --include="*.vue"
```
Expected: no hits outside `ReviewCell.ts` comments/kept files' repointed imports. Fix any stragglers the same way (repoint or delete).

- [ ] **Step 7: Verify everything still passes**

Run: `cd extralit-frontend && npm run test && npx nuxi typecheck && npm run lint`
Expected: all green; test count drops by the deleted specs only.

- [ ] **Step 8: Commit**

```bash
git add -A extralit-frontend
git commit -m "refactor(v2-ui): delete reference-review page — review derives from projection (spec §3.5)"
```

---

### Task 12: e2e — seed extension + `extractions-grid.spec.ts`

**Files:**
- Modify: `extralit-frontend/e2e/v2/seed/seed_v2_e2e.py`
- Modify: `extralit-frontend/e2e/v2/fixtures.ts` (extend `SeedOutput`)
- Create: `extralit-frontend/e2e/v2/extractions-grid.spec.ts`

**Interfaces:**
- Consumes: existing `test`/`expect`/`signIn`/`loadSeed` from `e2e/v2/fixtures.ts`; the `/extractions?workspace_id=` override (Task 10).
- Produces: seed additionally creates (a) a submitted response for the `label` question (value `"control"`) plus a competing suggestion (`"intervention"`) so the grid proves response-beats-suggestion, and (b) a second schema `e2e_v2_empty` with one question and ZERO records (coverage map). `SeedOutput` gains `emptySchemaName: string`.

- [ ] **Step 1: Extend the seed script**

In `e2e/v2/seed/seed_v2_e2e.py`:

Top-of-file constants (next to `SCHEMA_NAME`):

```python
EMPTY_SCHEMA_NAME = "e2e_v2_empty"

EMPTY_BODY = pa.DataFrameSchema(
    columns={"notes": pa.Column(pa.String, nullable=True)}
).to_json()
```

Extend the schema-recreate loop (currently deletes only `SCHEMA_NAME`):

```python
        for schema_item in schemas:
            if schema_item["name"] in (SCHEMA_NAME, EMPTY_SCHEMA_NAME):
                client.delete(f"/api/v2/schemas/{schema_item['id']}").raise_for_status()
```

After the existing suggestion `client.put(...suggestions...)` block, add:

```python
        # Response-beats-suggestion on `label`: competing suggestion + submitted response.
        client.put(
            f"/api/v2/records/{record['id']}/suggestions",
            json={
                "question_id": questions["label"]["id"],
                "value": "intervention",
                "score": 0.55,
                "agent": "e2e-seeder",
            },
        ).raise_for_status()
        client.put(
            f"/api/v2/records/{record['id']}/responses",
            json={"values": {"label": {"value": "control"}}, "status": "submitted"},
        ).raise_for_status()

        # Second schema with zero records: the grid doubles as a coverage map (§3.1).
        empty_schema = (
            client.post(
                "/api/v2/schemas",
                json={"name": EMPTY_SCHEMA_NAME, "workspace_id": workspace["id"]},
            )
            .raise_for_status()
            .json()
        )
        client.post(
            f"/api/v2/schemas/{empty_schema['id']}/versions", json={"body": EMPTY_BODY}
        ).raise_for_status()
        client.post(
            f"/api/v2/schemas/{empty_schema['id']}/questions",
            json={
                "name": "notes",
                "title": "Notes",
                "type": "text",
                "columns": ["notes"],
                "settings": {},
                "required": False,
            },
        ).raise_for_status()
```

And extend the output dict:

```python
        "emptySchemaName": EMPTY_SCHEMA_NAME,
```

In `e2e/v2/fixtures.ts`, add `emptySchemaName: string;` to the `SeedOutput` type.

- [ ] **Step 2: Write the spec**

Create `e2e/v2/extractions-grid.spec.ts`:

```ts
import { expect, loadSeed, signIn, test } from "./fixtures";

// Replacement gate for the deleted review-loop specs (spec §3.5 accepted risk):
// seed → grid renders coalesced values → coverage-gap columns present.
test("extraction table renders coalesced values and coverage gaps", async ({ page }) => {
  const seed = loadSeed();
  await signIn(page);

  const projectionRequest = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v2/projection") &&
      !r.url().includes("/references/") &&
      r.request().method() === "GET"
  );
  await page.goto(`/extractions?workspace_id=${seed.workspaceId}`);
  expect((await projectionRequest).status()).toBe(200);

  const viewer = page.locator("perspective-viewer");
  await expect(viewer).toBeVisible();

  // Column manifest: both schemas appear — including the record-less one (coverage map).
  await expect(page.getByText(`${seed.schemaName}.size`)).toBeVisible();
  await expect(page.getByText(`${seed.emptySchemaName}.notes`)).toBeVisible();

  // Rows + coalesced values: suggestion-sourced `size`, response-beats-suggestion `label`.
  await expect(page.getByText(seed.reference).first()).toBeVisible();
  await expect(page.getByText("120").first()).toBeVisible();
  await expect(page.getByText("control").first()).toBeVisible();
  await expect(page.getByText("intervention")).toHaveCount(0);
});
```

- [ ] **Step 3: Run against the live stack**

Runbook (Orin host — see `extralit-frontend/CLAUDE.md` "v2 e2e suite" and the server-env notes):

```bash
docker run -d --rm --name tmp-redis -p 6379:6379 redis:7   # if not already up
cd extralit-server && MINIO_HOST=localhost ELASTICSEARCH_HOST=localhost REDIS_URL=redis://localhost:6379 uv run python -m extralit_server server-dev &   # or however the stack is normally brought up
cd extralit-frontend
npm run e2e:v2:seed
npm run dev -- --host &
npm run e2e:v2
```

Expected: `extractions-grid.spec.ts` PASSES, and the remaining v2 specs (`auth-smoke`, `search-roundtrip`) stay green (the seed's new response/suggestion must not break `search-roundtrip` — if it asserts on the `label` record fields, re-run `npm run e2e:v2:seed` and check its assertions).

If Perspective fails to boot in the real browser (WASM path / init API mismatch), fix in Task 8's bootstrap or Task 9's restore config — the exact d.ts files to consult are noted in those tasks. This spec is the acceptance gate for the whole Perspective wiring.

- [ ] **Step 4: Commit**

```bash
git add extralit-frontend/e2e/v2/seed/seed_v2_e2e.py extralit-frontend/e2e/v2/fixtures.ts extralit-frontend/e2e/v2/extractions-grid.spec.ts
git commit -m "test(v2-ui): extractions-grid e2e gate with coverage-map seed"
```

---

### Task 13: Phase 2 final verification — full suites + drift gate

**Files:** none new (fix-ups only if something fails). Re-runs the Phase 1 gates too, since Phase 2 sits on top of them.

- [ ] **Step 1: Server suite**

```bash
docker run -d --rm --name tmp-redis -p 6379:6379 redis:7   # if not already running
cd extralit-server && uv run pytest tests/unit/validators/v2 tests/integration/contexts/v2 tests/integration/api/v2 -q
```
Expected: ALL PASS.

- [ ] **Step 2: Contract drift gate**

```bash
cd extralit-frontend && npm run gen:api && git diff --exit-code v2/infrastructure/api
```
Expected: exit 0 (no drift — the committed snapshot matches the server).

- [ ] **Step 3: Frontend gates**

```bash
cd extralit-frontend && npm run test && npx nuxi typecheck && npm run lint && npm run build
```
Expected: all green; `npm run build` proves the Perspective WASM `?url` imports and `esnext` target survive a production build.

- [ ] **Step 4: Scope audit against the spec**

Confirm: no nav/`index.vue` wiring for `/extractions`; no sort/filter UI; no Arrow IPC; no annotation-mode changes; `ANNOTATION_CELL_LINKS_ENABLED === false`; kept review files intact (spec §3.5 keep-list); `V2TableEditor.vue` untouched (still emits the dict form).

- [ ] **Step 5: Commit any fix-ups**

```bash
git status   # should be clean; commit stragglers with a descriptive message if not
```

Then hand off with superpowers:finishing-a-development-branch — PR 2 from `feat/v2-ui-extraction-grid` to `develop` ("feat(v2-ui): /extractions Perspective grid, review-page retirement"). If PR 1 has merged, rebase onto `develop` first so PR 2's diff shows only Phase 2 commits; if not, open it stacked on `feat/v2-ui-extraction-table` and retarget after PR 1 lands.
