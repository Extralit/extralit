# v2 Frontend Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-07-09-v2-frontend-vertical-slice-design.md` (parent: `2026-06-27-schema-centric-data-model-design.md`)

**Goal:** Build the first v2 UI vertical slice — schemas → records → search → annotation — as an isolated `v2/` module in `extralit-frontend/`, consuming the shipped `/api/v2` surface, producing the reference-agnostic `ProjectionReviewForm`.

**Architecture:** A new `v2/` DDD module mirrors `v1/` (entities → use-cases → repositories → Pinia storage → ts-injecty DI), registered by a `loadV2DependencyContainer` called after v1's in `plugins/3.di.ts`. API request/response shapes come from a checked-in OpenAPI snapshot + `openapi-typescript`-generated types; repositories stay hand-written on the shared axios instance. Four Argilla-inherited leaf widgets are *moved* (not copied) to `components/base/inputs/` and v1 wrappers re-pointed; the table editor is rebuilt lean on tabulator-tables.

**Tech Stack:** Vue 3.5 / Nuxt 4 (SPA, `ssr:false`), Pinia, ts-injecty, axios (baseURL `/api`), openapi-typescript (new devDep, types only), tabulator-tables `^6.5.2`, @nuxtjs/i18n v10, Vitest + happy-dom + @vue/test-utils, Playwright (remote chromium over CDP). Server side: FastAPI + Typer CLI, uv, pytest.

## Global Constraints

- **v2→v1 import boundary:** `v2/**` may import from v1 ONLY: `v1/store/create.ts`, `v1/infrastructure/services/*`, and the extracted leaf inputs under `components/base/inputs/`. It must NOT import v1 entities (`Dataset`, `Record`, `Question`, `QuestionAnswer`) or v1 repositories. v1 never imports from `v2/`.
  - **Documented exception (workspaces survive Phase 6):** v2 *pages/view-models* (not `v2/` module code) may read the current workspace via `useWorkspaces()` from `v1/infrastructure/storage/WorkspaceStorage.ts` and the `Workspace` entity. This avoids forking workspace fetching; record any other exception candidates in the spec ledger instead of importing.
- **Reuse-don't-fork:** leaves are extracted with `git mv` and v1 re-pointed; nothing is copy-pasted into `v2/`.
- **Name-keyed global registries:** ts-injecty DI and `useStoreFor` Pinia stores are keyed by **class name**; Nuxt component auto-import is **flat** (`pathPrefix: false`). Every v2 use-case/repository/storage-state class name and every new component name must be globally unique vs v1 (hence `V2RecordRepository`, `V2TableEditor`, etc.).
- **UI copy says "Schema"** — all new copy through i18n key families `schemas.*` and `review.*` in `translation/en.js` (fallbackLocale is `en`; other locales fall back). Never reuse `dataset`-keyed copy.
- **Routes:** `/schemas`, `/schemas/[id]`, `/schemas/[id]/settings`. No `/v2/` prefix. Always `encodeURIComponent(reference)` when building API URLs.
- **axios baseURL is `/api`** → repository paths start with `/v2/...`. The shared instance injects `Authorization: Bearer` and runs `AxiosErrorHandler` + `AxiosCache` interceptors — do not create a parallel HTTP client.
- **Server contract gotchas** (from spec §7/§10, verified against merged code): projection cells & `response.values` keyed by question **name**, suggestions by question **id**; `response.values` is double-wrapped `{question_name: {"value": …}}` on PUT and GET; `GET /records/{id}/responses` returns `null` with 200; two 422 body shapes (`detail: string` and `detail: [{loc,msg,type}]`); `total` is approximate; unknown filter columns → 5xx (UI must offer only known columns); `span` questions are rejected by the server (excluded from the slice).
- **Question value shapes the server validates** (v1 validator union): `text`→string, `label_selection`→string, `multi_label_selection`→string[], `rating`→number, `ranking`→`[{value, rank}]`, `table`→object with keys ⊆ bound columns.
- **Tooling:** Python via `uv` only (`uv run pytest`, `uv add`); frontend `npm run test` (vitest, colocated `*.test.ts`), `npm run lint`, `npm run format`. Frontend TS posture is `strict:false`; type-only imports must use inline `import { type X }` (Vite `isolatedModules`).
- **Commits:** conventional commits, one per task minimum, on a feature branch off `develop`.

## Resolved open items (spec §9)

1. **OpenAPI dump home:** new Typer subcommand `openapi-dump` in `extralit_server.cli` (Task 1) — testable, matches the existing CLI pattern.
2. **App home:** nav sibling — a third "Schemas" tab on the home page that navigates to `/schemas` (Task 6). Home swap deferred to Phase 6.
3. **i18n:** new `schemas.*` / `review.*` families in `translation/en.js` only (fallback covers de/es/ja).
4. **Rebuild-index affordance:** yes — button on `/schemas/[id]/settings` calling `POST /v2/schemas/{id}:rebuild-index`, showing the returned `{indexed: n}` (Task 8).


## File structure

```
extralit-server/
  src/extralit_server/cli/openapi_dump.py            # Task 1 (new)
  src/extralit_server/cli/__init__.py                # Task 1 (register command)
  tests/unit/test_openapi_dump.py                    # Task 1 (new)

extralit-frontend/
  v2/
    domain/entities/
      schema/Schema.ts, schema/ColumnMeta.ts, schema/SchemaVersion.ts     # Task 3
      question/Question.ts                                                # Task 3
      review/widget-mapping.ts (+ .test.ts)                               # Task 3
      record/V2Record.ts, record/RecordsPage.ts                           # Task 5
      search/SearchCriteria.ts (+ .test.ts)                               # Task 5
      review/response-values.ts (+ .test.ts)                              # Task 10
      review/SuggestionHint.ts (+ tests)                                  # Task 11
      review/widget-adapters.ts (+ .test.ts)                              # Task 14
    domain/usecases/
      get-schemas-use-case.ts, get-schema-settings-use-case.ts            # Task 4
      get-schema-records-use-case.ts, search-records-use-case.ts,
      rebuild-schema-index-use-case.ts                                    # Task 5
      submit-reference-review-use-case.ts, save-review-draft-use-case.ts,
      discard-review-use-case.ts (+ tests)                                # Task 12
    infrastructure/
      api/openapi.json, api/generated/v2-api.ts                           # Task 2 (generated, committed)
      repositories/SchemaRepository.ts (+ .test.ts)                       # Task 4
      repositories/V2RecordRepository.ts (+ .test.ts)                     # Task 5
      repositories/AnnotationRepository.ts, ProjectionRepository.ts,
      repositories/apiErrors.ts (+ tests)                                 # Task 10
      storage/SchemasStorage.ts                                           # Task 4
    di/di.ts, di/index.ts                                                 # Task 4 (grows each task)
  components/base/inputs/                                                 # Task 9 (moved leaves)
    label-selection/{LabelSelection.component.vue, useLabelSelectionViewModel.ts}
    rating/RatingMonoSelection.component.vue
    ranking/{DndSelection.component.vue, ranking-adapter.js, ranking-fakes.js, ranking-adapter.test.js}
    text-area/ContentEditableFeedbackTask.vue
  components/v2/
    schemas/V2RecordsTable.vue                                            # Task 7
    review/{ReviewCellInput.vue, ReviewProvenance.vue} (+ tests)          # Task 14
    table/V2TableEditor.vue (+ .test.ts)                                  # Task 13
  pages/schemas/index.vue + useSchemasViewModel.ts (+ test)               # Task 6
  pages/schemas/[id]/index.vue + useSchemaRecordsViewModel.ts (+ test)    # Task 7
  pages/schemas/[id]/settings.vue + useSchemaSettingsViewModel.ts (+ test)# Task 8
  e2e/v2/                                                                 # Tasks 16–17
    fixtures.ts, seed/seed_v2_e2e.py, *.spec.ts
  translation/en.js                                                       # Tasks 6, 8, 14 (add keys)
  plugins/3.di.ts                                                         # Task 4 (call v2 loader)
  playwright.config.ts, eslint.config.mjs, package.json                   # Tasks 2, 16

.github/workflows/extralit-frontend.yml                                   # Task 2 (types drift gate)
.github/workflows/extralit-server.yml                                     # Task 2 (snapshot drift gate)
```

---

### Task 1: Server `openapi-dump` CLI command

**Files:**
- Create: `extralit-server/src/extralit_server/cli/openapi_dump.py`
- Modify: `extralit-server/src/extralit_server/cli/__init__.py`
- Test: `extralit-server/tests/unit/test_openapi_dump.py`

**Interfaces:**
- Consumes: `extralit_server.api.v2.api_v2` (module-level FastAPI singleton; `api_v2.openapi()` returns the schema dict; paths are mount-relative, e.g. `/schemas`).
- Produces: CLI `python -m extralit_server.cli openapi-dump [--output PATH]` printing/writing deterministic JSON (`indent=2, sort_keys=True`, trailing newline). Task 2's `gen:api:snapshot` npm script and the server CI drift gate both invoke it.

- [ ] **Step 1: Write the failing test**

Create `extralit-server/tests/unit/test_openapi_dump.py`:

```python
import json

from typer.testing import CliRunner

from extralit_server.cli import app

runner = CliRunner()


def test_openapi_dump_writes_v2_schema(tmp_path):
    output = tmp_path / "openapi.json"

    result = runner.invoke(app, ["openapi-dump", "--output", str(output)])

    assert result.exit_code == 0
    schema = json.loads(output.read_text())
    assert schema["info"]["title"] == "Extralit v2"
    assert "/schemas" in schema["paths"]
    assert "/projection/references/{reference}" in schema["paths"]


def test_openapi_dump_is_deterministic(tmp_path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"

    assert runner.invoke(app, ["openapi-dump", "--output", str(first)]).exit_code == 0
    assert runner.invoke(app, ["openapi-dump", "--output", str(second)]).exit_code == 0

    assert first.read_bytes() == second.read_bytes()


def test_openapi_dump_prints_to_stdout_without_output():
    result = runner.invoke(app, ["openapi-dump"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["info"]["title"] == "Extralit v2"
```

Note: if the `/projection/references/{reference}` path key assertion fails, print `schema["paths"].keys()` and use the exact key FastAPI emits for the `{reference:path}` route (it strips the `:path` converter to `{reference}`); fix the assertion, not the route.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-server && uv run pytest tests/unit/test_openapi_dump.py -v --disable-warnings`
Expected: FAIL — exit code 2 from Typer ("No such command 'openapi-dump'").

- [ ] **Step 3: Write the command**

Create `extralit-server/src/extralit_server/cli/openapi_dump.py`:

```python
import json
from pathlib import Path
from typing import Optional

import typer


def openapi_dump(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the schema to this file instead of stdout",
    ),
) -> None:
    """Dump the /api/v2 OpenAPI schema as deterministic JSON (for frontend type generation)."""
    # Imported lazily so `--help` stays fast and settings load only when the command runs.
    from extralit_server.api.v2 import api_v2

    text = json.dumps(api_v2.openapi(), indent=2, sort_keys=True) + "\n"

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    else:
        typer.echo(text, nl=False)
```

Modify `extralit-server/src/extralit_server/cli/__init__.py` — add the import and registration (final file):

```python
import typer

from .database import app as database_app
from .index import app as index_app
from .openapi_dump import openapi_dump
from .search_engine import app as search_engine_app
from .start import start
from .worker import worker

app = typer.Typer(help="Commands for Extralit server management", no_args_is_help=True)

app.add_typer(database_app, name="database")
app.add_typer(index_app, name="index")
app.add_typer(search_engine_app, name="search-engine")
app.command(name="worker", help="Starts rq workers")(worker)
app.command(name="start", help="Starts the Extralit server")(start)
app.command(name="openapi-dump", help="Dump the /api/v2 OpenAPI schema as JSON")(openapi_dump)

if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-server && uv run pytest tests/unit/test_openapi_dump.py -v --disable-warnings`
Expected: 3 PASSED.

- [ ] **Step 5: Lint and commit**

```bash
cd extralit-server && uv run ruff check src/extralit_server/cli tests/unit/test_openapi_dump.py
git add src/extralit_server/cli/openapi_dump.py src/extralit_server/cli/__init__.py tests/unit/test_openapi_dump.py
git commit -m "feat(server): add openapi-dump CLI command for v2 schema export"
```

---

### Task 2: Frontend typegen pipeline + drift gates

**Files:**
- Create: `extralit-frontend/v2/infrastructure/api/openapi.json` (generated, committed)
- Create: `extralit-frontend/v2/infrastructure/api/generated/v2-api.ts` (generated, committed)
- Modify: `extralit-frontend/package.json` (devDep + scripts)
- Modify: `extralit-frontend/eslint.config.mjs` (ignore generated dir)
- Modify: `.github/workflows/extralit-frontend.yml` (types drift gate)
- Modify: `.github/workflows/extralit-server.yml` (snapshot drift gate)

**Interfaces:**
- Consumes: Task 1's `openapi-dump` command.
- Produces: `import type { components } from "~/v2/infrastructure/api/generated/v2-api"` — all later repository tasks type DTOs as `components["schemas"]["SchemaRead"]`, `["SchemaVersionRead"]`, `["QuestionRead"]`, `["RecordRead"]`, `["Records"]`, `["RecordSearchQuery"]`, `["SuggestionRead"]`, `["ResponseRead"]`, `["ProjectionView"]`. npm scripts `gen:api`, `gen:api:snapshot`, `gen:api:types`.

- [ ] **Step 1: Add openapi-typescript devDependency**

```bash
cd extralit-frontend && npm install --save-dev openapi-typescript
```

- [ ] **Step 2: Add npm scripts**

In `extralit-frontend/package.json` `"scripts"`, add (after `"test:coverage"`):

```json
"gen:api": "npm run gen:api:snapshot && npm run gen:api:types",
"gen:api:snapshot": "uv run --project ../extralit-server python -m extralit_server.cli openapi-dump --output v2/infrastructure/api/openapi.json",
"gen:api:types": "openapi-typescript v2/infrastructure/api/openapi.json -o v2/infrastructure/api/generated/v2-api.ts && prettier --write v2/infrastructure/api/generated/v2-api.ts"
```

- [ ] **Step 3: Generate and inspect**

Run: `cd extralit-frontend && npm run gen:api`
Expected: both files created. Open `v2/infrastructure/api/generated/v2-api.ts` and verify it exports `paths` and `components` with `components["schemas"]["SchemaRead"]` present. If `uv run --project` fails to resolve the server env, use `uv run --directory ../extralit-server python -m extralit_server.cli openapi-dump --output ../extralit-frontend/v2/infrastructure/api/openapi.json` in the script instead.

- [ ] **Step 4: Ignore generated file in eslint**

In `extralit-frontend/eslint.config.mjs`, first config object's `ignores` array, add after `"components/base/base-render-table/**",`:

```js
      "v2/infrastructure/api/generated/**",
```

- [ ] **Step 5: Frontend CI types drift gate**

In `.github/workflows/extralit-frontend.yml`, insert between the "Install dependencies 📦" and "Run lint 🧹" steps:

```yaml
      - name: Check generated v2 API types are current 🔒
        run: |
          npm run gen:api:types
          git diff --exit-code -- v2/infrastructure/api/generated
```

(Only regenerates TS from the committed snapshot — no Python needed in this job. Snapshot↔server drift is gated server-side, next step.)

- [ ] **Step 6: Server CI snapshot drift gate**

In `.github/workflows/extralit-server.yml`, `build` job, insert between "Install dependencies" and "Run tests 📈":

```yaml
      - name: Check frontend v2 OpenAPI snapshot is current 🔒
        run: |
          uv run python -m extralit_server.cli openapi-dump --output /tmp/openapi-v2.json
          diff -u ../extralit-frontend/v2/infrastructure/api/openapi.json /tmp/openapi-v2.json \
            || { echo "::error::v2 OpenAPI drift — run 'npm run gen:api' in extralit-frontend and commit"; exit 1; }
```

Also add `"extralit-frontend/v2/infrastructure/api/**"` to that workflow's `on.push.paths` list so snapshot-only commits re-run the gate.

- [ ] **Step 7: Verify determinism and commit**

Run: `cd extralit-frontend && npm run gen:api && git status --porcelain -- v2/` — expected: no diff on second run (only untracked files from the first run staged below).

```bash
git add extralit-frontend/package.json extralit-frontend/package-lock.json extralit-frontend/eslint.config.mjs \
  extralit-frontend/v2/infrastructure/api .github/workflows/extralit-frontend.yml .github/workflows/extralit-server.yml
git commit -m "feat(frontend): v2 OpenAPI snapshot + openapi-typescript typegen with CI drift gates"
```

---

### Task 3: v2 domain entities + widget mapping (pure domain, no infra)

**Files:**
- Create: `extralit-frontend/v2/domain/entities/schema/Schema.ts`
- Create: `extralit-frontend/v2/domain/entities/schema/ColumnMeta.ts`
- Create: `extralit-frontend/v2/domain/entities/schema/SchemaVersion.ts`
- Create: `extralit-frontend/v2/domain/entities/question/Question.ts`
- Create: `extralit-frontend/v2/domain/entities/review/widget-mapping.ts`
- Test: `extralit-frontend/v2/domain/entities/review/widget-mapping.test.ts`
- Test: `extralit-frontend/v2/domain/entities/schema/SchemaVersion.test.ts`

**Interfaces:**
- Consumes: nothing (leaf task).
- Produces (used by every later task):
  - `class Schema { id, name, status, workspaceId, currentVersionId, settings, insertedAt, updatedAt }`
  - `class ColumnMeta { name: string; dtype: string; nullable: boolean; review: ReviewOverlay | null }`
  - `class SchemaVersion { id, schemaId, version: number, columnsCache: ColumnMeta[], reviewWidgets, insertedAt; findColumn(name): ColumnMeta | undefined }`
  - `class Question { id, schemaId, name, title, description, type: QuestionType, columns: string[], settings, required; get options(): QuestionOption[]; get ratingValues(): number[] }` with `type QuestionType = "text" | "rating" | "label_selection" | "multi_label_selection" | "ranking" | "table"` and `interface QuestionOption { value: string; text: string; description: string | null }`
  - `type CellEditor = "text" | "number" | "checkbox" | "date"`; `dtypeDefaultEditor(dtype): CellEditor`; `columnCellEditor(column: ColumnMeta): CellEditor`; `contextRenderer(column: ColumnMeta): CellEditor`

- [ ] **Step 1: Write the failing tests**

Create `extralit-frontend/v2/domain/entities/review/widget-mapping.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ColumnMeta } from "../schema/ColumnMeta";
import { columnCellEditor, contextRenderer, dtypeDefaultEditor } from "./widget-mapping";

describe("dtypeDefaultEditor", () => {
  it.each([
    ["str", "text"],
    ["int64", "number"],
    ["int32", "number"],
    ["float64", "number"],
    ["bool", "checkbox"],
    ["datetime64[ns]", "date"],
    ["object", "text"], // unknown dtype falls back to text
  ])("maps dtype %s to %s", (dtype, editor) => {
    expect(dtypeDefaultEditor(dtype)).toBe(editor);
  });
});

describe("columnCellEditor (§6.2 precedence)", () => {
  it("uses review.type when it is a known editor", () => {
    const column = new ColumnMeta("score", "float64", true, { type: "text" });
    expect(columnCellEditor(column)).toBe("text");
  });

  it("falls back to dtype default when review.type is unknown (forward-compatible overlay)", () => {
    const column = new ColumnMeta("score", "float64", true, { type: "sparkline" });
    expect(columnCellEditor(column)).toBe("number");
  });

  it("falls back to dtype default when review is null", () => {
    const column = new ColumnMeta("done", "bool", false, null);
    expect(columnCellEditor(column)).toBe("checkbox");
  });
});

describe("contextRenderer (§6.3)", () => {
  it("mirrors the same precedence for read-only context fields", () => {
    expect(contextRenderer(new ColumnMeta("when", "datetime64[ns]", true, null))).toBe("date");
    expect(contextRenderer(new ColumnMeta("when", "datetime64[ns]", true, { type: "text" }))).toBe("text");
  });
});
```

Create `extralit-frontend/v2/domain/entities/schema/SchemaVersion.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ColumnMeta } from "./ColumnMeta";
import { SchemaVersion } from "./SchemaVersion";

describe("SchemaVersion", () => {
  const version = new SchemaVersion(
    "v-1",
    "s-1",
    1,
    [new ColumnMeta("title", "str", false, null)],
    {},
    "2026-01-01T00:00:00"
  );

  it("finds a cached column by name", () => {
    expect(version.findColumn("title")?.dtype).toBe("str");
  });

  it("returns undefined for a column missing from this version's cache (old-version tolerance)", () => {
    expect(version.findColumn("added_later")).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extralit-frontend && npx vitest run v2/domain --reporter=verbose`
Expected: FAIL — cannot resolve `./widget-mapping` / `./SchemaVersion`.

- [ ] **Step 3: Write the entities**

Create `extralit-frontend/v2/domain/entities/schema/Schema.ts`:

```ts
export class Schema {
  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly status: string,
    public readonly workspaceId: string,
    public readonly currentVersionId: string | null,
    public readonly settings: Record<string, unknown>,
    public readonly insertedAt: string,
    public readonly updatedAt: string
  ) {}
}
```

Create `extralit-frontend/v2/domain/entities/schema/ColumnMeta.ts`:

```ts
// The out-of-band per-column overlay (parent spec §13). Free-form JSONB: `type` is the
// only key the UI interprets; unknown types fall back to the dtype default.
export interface ReviewOverlay {
  type?: string;
  [key: string]: unknown;
}

export class ColumnMeta {
  constructor(
    public readonly name: string,
    public readonly dtype: string,
    public readonly nullable: boolean,
    public readonly review: ReviewOverlay | null
  ) {}
}
```

Create `extralit-frontend/v2/domain/entities/schema/SchemaVersion.ts`:

```ts
import { type ColumnMeta } from "./ColumnMeta";

export class SchemaVersion {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly version: number,
    public readonly columnsCache: ColumnMeta[],
    public readonly reviewWidgets: Record<string, Record<string, unknown>>,
    public readonly insertedAt: string
  ) {}

  findColumn(name: string): ColumnMeta | undefined {
    return this.columnsCache.find((column) => column.name === name);
  }
}
```

Create `extralit-frontend/v2/domain/entities/question/Question.ts`:

```ts
export type QuestionType = "text" | "rating" | "label_selection" | "multi_label_selection" | "ranking" | "table";

export interface QuestionOption {
  value: string;
  text: string;
  description: string | null;
}

export class Question {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly name: string,
    public readonly title: string,
    public readonly description: string | null,
    public readonly type: QuestionType,
    public readonly columns: string[],
    public readonly settings: Record<string, unknown>,
    public readonly required: boolean
  ) {}

  get isLabelType(): boolean {
    return this.type === "label_selection" || this.type === "multi_label_selection";
  }

  // label_selection / multi_label_selection / ranking settings.options: {value, text, description}
  get options(): QuestionOption[] {
    const options = (this.settings.options as QuestionOption[] | undefined) ?? [];
    return options.map((o) => ({ value: o.value, text: o.text, description: o.description ?? null }));
  }

  // rating settings.options: {value: int}
  get ratingValues(): number[] {
    const options = (this.settings.options as { value: number }[] | undefined) ?? [];
    return options.map((o) => o.value);
  }
}
```

Create `extralit-frontend/v2/domain/entities/review/widget-mapping.ts`:

```ts
import { type ColumnMeta } from "../schema/ColumnMeta";

// Cell editors for table-question sub-columns and read-only context fields (spec §6.2/§6.3).
// Question-level widgets (§6.1) come straight from question.type — see ReviewCellInput.
export type CellEditor = "text" | "number" | "checkbox" | "date";

const KNOWN_EDITORS: CellEditor[] = ["text", "number", "checkbox", "date"];

export const dtypeDefaultEditor = (dtype: string): CellEditor => {
  if (dtype.startsWith("int") || dtype.startsWith("float")) return "number";
  if (dtype === "bool") return "checkbox";
  if (dtype.startsWith("datetime")) return "date";
  return "text"; // str and anything unknown
};

export const columnCellEditor = (column: ColumnMeta): CellEditor => {
  const hinted = column.review?.type;
  if (hinted && (KNOWN_EDITORS as string[]).includes(hinted)) return hinted as CellEditor;
  return dtypeDefaultEditor(column.dtype);
};

// Same precedence for non-question context fields; separate name so call sites read as §6.3.
export const contextRenderer = (column: ColumnMeta): CellEditor => columnCellEditor(column);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run v2/domain --reporter=verbose`
Expected: all PASS.

- [ ] **Step 5: Lint and commit**

```bash
cd extralit-frontend && npm run lint && npm run format
git add v2/domain
git commit -m "feat(v2-ui): schema/question domain entities + widget-selection mapping"
```

---

### Task 4: SchemaRepository + SchemasStorage + first use-cases + DI wiring

**Files:**
- Create: `extralit-frontend/v2/infrastructure/repositories/SchemaRepository.ts`
- Create: `extralit-frontend/v2/infrastructure/storage/SchemasStorage.ts`
- Create: `extralit-frontend/v2/domain/usecases/get-schemas-use-case.ts`
- Create: `extralit-frontend/v2/domain/usecases/get-schema-settings-use-case.ts`
- Create: `extralit-frontend/v2/di/di.ts`, `extralit-frontend/v2/di/index.ts`
- Modify: `extralit-frontend/plugins/3.di.ts`
- Test: `extralit-frontend/v2/infrastructure/repositories/SchemaRepository.test.ts`
- Test: `extralit-frontend/v2/domain/usecases/get-schemas-use-case.test.ts`

**Interfaces:**
- Consumes: Task 3 entities; Task 2 generated types; v1's `useAxiosExtension` (`v1/infrastructure/services/useAxiosExtension.ts`, allowed import) and `useStoreFor` (`v1/store/create.ts`, allowed import).
- Produces:
  - `class SchemaRepository { constructor(axios: AxiosInstance); getSchemas(workspaceId: string): Promise<Schema[]>; getSchema(schemaId: string): Promise<Schema>; getVersions(schemaId: string): Promise<SchemaVersion[]>; getQuestions(schemaId: string): Promise<Question[]> }`
  - `useSchemas()` storage composable: `{ ...store, saveSchemas(schemas: Schema[]): void }` over state class `Schemas { schemas: Schema[] }`
  - `class GetSchemasUseCase { constructor(SchemaRepository, useSchemas); execute(workspaceId: string): Promise<Schema[]> }`
  - `class GetSchemaSettingsUseCase { constructor(SchemaRepository); execute(schemaId: string): Promise<{ schema: Schema; versions: SchemaVersion[]; questions: Question[] }> }`
  - `loadV2DependencyContainer(nuxtApp)` from `~/v2/di` — every later task appends registrations to `v2/di/di.ts`.

- [ ] **Step 1: Write the failing tests**

Create `extralit-frontend/v2/infrastructure/repositories/SchemaRepository.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { SchemaRepository } from "./SchemaRepository";

const axiosMock = (getImpl: (url: string) => unknown) =>
  ({ get: vi.fn(async (url: string) => ({ data: getImpl(url) })) } as unknown as AxiosInstance);

const BACKEND_SCHEMA = {
  id: "s-1",
  name: "sample_size",
  status: "published",
  current_version_id: "v-1",
  settings: {},
  workspace_id: "w-1",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("SchemaRepository", () => {
  it("lists schemas for a workspace and maps to domain entities", async () => {
    const axios = axiosMock(() => ({ items: [BACKEND_SCHEMA] }));
    const repository = new SchemaRepository(axios);

    const schemas = await repository.getSchemas("w-1");

    expect(axios.get).toHaveBeenCalledWith("/v2/schemas", { params: { workspace_id: "w-1" } });
    expect(schemas[0].workspaceId).toBe("w-1");
    expect(schemas[0].currentVersionId).toBe("v-1");
  });

  it("maps versions including columns_cache to ColumnMeta", async () => {
    const axios = axiosMock(() => [
      {
        id: "v-1",
        schema_id: "s-1",
        version: 1,
        object_key: "k",
        object_version_id: null,
        etag: "e",
        checksum: "c",
        parent_version_id: null,
        columns_cache: [{ name: "title", dtype: "str", nullable: false, review: { type: "text" } }],
        review_widgets: {},
        inserted_at: "2026-01-01T00:00:00",
      },
    ]);
    const repository = new SchemaRepository(axios);

    const versions = await repository.getVersions("s-1");

    expect(axios.get).toHaveBeenCalledWith("/v2/schemas/s-1/versions");
    expect(versions[0].findColumn("title")?.review?.type).toBe("text");
  });

  it("maps questions preserving type, columns and settings", async () => {
    const axios = axiosMock(() => ({
      items: [
        {
          id: "q-1",
          schema_id: "s-1",
          name: "label",
          title: "Label",
          description: null,
          type: "label_selection",
          columns: ["label"],
          settings: { type: "label_selection", options: [{ value: "a", text: "A", description: null }] },
          required: true,
          inserted_at: "2026-01-01T00:00:00",
          updated_at: "2026-01-01T00:00:00",
        },
      ],
    }));
    const repository = new SchemaRepository(axios);

    const questions = await repository.getQuestions("s-1");

    expect(questions[0].type).toBe("label_selection");
    expect(questions[0].options).toEqual([{ value: "a", text: "A", description: null }]);
    expect(questions[0].required).toBe(true);
  });
});
```

Create `extralit-frontend/v2/domain/usecases/get-schemas-use-case.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { GetSchemasUseCase } from "./get-schemas-use-case";
import { Schema } from "../entities/schema/Schema";
import { useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";

const SCHEMA = new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "2026-01-01", "2026-01-01");

describe("GetSchemasUseCase", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("fetches schemas and saves them to storage", async () => {
    const repository = { getSchemas: vi.fn(async () => [SCHEMA]) };
    const useCase = new GetSchemasUseCase(repository as never, useSchemas);

    const result = await useCase.execute("w-1");

    expect(repository.getSchemas).toHaveBeenCalledWith("w-1");
    expect(result).toEqual([SCHEMA]);
    expect(useSchemas().get().schemas).toEqual([SCHEMA]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write repository, storage, use-cases, DI**

Create `extralit-frontend/v2/infrastructure/repositories/SchemaRepository.ts`:

```ts
import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { ColumnMeta, type ReviewOverlay } from "~/v2/domain/entities/schema/ColumnMeta";
import { SchemaVersion } from "~/v2/domain/entities/schema/SchemaVersion";
import { Question, type QuestionType } from "~/v2/domain/entities/question/Question";

type BackendSchema = components["schemas"]["SchemaRead"];
type BackendSchemas = components["schemas"]["Schemas"];
type BackendVersion = components["schemas"]["SchemaVersionRead"];
type BackendQuestions = components["schemas"]["Questions"];
type BackendQuestion = components["schemas"]["QuestionRead"];

const toSchema = (backend: BackendSchema): Schema =>
  new Schema(
    backend.id,
    backend.name,
    backend.status,
    backend.workspace_id,
    backend.current_version_id ?? null,
    (backend.settings ?? {}) as Record<string, unknown>,
    backend.inserted_at,
    backend.updated_at
  );

const toVersion = (backend: BackendVersion): SchemaVersion =>
  new SchemaVersion(
    backend.id,
    backend.schema_id,
    backend.version,
    ((backend.columns_cache ?? []) as { name: string; dtype: string; nullable: boolean; review?: ReviewOverlay | null }[]).map(
      (c) => new ColumnMeta(c.name, c.dtype, c.nullable, c.review ?? null)
    ),
    (backend.review_widgets ?? {}) as Record<string, Record<string, unknown>>,
    backend.inserted_at
  );

const toQuestion = (backend: BackendQuestion): Question =>
  new Question(
    backend.id,
    backend.schema_id,
    backend.name,
    backend.title,
    backend.description ?? null,
    backend.type as QuestionType,
    backend.columns,
    (backend.settings ?? {}) as Record<string, unknown>,
    backend.required
  );

export class SchemaRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getSchemas(workspaceId: string): Promise<Schema[]> {
    const { data } = await this.axios.get<BackendSchemas>("/v2/schemas", { params: { workspace_id: workspaceId } });
    return data.items.map(toSchema);
  }

  async getSchema(schemaId: string): Promise<Schema> {
    const { data } = await this.axios.get<BackendSchema>(`/v2/schemas/${schemaId}`);
    return toSchema(data);
  }

  async getVersions(schemaId: string): Promise<SchemaVersion[]> {
    const { data } = await this.axios.get<BackendVersion[]>(`/v2/schemas/${schemaId}/versions`);
    return data.map(toVersion);
  }

  async getQuestions(schemaId: string): Promise<Question[]> {
    const { data } = await this.axios.get<BackendQuestions>(`/v2/schemas/${schemaId}/questions`);
    return data.items.map(toQuestion);
  }
}
```

Note: if `npx nuxi typecheck` reports the generated `components["schemas"]` keys differ (e.g. FastAPI emits `Schemas` as `Schemas-Output`), read the actual key names from `v2/infrastructure/api/generated/v2-api.ts` and adjust the four `type Backend*` aliases — never hand-write the shapes.

Create `extralit-frontend/v2/infrastructure/storage/SchemasStorage.ts`:

```ts
import { useStoreFor } from "@/v1/store/create";
import { Schema } from "~/v2/domain/entities/schema/Schema";

// Class name is the Pinia store key — must stay unique vs every v1 useStoreFor class.
class Schemas {
  constructor(public readonly schemas: Schema[] = []) {}
}

interface ISchemasStorage {
  saveSchemas(schemas: Schema[]): void;
}

const useStoreForSchemas = useStoreFor<Schemas, ISchemasStorage>(Schemas);

export const useSchemas = () => {
  const store = useStoreForSchemas();

  const saveSchemas = (schemas: Schema[]) => {
    store.save(new Schemas(schemas));
  };

  return { ...store, saveSchemas };
};
```

Create `extralit-frontend/v2/domain/usecases/get-schemas-use-case.ts`:

```ts
import { Schema } from "../entities/schema/Schema";
import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { type useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";

export class GetSchemasUseCase {
  constructor(
    private readonly schemaRepository: SchemaRepository,
    private readonly schemasStorage: typeof useSchemas
  ) {}

  async execute(workspaceId: string): Promise<Schema[]> {
    const schemas = await this.schemaRepository.getSchemas(workspaceId);
    this.schemasStorage().saveSchemas(schemas);
    return schemas;
  }
}
```

Create `extralit-frontend/v2/domain/usecases/get-schema-settings-use-case.ts`:

```ts
import { Schema } from "../entities/schema/Schema";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import { Question } from "../entities/question/Question";
import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";

export interface SchemaSettings {
  schema: Schema;
  versions: SchemaVersion[];
  questions: Question[];
}

export class GetSchemaSettingsUseCase {
  constructor(private readonly schemaRepository: SchemaRepository) {}

  async execute(schemaId: string): Promise<SchemaSettings> {
    const [schema, versions, questions] = await Promise.all([
      this.schemaRepository.getSchema(schemaId),
      this.schemaRepository.getVersions(schemaId),
      this.schemaRepository.getQuestions(schemaId),
    ]);
    return { schema, versions, questions };
  }
}
```

Create `extralit-frontend/v2/di/di.ts`:

```ts
import type { AxiosInstance } from "axios";
import Container, { register } from "ts-injecty";

import { useAxiosExtension } from "@/v1/infrastructure/services/useAxiosExtension";

import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";

type NuxtAppLike = {
  $axios: AxiosInstance;
  $i18n?: { t: (key: string) => unknown };
};

// Same global ts-injecty container as v1 (registrations keyed by class name — v2 names
// are disjoint from v1's by the Global Constraints rule). Called after v1's loader.
export const loadV2DependencyContainer = (nuxtApp: NuxtAppLike) => {
  const t = (key: string) => String(nuxtApp.$i18n?.t(key) ?? key);
  const useAxios = useAxiosExtension(nuxtApp.$axios, t);

  const dependencies = [
    register(SchemaRepository).withDependency(useAxios).build(),
    register(GetSchemasUseCase).withDependencies(SchemaRepository, useSchemas).build(),
    register(GetSchemaSettingsUseCase).withDependency(SchemaRepository).build(),
  ];

  Container.register(dependencies);
};
```

Create `extralit-frontend/v2/di/index.ts`:

```ts
export * from "./di";
```

Modify `extralit-frontend/plugins/3.di.ts` (final file):

```ts
import { defineNuxtPlugin } from "#app";
import { loadDependencyContainer } from "~/v1/di";
import { loadV2DependencyContainer } from "~/v2/di";

// Ordered last (3.) so $auth (1.) and $axios (2.) are available when repositories resolve.
export default defineNuxtPlugin((nuxtApp) => {
  loadDependencyContainer(nuxtApp as never);
  loadV2DependencyContainer(nuxtApp as never);
});
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: all PASS. Also run the full suite once (`npm run test`) to prove the plugin change breaks nothing.

- [ ] **Step 5: Boot check and commit**

Run: `cd extralit-frontend && npm run dev` briefly (Ctrl-C after "Vite server ready") — the DI plugin must not throw at startup.

```bash
git add v2 plugins/3.di.ts
git commit -m "feat(v2-ui): v2 DI container, SchemaRepository, schemas storage and first use-cases"
```

---

### Task 5: Records domain + V2RecordRepository + record use-cases

**Files:**
- Create: `extralit-frontend/v2/domain/entities/record/V2Record.ts`
- Create: `extralit-frontend/v2/domain/entities/record/RecordsPage.ts`
- Create: `extralit-frontend/v2/domain/entities/search/SearchCriteria.ts`
- Create: `extralit-frontend/v2/infrastructure/repositories/V2RecordRepository.ts`
- Create: `extralit-frontend/v2/domain/usecases/get-schema-records-use-case.ts`
- Create: `extralit-frontend/v2/domain/usecases/search-records-use-case.ts`
- Create: `extralit-frontend/v2/domain/usecases/rebuild-schema-index-use-case.ts`
- Modify: `extralit-frontend/v2/di/di.ts` (add registrations)
- Test: `extralit-frontend/v2/domain/entities/search/SearchCriteria.test.ts`
- Test: `extralit-frontend/v2/infrastructure/repositories/V2RecordRepository.test.ts`

**Interfaces:**
- Consumes: Task 3 entities, Task 2 generated types, Task 4 DI file.
- Produces:
  - `type V2RecordStatus = "pending" | "completed" | "discarded"`; `class V2Record { id, schemaId, schemaVersionId, reference, externalId, fields: Record<string, unknown>, metadata, status: V2RecordStatus, insertedAt, updatedAt }`
  - `class RecordsPage { items: V2Record[]; total: number }` — `total` is documented approximate.
  - `class SearchCriteria { constructor(text?: string | null, filters?: RecordFilter[], offset?: number, limit?: number); toQueryBody() }` with `interface RecordFilter { column: string; op: "eq" | "in" | "ge" | "le"; value: unknown }`
  - `class V2RecordRepository { constructor(axios); getRecords(schemaId, options?: { offset?: number; limit?: number; status?: V2RecordStatus; reference?: string }): Promise<RecordsPage>; searchRecords(schemaId, criteria: SearchCriteria): Promise<RecordsPage>; rebuildIndex(schemaId): Promise<number> }`
  - Use-cases: `GetSchemaRecordsUseCase.execute(schemaId, options?) → RecordsPage`; `SearchRecordsUseCase.execute(schemaId, criteria) → RecordsPage`; `RebuildSchemaIndexUseCase.execute(schemaId) → number`.

- [ ] **Step 1: Write the failing tests**

Create `extralit-frontend/v2/domain/entities/search/SearchCriteria.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { SearchCriteria } from "./SearchCriteria";

describe("SearchCriteria serialization", () => {
  it("serializes text, filters, offset and limit to the RecordSearchQuery body", () => {
    const criteria = new SearchCriteria("malaria", [{ column: "status", op: "eq", value: "pending" }], 20, 10);

    expect(criteria.toQueryBody()).toEqual({
      text: "malaria",
      filters: [{ column: "status", op: "eq", value: "pending" }],
      offset: 20,
      limit: 10,
    });
  });

  it("omits empty text as null and defaults paging", () => {
    expect(new SearchCriteria("").toQueryBody()).toEqual({ text: null, filters: [], offset: 0, limit: 50 });
  });

  it("drops ge/le filters whose value is null (server silently matches nothing, §10.1-D)", () => {
    const criteria = new SearchCriteria(null, [
      { column: "score", op: "ge", value: null },
      { column: "score", op: "le", value: 5 },
    ]);

    expect(criteria.toQueryBody().filters).toEqual([{ column: "score", op: "le", value: 5 }]);
  });
});
```

Create `extralit-frontend/v2/infrastructure/repositories/V2RecordRepository.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { V2RecordRepository } from "./V2RecordRepository";
import { SearchCriteria } from "~/v2/domain/entities/search/SearchCriteria";

const BACKEND_RECORD = {
  id: "r-1",
  schema_id: "s-1",
  schema_version_id: "v-1",
  reference: "10.1000/j.x",
  external_id: null,
  fields: { title: "A study" },
  metadata: null,
  status: "pending",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("V2RecordRepository", () => {
  it("lists records with paging/reference params and maps the page", async () => {
    const axios = { get: vi.fn(async () => ({ data: { items: [BACKEND_RECORD], total: 12000 } })) } as unknown as AxiosInstance;
    const repository = new V2RecordRepository(axios);

    const page = await repository.getRecords("s-1", { offset: 0, limit: 25, reference: "10.1000/j.x" });

    expect((axios.get as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual([
      "/v2/schemas/s-1/records",
      { params: { offset: 0, limit: 25, reference: "10.1000/j.x" } },
    ]);
    expect(page.items[0].reference).toBe("10.1000/j.x");
    expect(page.total).toBe(12000);
  });

  it("posts search criteria to the :search custom verb", async () => {
    const axios = { post: vi.fn(async () => ({ data: { items: [], total: 0 } })) } as unknown as AxiosInstance;
    const repository = new V2RecordRepository(axios);

    await repository.searchRecords("s-1", new SearchCriteria("fts terms"));

    expect((axios.post as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual([
      "/v2/schemas/s-1/records:search",
      { text: "fts terms", filters: [], offset: 0, limit: 50 },
    ]);
  });

  it("returns the indexed count from :rebuild-index", async () => {
    const axios = { post: vi.fn(async () => ({ data: { indexed: 42 } })) } as unknown as AxiosInstance;
    const repository = new V2RecordRepository(axios);

    await expect(repository.rebuildIndex("s-1")).resolves.toBe(42);
    expect(axios.post).toHaveBeenCalledWith("/v2/schemas/s-1:rebuild-index");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: new tests FAIL (modules not found); Task 3–4 tests still pass.

- [ ] **Step 3: Write entities, repository, use-cases**

Create `extralit-frontend/v2/domain/entities/record/V2Record.ts`:

```ts
export type V2RecordStatus = "pending" | "completed" | "discarded";

export class V2Record {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly schemaVersionId: string,
    public readonly reference: string,
    public readonly externalId: string | null,
    public readonly fields: Record<string, unknown>,
    public readonly metadata: Record<string, unknown> | null,
    public readonly status: V2RecordStatus,
    // Naive ISO strings from the server — treat as UTC (spec §7 gotchas).
    public readonly insertedAt: string,
    public readonly updatedAt: string
  ) {}
}
```

Create `extralit-frontend/v2/domain/entities/record/RecordsPage.ts`:

```ts
import { type V2Record } from "./V2Record";

export class RecordsPage {
  constructor(
    public readonly items: V2Record[],
    // Approximate by contract (§10.1-D): stale Lance ids are skipped on hydration and FTS
    // totals saturate at 10,000 — pagination must not promise exact counts.
    public readonly total: number
  ) {}
}
```

Create `extralit-frontend/v2/domain/entities/search/SearchCriteria.ts`:

```ts
export type FilterOp = "eq" | "in" | "ge" | "le";

export interface RecordFilter {
  column: string;
  op: FilterOp;
  value: unknown;
}

export class SearchCriteria {
  constructor(
    public readonly text: string | null = null,
    public readonly filters: RecordFilter[] = [],
    public readonly offset: number = 0,
    public readonly limit: number = 50
  ) {}

  toQueryBody() {
    return {
      text: this.text || null,
      // ge/le with null silently matches nothing server-side — drop them here.
      filters: this.filters.filter((f) => !((f.op === "ge" || f.op === "le") && f.value === null)),
      offset: this.offset,
      limit: this.limit,
    };
  }
}
```

Create `extralit-frontend/v2/infrastructure/repositories/V2RecordRepository.ts`:

```ts
import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { V2Record, type V2RecordStatus } from "~/v2/domain/entities/record/V2Record";
import { RecordsPage } from "~/v2/domain/entities/record/RecordsPage";
import { SearchCriteria } from "~/v2/domain/entities/search/SearchCriteria";

type BackendRecord = components["schemas"]["RecordRead"];
type BackendRecords = components["schemas"]["Records"];

const toRecord = (backend: BackendRecord): V2Record =>
  new V2Record(
    backend.id,
    backend.schema_id,
    backend.schema_version_id,
    backend.reference,
    backend.external_id ?? null,
    (backend.fields ?? {}) as Record<string, unknown>,
    (backend.metadata ?? null) as Record<string, unknown> | null,
    backend.status as V2RecordStatus,
    backend.inserted_at,
    backend.updated_at
  );

const toPage = (backend: BackendRecords): RecordsPage => new RecordsPage(backend.items.map(toRecord), backend.total);

export interface GetRecordsOptions {
  offset?: number;
  limit?: number;
  status?: V2RecordStatus;
  reference?: string;
}

export class V2RecordRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getRecords(schemaId: string, options: GetRecordsOptions = {}): Promise<RecordsPage> {
    const { data } = await this.axios.get<BackendRecords>(`/v2/schemas/${schemaId}/records`, { params: options });
    return toPage(data);
  }

  async searchRecords(schemaId: string, criteria: SearchCriteria): Promise<RecordsPage> {
    const { data } = await this.axios.post<BackendRecords>(`/v2/schemas/${schemaId}/records:search`, criteria.toQueryBody());
    return toPage(data);
  }

  async rebuildIndex(schemaId: string): Promise<number> {
    const { data } = await this.axios.post<{ indexed: number }>(`/v2/schemas/${schemaId}:rebuild-index`);
    return data.indexed;
  }
}
```

Create the three use-cases:

`extralit-frontend/v2/domain/usecases/get-schema-records-use-case.ts`:

```ts
import { RecordsPage } from "../entities/record/RecordsPage";
import { V2RecordRepository, type GetRecordsOptions } from "~/v2/infrastructure/repositories/V2RecordRepository";

export class GetSchemaRecordsUseCase {
  constructor(private readonly recordRepository: V2RecordRepository) {}

  execute(schemaId: string, options: GetRecordsOptions = {}): Promise<RecordsPage> {
    return this.recordRepository.getRecords(schemaId, options);
  }
}
```

`extralit-frontend/v2/domain/usecases/search-records-use-case.ts`:

```ts
import { RecordsPage } from "../entities/record/RecordsPage";
import { SearchCriteria } from "../entities/search/SearchCriteria";
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";

export class SearchRecordsUseCase {
  constructor(private readonly recordRepository: V2RecordRepository) {}

  execute(schemaId: string, criteria: SearchCriteria): Promise<RecordsPage> {
    return this.recordRepository.searchRecords(schemaId, criteria);
  }
}
```

`extralit-frontend/v2/domain/usecases/rebuild-schema-index-use-case.ts`:

```ts
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";

export class RebuildSchemaIndexUseCase {
  constructor(private readonly recordRepository: V2RecordRepository) {}

  execute(schemaId: string): Promise<number> {
    return this.recordRepository.rebuildIndex(schemaId);
  }
}
```

Modify `extralit-frontend/v2/di/di.ts` — add imports and registrations inside `dependencies`:

```ts
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";
import { GetSchemaRecordsUseCase } from "~/v2/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v2/domain/usecases/search-records-use-case";
import { RebuildSchemaIndexUseCase } from "~/v2/domain/usecases/rebuild-schema-index-use-case";
```

```ts
    register(V2RecordRepository).withDependency(useAxios).build(),
    register(GetSchemaRecordsUseCase).withDependency(V2RecordRepository).build(),
    register(SearchRecordsUseCase).withDependency(V2RecordRepository).build(),
    register(RebuildSchemaIndexUseCase).withDependency(V2RecordRepository).build(),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add v2
git commit -m "feat(v2-ui): records domain, V2RecordRepository, search criteria and record use-cases"
```

---

### Task 6: `/schemas` list page + home nav sibling + base i18n keys

**Files:**
- Create: `extralit-frontend/pages/schemas/index.vue`
- Create: `extralit-frontend/pages/schemas/useSchemasViewModel.ts`
- Modify: `extralit-frontend/pages/index.vue` (nav-sibling tab)
- Modify: `extralit-frontend/translation/en.js` (add `schemas.*` keys)
- Test: `extralit-frontend/pages/schemas/index.test.ts`

**Interfaces:**
- Consumes: `GetSchemasUseCase` (Task 4) via `useResolve` from ts-injecty; `useWorkspaces()` + `Workspace` from v1 (documented exception); `useResolveMock` from `v1/di/__mocks__/useResolveMock` in tests.
- Produces: route `/schemas`; `useSchemasViewModel(): { schemas, isLoading, selectedWorkspace, loadSchemas }`.

Note: the Nuxt `pages:extend` hook already strips non-`.vue` co-located files from routes, so `useSchemasViewModel.ts` and `index.test.ts` are safe next to the page.

- [ ] **Step 1: Add i18n keys**

In `extralit-frontend/translation/en.js`, add a new top-level `schemas` family (alphabetical placement near existing top-level keys):

```js
  schemas: {
    title: "Schemas",
    empty: "No schemas in this workspace yet.",
    noWorkspace: "Select a workspace to view its schemas.",
    loadError: "Could not load schemas.",
    name: "Name",
    status: "Status",
    updatedAt: "Updated",
    records: "Records",
    searchPlaceholder: "Search records…",
    noResults: "No records match this search.",
    totalApproximate: "~{total} records",
    reference: "Reference",
    settings: "Settings",
    columns: "Columns",
    versions: "Versions",
    version: "Version",
    questions: "Questions",
    dtype: "Type",
    nullable: "Nullable",
    required: "Required",
    rebuildIndex: "Rebuild search index",
    rebuildIndexHint: "Recovers search after a failed sync. May take tens of seconds.",
    rebuildIndexDone: "Re-indexed {count} records",
  },
```

- [ ] **Step 2: Write the failing component test**

Create `extralit-frontend/pages/schemas/index.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import SchemasPage from "./index.vue";

const SCHEMA = new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "2026-01-01", "2026-01-01");

describe("schemas list page", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useWorkspaces().saveWorkspaces([new Workspace("w-1", "ws")]);
    useWorkspaces().saveSelectedWorkspace(new Workspace("w-1", "ws"));
  });

  it("loads schemas for the selected workspace and renders a row per schema", async () => {
    const execute = vi.fn(async () => [SCHEMA]);
    useResolveMock(GetSchemasUseCase, { execute });

    const wrapper = shallowMount(SchemasPage, { global: { stubs: { NuxtLink: { template: "<a><slot /></a>" } } } });
    await flushPromises();

    expect(execute).toHaveBeenCalledWith("w-1");
    expect(wrapper.text()).toContain("sample_size");
  });

  it("shows the empty state when the workspace has no schemas", async () => {
    useResolveMock(GetSchemasUseCase, { execute: vi.fn(async () => []) });

    const wrapper = shallowMount(SchemasPage, { global: { stubs: { NuxtLink: true } } });
    await flushPromises();

    expect(wrapper.text()).toContain("schemas.empty");
  });
});
```

(`$t` is mocked in `test/setup.ts` to return the key, so assertions target key names.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd extralit-frontend && npx vitest run pages/schemas --reporter=verbose`
Expected: FAIL — `./index.vue` not found.

- [ ] **Step 4: Write the view-model and page**

Create `extralit-frontend/pages/schemas/useSchemasViewModel.ts`:

```ts
import { computed, onBeforeMount, ref, watch } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemasUseCase } from "~/v2/domain/usecases/get-schemas-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
// Documented v1 exception: workspace selection survives Phase 6 (see plan Global Constraints).
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

export const useSchemasViewModel = () => {
  const getSchemasUseCase = useResolve(GetSchemasUseCase);
  const workspacesStore = useWorkspaces();

  const schemas = ref<Schema[]>([]);
  const isLoading = ref(false);
  const loadFailed = ref(false);

  const selectedWorkspace = computed(() => workspacesStore.get().selectedWorkspace);

  const loadSchemas = async () => {
    if (!selectedWorkspace.value) return;
    isLoading.value = true;
    loadFailed.value = false;
    try {
      schemas.value = await getSchemasUseCase.execute(selectedWorkspace.value.id);
    } catch {
      loadFailed.value = true; // AxiosErrorHandler already notified
    } finally {
      isLoading.value = false;
    }
  };

  onBeforeMount(loadSchemas);
  watch(selectedWorkspace, loadSchemas);

  return { schemas, isLoading, loadFailed, selectedWorkspace, loadSchemas };
};
```

Create `extralit-frontend/pages/schemas/index.vue`:

```vue
<template>
  <div class="schemas-page">
    <h1 class="schemas-page__title" v-text="$t('schemas.title')" />

    <p v-if="!selectedWorkspace" class="schemas-page__empty" v-text="$t('schemas.noWorkspace')" />
    <BaseLoading v-else-if="isLoading" />
    <p v-else-if="loadFailed" class="schemas-page__empty" v-text="$t('schemas.loadError')" />
    <p v-else-if="!schemas.length" class="schemas-page__empty" v-text="$t('schemas.empty')" />

    <table v-else class="schemas-page__table">
      <thead>
        <tr>
          <th v-text="$t('schemas.name')" />
          <th v-text="$t('schemas.status')" />
          <th v-text="$t('schemas.updatedAt')" />
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="schema in schemas" :key="schema.id">
          <td>
            <NuxtLink :to="`/schemas/${schema.id}`">{{ schema.name }}</NuxtLink>
          </td>
          <td>{{ schema.status }}</td>
          <td>{{ schema.updatedAt }}</td>
          <td>
            <NuxtLink :to="`/schemas/${schema.id}/settings`">{{ $t("schemas.settings") }}</NuxtLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script lang="ts">
import { useSchemasViewModel } from "./useSchemasViewModel";

export default {
  setup() {
    return useSchemasViewModel();
  },
};
</script>

<style lang="scss" scoped>
.schemas-page {
  padding: $base-space * 3;

  &__title {
    margin: 0 0 $base-space * 2;
  }

  &__empty {
    color: var(--fg-tertiary);
  }

  &__table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      text-align: left;
      padding: $base-space;
      border-bottom: 1px solid var(--bg-opacity-10);
    }
  }
}
</style>
```

- [ ] **Step 5: Add the nav sibling on the home page**

In `extralit-frontend/pages/index.vue`:

In `data()`, extend `tabs`:

```js
      tabs: [
        { id: "datasets", name: this.$t("home.datasets") },
        { id: "documents", name: this.$t("home.documents") },
        { id: "schemas", name: this.$t("schemas.title") },
      ],
```

In `methods.onTabChange`, navigate instead of switching for the schemas tab (final method):

```js
    onTabChange(tabId) {
      if (tabId === "schemas") {
        this.$router.push("/schemas");
        return;
      }
      const selectedTab = this.tabs.find((tab) => tab.id === tabId);
      if (selectedTab) {
        this.activeTab = selectedTab;
      }
    },
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run pages/schemas v2 --reporter=verbose && npm run test`
Expected: new tests PASS; full suite green (home page specs unaffected — they don't assert the tab count; if one does, update its expectation to include the new tab).

- [ ] **Step 7: Commit**

```bash
git add pages/schemas pages/index.vue translation/en.js
git commit -m "feat(v2-ui): /schemas list page with home nav sibling and schemas.* i18n"
```

---

### Task 7: `/schemas/[id]` records table + FTS search

**Files:**
- Create: `extralit-frontend/pages/schemas/[id]/index.vue`
- Create: `extralit-frontend/pages/schemas/[id]/useSchemaRecordsViewModel.ts`
- Create: `extralit-frontend/components/v2/schemas/V2RecordsTable.vue`
- Test: `extralit-frontend/pages/schemas/[id]/useSchemaRecordsViewModel.test.ts`

**Interfaces:**
- Consumes: `GetSchemaRecordsUseCase`, `SearchRecordsUseCase`, `GetSchemaSettingsUseCase` (Tasks 4–5), `SearchCriteria`, `RecordsPage`.
- Produces: route `/schemas/[id]`; `useSchemaRecordsViewModel(schemaId: string): { schema, columns, page, isLoading, searchText, statusFilter, currentOffset, pageSize, search, goToOffset, isApproximateTotal }`; component `V2RecordsTable` (props: `records: V2Record[]`, `columns: ColumnMeta[]`; renders `reference` link column + one column per ColumnMeta from `record.fields`).

Design notes locked in:
- Filter UI offers ONLY `status` (known enum) in this slice — arbitrary column filters invite the unknown-column 5xx (§10.1-D). Column filters come later once the UI derives them from `columns_cache`.
- Empty `searchText` + no filter → `GET /records` listing (exact total); otherwise `POST :search` (approximate total). `isApproximateTotal` = true on the search path; the template renders `schemas.totalApproximate` then.
- Search may miss just-written records (eventual consistency) — the empty state copy is neutral (`schemas.noResults`), never "0 records exist".

- [ ] **Step 1: Write the failing view-model test**

Create `extralit-frontend/pages/schemas/[id]/useSchemaRecordsViewModel.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemaRecordsUseCase } from "~/v2/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v2/domain/usecases/search-records-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RecordsPage } from "~/v2/domain/entities/record/RecordsPage";
import { V2Record } from "~/v2/domain/entities/record/V2Record";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { SchemaVersion } from "~/v2/domain/entities/schema/SchemaVersion";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { useSchemaRecordsViewModel } from "./useSchemaRecordsViewModel";

const RECORD = new V2Record("r-1", "s-1", "v-1", "10.1000/j.x", null, { title: "A study" }, null, "pending", "", "");
const SETTINGS = {
  schema: new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "", ""),
  versions: [new SchemaVersion("v-1", "s-1", 1, [new ColumnMeta("title", "str", false, null)], {}, "")],
  questions: [],
};

describe("useSchemaRecordsViewModel", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("lists via GET when there is no query, searches via :search when there is", async () => {
    const list = vi.fn(async () => new RecordsPage([RECORD], 1));
    const search = vi.fn(async () => new RecordsPage([RECORD], 1));
    useResolveMock(GetSchemaRecordsUseCase, { execute: list });
    useResolveMock(SearchRecordsUseCase, { execute: search });
    useResolveMock(GetSchemaSettingsUseCase, { execute: vi.fn(async () => SETTINGS) });

    const vm = useSchemaRecordsViewModel("s-1");
    await vm.search();
    expect(list).toHaveBeenCalledWith("s-1", { offset: 0, limit: 25 });
    expect(vm.isApproximateTotal.value).toBe(false);

    vm.searchText.value = "malaria";
    await vm.search();
    expect(search).toHaveBeenCalled();
    expect(search.mock.calls[0][1].toQueryBody().text).toBe("malaria");
    expect(vm.isApproximateTotal.value).toBe(true);
  });

  it("passes the status filter through the search path", async () => {
    const search = vi.fn(async () => new RecordsPage([], 0));
    useResolveMock(GetSchemaRecordsUseCase, { execute: vi.fn(async () => new RecordsPage([], 0)) });
    useResolveMock(SearchRecordsUseCase, { execute: search });
    useResolveMock(GetSchemaSettingsUseCase, { execute: vi.fn(async () => SETTINGS) });

    const vm = useSchemaRecordsViewModel("s-1");
    vm.statusFilter.value = "pending";
    await vm.search();

    expect(search.mock.calls[0][1].toQueryBody().filters).toEqual([{ column: "status", op: "eq", value: "pending" }]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-frontend && npx vitest run "pages/schemas/[id]" --reporter=verbose`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the view-model**

Create `extralit-frontend/pages/schemas/[id]/useSchemaRecordsViewModel.ts`:

```ts
import { computed, onBeforeMount, ref } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemaRecordsUseCase } from "~/v2/domain/usecases/get-schema-records-use-case";
import { SearchRecordsUseCase } from "~/v2/domain/usecases/search-records-use-case";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RecordsPage } from "~/v2/domain/entities/record/RecordsPage";
import { SearchCriteria, type RecordFilter } from "~/v2/domain/entities/search/SearchCriteria";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { type V2RecordStatus } from "~/v2/domain/entities/record/V2Record";

const PAGE_SIZE = 25;

export const useSchemaRecordsViewModel = (schemaId: string) => {
  const getRecordsUseCase = useResolve(GetSchemaRecordsUseCase);
  const searchRecordsUseCase = useResolve(SearchRecordsUseCase);
  const getSettingsUseCase = useResolve(GetSchemaSettingsUseCase);

  const schema = ref<Schema | null>(null);
  const columns = ref<ColumnMeta[]>([]);
  const page = ref<RecordsPage>(new RecordsPage([], 0));
  const isLoading = ref(false);
  const searchText = ref("");
  const statusFilter = ref<V2RecordStatus | "">("");
  const currentOffset = ref(0);

  const hasQuery = computed(() => Boolean(searchText.value.trim() || statusFilter.value));
  const isApproximateTotal = ref(false);

  const loadSettings = async () => {
    const settings = await getSettingsUseCase.execute(schemaId);
    schema.value = settings.schema;
    const currentVersion = settings.versions.find((v) => v.id === settings.schema.currentVersionId);
    columns.value = currentVersion?.columnsCache ?? [];
  };

  const search = async () => {
    isLoading.value = true;
    try {
      if (hasQuery.value) {
        const filters: RecordFilter[] = statusFilter.value
          ? [{ column: "status", op: "eq", value: statusFilter.value }]
          : [];
        const criteria = new SearchCriteria(searchText.value.trim() || null, filters, currentOffset.value, PAGE_SIZE);
        page.value = await searchRecordsUseCase.execute(schemaId, criteria);
        isApproximateTotal.value = true;
      } else {
        page.value = await getRecordsUseCase.execute(schemaId, { offset: currentOffset.value, limit: PAGE_SIZE });
        isApproximateTotal.value = false;
      }
    } finally {
      isLoading.value = false;
    }
  };

  const goToOffset = async (offset: number) => {
    currentOffset.value = Math.max(0, offset);
    await search();
  };

  onBeforeMount(async () => {
    await Promise.all([loadSettings(), search()]);
  });

  return {
    schema,
    columns,
    page,
    isLoading,
    searchText,
    statusFilter,
    currentOffset,
    pageSize: PAGE_SIZE,
    isApproximateTotal,
    search,
    goToOffset,
  };
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extralit-frontend && npx vitest run "pages/schemas/[id]" --reporter=verbose`
Expected: PASS.

- [ ] **Step 5: Write the table component and page**

Create `extralit-frontend/components/v2/schemas/V2RecordsTable.vue`:

```vue
<template>
  <table class="v2-records-table">
    <thead>
      <tr>
        <th v-text="$t('schemas.reference')" />
        <th v-for="column in columns" :key="column.name">{{ column.name }}</th>
        <th v-text="$t('schemas.status')" />
      </tr>
    </thead>
    <tbody>
      <tr v-for="record in records" :key="record.id">
        <td>
          <NuxtLink
            :to="`/references/${encodeURIComponent(record.reference)}?workspace_id=${workspaceId}`"
            :data-reference="record.reference"
          >
            {{ record.reference }}
          </NuxtLink>
        </td>
        <td v-for="column in columns" :key="column.name">{{ formatCell(record.fields[column.name]) }}</td>
        <td>{{ record.status }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script lang="ts">
import { type PropType } from "vue";
import { type V2Record } from "~/v2/domain/entities/record/V2Record";
import { type ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";

export default {
  props: {
    records: { type: Array as PropType<V2Record[]>, required: true },
    columns: { type: Array as PropType<ColumnMeta[]>, required: true },
    workspaceId: { type: String, required: true },
  },
  methods: {
    formatCell(value: unknown): string {
      if (value === null || value === undefined) return "—";
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
    },
  },
};
</script>

<style lang="scss" scoped>
.v2-records-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    text-align: left;
    padding: $base-space;
    border-bottom: 1px solid var(--bg-opacity-10);
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
```

Create `extralit-frontend/pages/schemas/[id]/index.vue`:

```vue
<template>
  <div class="schema-detail">
    <div class="schema-detail__header">
      <h1 class="schema-detail__title">{{ schema?.name }}</h1>
      <NuxtLink v-if="schema" :to="`/schemas/${schema.id}/settings`">{{ $t("schemas.settings") }}</NuxtLink>
    </div>

    <form class="schema-detail__search" @submit.prevent="onSearch">
      <input
        v-model="searchText"
        class="schema-detail__search-input"
        type="search"
        :placeholder="$t('schemas.searchPlaceholder')"
      />
      <select v-model="statusFilter" @change="onSearch">
        <option value="">{{ $t("schemas.status") }}</option>
        <option value="pending">pending</option>
        <option value="completed">completed</option>
        <option value="discarded">discarded</option>
      </select>
    </form>

    <BaseLoading v-if="isLoading" />
    <p v-else-if="!page.items.length" class="schema-detail__empty" v-text="$t('schemas.noResults')" />
    <template v-else>
      <p class="schema-detail__total">
        <template v-if="isApproximateTotal">{{ $t("schemas.totalApproximate", { total: page.total }) }}</template>
        <template v-else>{{ page.total }}</template>
      </p>
      <V2RecordsTable :records="page.items" :columns="columns" :workspace-id="schema?.workspaceId ?? ''" />
      <div class="schema-detail__pager">
        <button :disabled="currentOffset === 0" @click="goToOffset(currentOffset - pageSize)">‹</button>
        <!-- total is approximate: allow next whenever a full page came back -->
        <button :disabled="page.items.length < pageSize" @click="goToOffset(currentOffset + pageSize)">›</button>
      </div>
    </template>
  </div>
</template>

<script lang="ts">
import { useRoute } from "vue-router";
import { useSchemaRecordsViewModel } from "./useSchemaRecordsViewModel";

export default {
  setup() {
    const route = useRoute();
    const viewModel = useSchemaRecordsViewModel(String(route.params.id));

    const onSearch = async () => {
      viewModel.currentOffset.value = 0;
      await viewModel.search();
    };

    return { ...viewModel, onSearch };
  },
};
</script>

<style lang="scss" scoped>
.schema-detail {
  padding: $base-space * 3;

  &__header {
    display: flex;
    align-items: baseline;
    gap: $base-space * 2;
  }

  &__title {
    margin: 0 0 $base-space * 2;
  }

  &__search {
    display: flex;
    gap: $base-space;
    margin-bottom: $base-space * 2;
  }

  &__search-input {
    flex: 1;
    padding: $base-space;
  }

  &__total,
  &__empty {
    color: var(--fg-tertiary);
  }

  &__pager {
    display: flex;
    gap: $base-space;
    margin-top: $base-space * 2;
  }
}
</style>
```

- [ ] **Step 6: Run full suite and commit**

Run: `cd extralit-frontend && npm run test`
Expected: green.

```bash
git add "pages/schemas/[id]" components/v2/schemas
git commit -m "feat(v2-ui): schema detail page with records table, FTS search and status filter"
```

---

### Task 8: `/schemas/[id]/settings` read-only inspection + rebuild-index

**Files:**
- Create: `extralit-frontend/pages/schemas/[id]/settings.vue`
- Create: `extralit-frontend/pages/schemas/[id]/useSchemaSettingsViewModel.ts`
- Test: `extralit-frontend/pages/schemas/[id]/useSchemaSettingsViewModel.test.ts`

**Interfaces:**
- Consumes: `GetSchemaSettingsUseCase`, `RebuildSchemaIndexUseCase` (Tasks 4–5); `useNotifications` from `v1/infrastructure/services` (allowed import).
- Produces: route `/schemas/[id]/settings`; `useSchemaSettingsViewModel(schemaId): { settings, isLoading, isRebuilding, rebuildIndex }`.

- [ ] **Step 1: Write the failing test**

Create `extralit-frontend/pages/schemas/[id]/useSchemaSettingsViewModel.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetSchemaSettingsUseCase } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RebuildSchemaIndexUseCase } from "~/v2/domain/usecases/rebuild-schema-index-use-case";
import { Schema } from "~/v2/domain/entities/schema/Schema";
import { useSchemaSettingsViewModel } from "./useSchemaSettingsViewModel";

vi.mock("~/v1/infrastructure/services/useNotifications", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
// useTranslate calls useNuxtApp() — unavailable in the happy-dom env, so mock it too.
vi.mock("~/v1/infrastructure/services/useTranslate", () => ({
  useTranslate: () => ({ t: (key: string) => key, tc: (key: string) => key }),
}));

const SETTINGS = {
  schema: new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "", ""),
  versions: [],
  questions: [],
};

describe("useSchemaSettingsViewModel", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads schema settings on demand", async () => {
    const execute = vi.fn(async () => SETTINGS);
    useResolveMock(GetSchemaSettingsUseCase, { execute });
    useResolveMock(RebuildSchemaIndexUseCase, { execute: vi.fn() });

    const vm = useSchemaSettingsViewModel("s-1");
    await vm.load();

    expect(execute).toHaveBeenCalledWith("s-1");
    expect(vm.settings.value?.schema.name).toBe("sample_size");
  });

  it("rebuild flag toggles around the (possibly slow) rebuild call", async () => {
    useResolveMock(GetSchemaSettingsUseCase, { execute: vi.fn(async () => SETTINGS) });
    let resolveRebuild!: (n: number) => void;
    useResolveMock(RebuildSchemaIndexUseCase, {
      execute: vi.fn(() => new Promise<number>((resolve) => (resolveRebuild = resolve))),
    });

    const vm = useSchemaSettingsViewModel("s-1");
    const pending = vm.rebuildIndex();
    expect(vm.isRebuilding.value).toBe(true);

    resolveRebuild(42);
    await pending;
    expect(vm.isRebuilding.value).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-frontend && npx vitest run "pages/schemas/[id]/useSchemaSettingsViewModel" --reporter=verbose`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the view-model and page**

Create `extralit-frontend/pages/schemas/[id]/useSchemaSettingsViewModel.ts`:

```ts
import { onBeforeMount, ref } from "vue";
import { useResolve } from "ts-injecty";
import { GetSchemaSettingsUseCase, type SchemaSettings } from "~/v2/domain/usecases/get-schema-settings-use-case";
import { RebuildSchemaIndexUseCase } from "~/v2/domain/usecases/rebuild-schema-index-use-case";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";
import { useTranslate } from "~/v1/infrastructure/services/useTranslate";

export const useSchemaSettingsViewModel = (schemaId: string) => {
  const getSettingsUseCase = useResolve(GetSchemaSettingsUseCase);
  const rebuildIndexUseCase = useResolve(RebuildSchemaIndexUseCase);
  const notifications = useNotifications();
  const { t } = useTranslate();

  const settings = ref<SchemaSettings | null>(null);
  const isLoading = ref(false);
  const isRebuilding = ref(false);

  const load = async () => {
    isLoading.value = true;
    try {
      settings.value = await getSettingsUseCase.execute(schemaId);
    } finally {
      isLoading.value = false;
    }
  };

  const rebuildIndex = async () => {
    isRebuilding.value = true;
    try {
      const indexed = await rebuildIndexUseCase.execute(schemaId);
      notifications.notify({ message: t("schemas.rebuildIndexDone", { count: indexed }), type: "success" });
    } finally {
      isRebuilding.value = false;
    }
  };

  onBeforeMount(load);

  return { settings, isLoading, isRebuilding, load, rebuildIndex };
};
```

(Signatures verified against `v1/infrastructure/services/`: `notify({ message, type })` and `useTranslate()` → `{ t, tc }` with `t(key, values?)`.)

Create `extralit-frontend/pages/schemas/[id]/settings.vue`:

```vue
<template>
  <div class="schema-settings">
    <BaseLoading v-if="isLoading" />
    <template v-else-if="settings">
      <h1>{{ settings.schema.name }} — {{ $t("schemas.settings") }}</h1>

      <section>
        <h2 v-text="$t('schemas.columns')" />
        <table class="schema-settings__table">
          <thead>
            <tr>
              <th v-text="$t('schemas.name')" />
              <th v-text="$t('schemas.dtype')" />
              <th v-text="$t('schemas.nullable')" />
            </tr>
          </thead>
          <tbody>
            <tr v-for="column in currentColumns" :key="column.name">
              <td>{{ column.name }}</td>
              <td>{{ column.dtype }}</td>
              <td>{{ column.nullable ? "✓" : "" }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2 v-text="$t('schemas.versions')" />
        <ul>
          <li v-for="version in settings.versions" :key="version.id">
            {{ $t("schemas.version") }} {{ version.version }} — {{ version.insertedAt }}
            <template v-if="version.id === settings.schema.currentVersionId">(current)</template>
          </li>
        </ul>
      </section>

      <section>
        <h2 v-text="$t('schemas.questions')" />
        <table class="schema-settings__table">
          <thead>
            <tr>
              <th v-text="$t('schemas.name')" />
              <th v-text="$t('schemas.dtype')" />
              <th v-text="$t('schemas.columns')" />
              <th v-text="$t('schemas.required')" />
            </tr>
          </thead>
          <tbody>
            <tr v-for="question in settings.questions" :key="question.id">
              <td>{{ question.name }}</td>
              <td>{{ question.type }}</td>
              <td>{{ question.columns.join(", ") }}</td>
              <td>{{ question.required ? "✓" : "" }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <BaseButton class="primary" :disabled="isRebuilding" @on-click="rebuildIndex">
          {{ $t("schemas.rebuildIndex") }}
        </BaseButton>
        <p class="schema-settings__hint" v-text="$t('schemas.rebuildIndexHint')" />
      </section>
    </template>
  </div>
</template>

<script lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useSchemaSettingsViewModel } from "./useSchemaSettingsViewModel";

export default {
  setup() {
    const route = useRoute();
    const viewModel = useSchemaSettingsViewModel(String(route.params.id));

    const currentColumns = computed(() => {
      const current = viewModel.settings.value?.versions.find(
        (v) => v.id === viewModel.settings.value?.schema.currentVersionId
      );
      return current?.columnsCache ?? [];
    });

    return { ...viewModel, currentColumns };
  },
};
</script>

<style lang="scss" scoped>
.schema-settings {
  padding: $base-space * 3;

  section {
    margin-bottom: $base-space * 3;
  }

  &__table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      text-align: left;
      padding: $base-space;
      border-bottom: 1px solid var(--bg-opacity-10);
    }
  }

  &__hint {
    color: var(--fg-tertiary);
    font-size: 0.85em;
  }
}
</style>
```

(Check `components/base/base-button/BaseButton.vue` for its click emit name — if it emits native `click` rather than `on-click`, bind `@click`.)

- [ ] **Step 4: Run tests and commit**

Run: `cd extralit-frontend && npx vitest run "pages/schemas/[id]" --reporter=verbose && npm run test`
Expected: green.

```bash
git add "pages/schemas/[id]"
git commit -m "feat(v2-ui): read-only schema settings page with rebuild-index affordance"
```

---

### Task 9: Extract the four leaf widgets to `components/base/inputs/`

**Files (all moves via `git mv`, then re-point imports):**
- Move: `components/features/annotation/container/questions/form/shared-components/label-selection/LabelSelection.component.vue` → `components/base/inputs/label-selection/LabelSelection.component.vue`
- Move: `.../label-selection/useLabelSelectionViewModel.ts` → `components/base/inputs/label-selection/useLabelSelectionViewModel.ts`
- Move: `.../form/rating/RatingMonoSelection.component.vue` → `components/base/inputs/rating/RatingMonoSelection.component.vue`
- Move: `.../form/ranking/drag-and-drop-selection/DndSelection.component.vue` → `components/base/inputs/ranking/DndSelection.component.vue`
- Move: `.../form/ranking/ranking-adapter.js`, `ranking-adapter.test.js`, `ranking-fakes.js` → `components/base/inputs/ranking/`
- Move: `.../form/text-area/ContentEditableFeedbackTask.vue` → `components/base/inputs/text-area/ContentEditableFeedbackTask.vue`
- Modify: v1 wrappers that import moved files by path (`Ranking.component.vue` imports `ranking-adapter`; `TextAreaContents.vue` if it imports the leaf by relative path) — component-name references (`<LabelSelectionComponent>`, `<RatingMonoSelectionComponent>`, `<DndSelectionComponent>`, `<ContentEditableFeedbackTask>`) keep resolving via flat auto-import and need no change.

**Interfaces:**
- Consumes: nothing new.
- Produces: v1-free controlled leaves for Task 14. Their existing contracts (verbatim, do not change in this task):
  - `LabelSelectionComponent` — props `{ maxOptionsToShowBeforeCollapse?: number, modelValue: {id,text,value,description,isSelected}[], suggestion?: object, componentId: string, multiple?: boolean, suggestionFirst?: boolean, isFocused?: boolean, visibleShortcuts?: boolean }`, emits `update:modelValue | on-focus | on-selected`. Mutates `option.isSelected` in place.
  - `RatingMonoSelectionComponent` — props `{ modelValue: {id,value,isSelected}[], isFocused?, suggestion? }`, emits `update:modelValue | on-focus | on-selected`.
  - `DndSelectionComponent` — props `{ ranking: object (adapter output), suggestion?, isFocused? }`, emits `on-reorder | on-focus`. `adaptQuestionsToSlots({options})` takes `{id,text,value,description,rank?}[]`, returns `{slots, questions, getRanking(option), moveQuestionToSlot(q, slot)}`.
  - `ContentEditableFeedbackTask` — props `{ value: string, placeholder?, originalValue?, isFocused? }`, emits `change-text | on-change-focus | on-exit-edition-mode`.
  - The `suggestion` prop duck-type all three selection leaves consume: `{ isSuggested(value): boolean; getSuggestion(value): { agent, score?: { fixed: string } } | undefined }` — Task 11's `SuggestionHint` implements it.

- [ ] **Step 1: Baseline — run the full suite green**

Run: `cd extralit-frontend && npm run test`
Expected: green (this is the no-regression baseline for a pure move).

- [ ] **Step 2: Move the files**

```bash
cd extralit-frontend
FORM=components/features/annotation/container/questions/form
mkdir -p components/base/inputs/{label-selection,rating,ranking,text-area}
git mv $FORM/shared-components/label-selection/LabelSelection.component.vue components/base/inputs/label-selection/
git mv $FORM/shared-components/label-selection/useLabelSelectionViewModel.ts components/base/inputs/label-selection/
git mv $FORM/rating/RatingMonoSelection.component.vue components/base/inputs/rating/
git mv $FORM/ranking/drag-and-drop-selection/DndSelection.component.vue components/base/inputs/ranking/
git mv $FORM/ranking/ranking-adapter.js components/base/inputs/ranking/
git mv $FORM/ranking/ranking-adapter.test.js components/base/inputs/ranking/
git mv $FORM/ranking/ranking-fakes.js components/base/inputs/ranking/
git mv $FORM/text-area/ContentEditableFeedbackTask.vue components/base/inputs/text-area/
```

If `shared-components/label-selection/` or `drag-and-drop-selection/` still contain other files (e.g. `SearchLabelComponent`), check whether they are used only by the moved leaf (`grep -rn "SearchLabel" components/`); if so, move them alongside; if shared more widely, leave them (auto-import keeps resolving them by name).

- [ ] **Step 3: Re-point path imports**

```bash
cd extralit-frontend && grep -rn "ranking-adapter\|ContentEditableFeedbackTask\|useLabelSelectionViewModel\|RatingMonoSelection\|DndSelection\|LabelSelection.component" components/ pages/ v1/ --include="*.vue" --include="*.ts" --include="*.js" | grep -v "components/base/inputs"
```

For every hit that imports a moved file **by path** (component-name template references need nothing), update the path, e.g. in `components/features/annotation/container/questions/form/ranking/Ranking.component.vue`:

```js
import { adaptQuestionsToSlots } from "@/components/base/inputs/ranking/ranking-adapter";
```

and in the moved leaves themselves fix any now-broken relative imports (e.g. `LabelSelection.component.vue` importing `./useLabelSelectionViewModel` still works; an import like `../../...` to form-level helpers must become an absolute `@/components/...` path).

- [ ] **Step 4: Verify no regression**

Run: `cd extralit-frontend && npm run test && npm run lint`
Expected: full suite green, including the moved `ranking-adapter.test.js`. Then boot `npm run dev` briefly and open a v1 dataset annotation page if a backend is available (optional smoke; the vitest suite is the gate).

- [ ] **Step 5: Commit**

```bash
git add -A components
git commit -m "refactor(frontend): extract v1-free leaf inputs to components/base/inputs (reuse-don't-fork)"
```

---

### Task 10: Annotation + projection repositories, value wrapping, 422 normalizer

**Files:**
- Create: `extralit-frontend/v2/domain/entities/review/response-values.ts`
- Create: `extralit-frontend/v2/infrastructure/repositories/AnnotationRepository.ts`
- Create: `extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.ts`
- Create: `extralit-frontend/v2/infrastructure/repositories/apiErrors.ts`
- Modify: `extralit-frontend/v2/di/di.ts`
- Test: `extralit-frontend/v2/domain/entities/review/response-values.test.ts`
- Test: `extralit-frontend/v2/infrastructure/repositories/AnnotationRepository.test.ts`
- Test: `extralit-frontend/v2/infrastructure/repositories/apiErrors.test.ts`

**Interfaces:**
- Consumes: Task 2 generated types.
- Produces:
  - `wrapResponseValues(values: Record<string, unknown>): Record<string, { value: unknown }>` and `unwrapResponseValues(wrapped: Record<string, { value: unknown }> | null): Record<string, unknown>`
  - `interface RecordSuggestion { id, recordId, questionId, value: unknown, score: number | number[] | null, agent: string | null }`
  - `interface RecordResponse { id, recordId, userId, values: Record<string, unknown>, status: ResponseStatus }` with `type ResponseStatus = "draft" | "submitted" | "discarded"` (values are already **unwrapped** by the repository)
  - `class AnnotationRepository { getSuggestions(recordId): Promise<RecordSuggestion[]>; getResponse(recordId): Promise<RecordResponse | null>; upsertResponse(recordId, values: Record<string, unknown> | null, status: ResponseStatus): Promise<RecordResponse> }` — `upsertResponse` wraps values internally.
  - `interface ProjectionCellDto { questionName: string; value: unknown; source: "response" | "suggestion" | null }`; `interface ProjectionRecordDto { recordId, schemaId, reference, cells: ProjectionCellDto[] }`; `class ProjectionRepository { getProjection(reference, workspaceId): Promise<{ reference: string; records: ProjectionRecordDto[]; totalRecords: number }> }` — URL uses `encodeURIComponent(reference)`.
  - `normalizeV2ApiError(error: unknown): { status: number | null; messages: string[] }` — handles both 422 body shapes.

- [ ] **Step 1: Write the failing tests**

Create `extralit-frontend/v2/domain/entities/review/response-values.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { unwrapResponseValues, wrapResponseValues } from "./response-values";

describe("response value wrapping (spec §7 asymmetric-wrapping gotcha)", () => {
  it("wraps plain values into {question_name: {value}}", () => {
    expect(wrapResponseValues({ size: 12, label: "a" })).toEqual({
      size: { value: 12 },
      label: { value: "a" },
    });
  });

  it("unwraps the double-wrapped GET shape", () => {
    expect(unwrapResponseValues({ size: { value: 12 } })).toEqual({ size: 12 });
  });

  it("unwraps null (no response yet) to an empty object", () => {
    expect(unwrapResponseValues(null)).toEqual({});
  });

  it("round-trips", () => {
    const values = { a: [1, 2], b: { c: true } };
    expect(unwrapResponseValues(wrapResponseValues(values))).toEqual(values);
  });
});
```

Create `extralit-frontend/v2/infrastructure/repositories/AnnotationRepository.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { AnnotationRepository } from "./AnnotationRepository";

describe("AnnotationRepository", () => {
  it("returns null when GET responses returns literal null with 200 (never 404)", async () => {
    const axios = { get: vi.fn(async () => ({ data: null })) } as unknown as AxiosInstance;

    await expect(new AnnotationRepository(axios).getResponse("r-1")).resolves.toBeNull();
    expect(axios.get).toHaveBeenCalledWith("/v2/records/r-1/responses");
  });

  it("unwraps response values on read", async () => {
    const axios = {
      get: vi.fn(async () => ({
        data: { id: "resp-1", record_id: "r-1", user_id: "u-1", values: { size: { value: 12 } }, status: "draft" },
      })),
    } as unknown as AxiosInstance;

    const response = await new AnnotationRepository(axios).getResponse("r-1");

    expect(response?.values).toEqual({ size: 12 });
    expect(response?.status).toBe("draft");
  });

  it("re-wraps values on upsert PUT", async () => {
    const put = vi.fn(async () => ({
      data: { id: "resp-1", record_id: "r-1", user_id: "u-1", values: { size: { value: 12 } }, status: "submitted" },
    }));
    const axios = { put } as unknown as AxiosInstance;

    await new AnnotationRepository(axios).upsertResponse("r-1", { size: 12 }, "submitted");

    expect(put).toHaveBeenCalledWith("/v2/records/r-1/responses", {
      values: { size: { value: 12 } },
      status: "submitted",
    });
  });

  it("maps suggestions keeping question_id keying and provenance", async () => {
    const axios = {
      get: vi.fn(async () => ({
        data: { items: [{ id: "sug-1", record_id: "r-1", question_id: "q-1", value: 3, score: 0.9, agent: "gpt", type: null }] },
      })),
    } as unknown as AxiosInstance;

    const suggestions = await new AnnotationRepository(axios).getSuggestions("r-1");

    expect(suggestions[0]).toMatchObject({ questionId: "q-1", value: 3, score: 0.9, agent: "gpt" });
  });
});
```

Create `extralit-frontend/v2/infrastructure/repositories/apiErrors.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { normalizeV2ApiError } from "./apiErrors";

const axiosError = (status: number, data: unknown) => ({ isAxiosError: true, response: { status, data } });

describe("normalizeV2ApiError (two 422 body shapes, spec §7)", () => {
  it("handles the domain-error string shape", () => {
    const normalized = normalizeV2ApiError(axiosError(422, { detail: "missing value for required question: size" }));
    expect(normalized).toEqual({ status: 422, messages: ["missing value for required question: size"] });
  });

  it("handles the pydantic array shape", () => {
    const normalized = normalizeV2ApiError(
      axiosError(422, { detail: [{ loc: ["body", "values"], msg: "field required", type: "missing" }] })
    );
    expect(normalized).toEqual({ status: 422, messages: ["body.values: field required"] });
  });

  it("falls back for non-axios errors", () => {
    expect(normalizeV2ApiError(new Error("boom"))).toEqual({ status: null, messages: ["boom"] });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: new tests FAIL (modules not found).

- [ ] **Step 3: Write the modules**

Create `extralit-frontend/v2/domain/entities/review/response-values.ts`:

```ts
// The server stores and returns response values double-wrapped: {question_name: {"value": ...}}
// on BOTH PUT and GET, while projection cells are bare (spec §7 asymmetric-wrapping gotcha).
export const wrapResponseValues = (values: Record<string, unknown>): Record<string, { value: unknown }> =>
  Object.fromEntries(Object.entries(values).map(([name, value]) => [name, { value }]));

export const unwrapResponseValues = (
  wrapped: Record<string, { value: unknown }> | null | undefined
): Record<string, unknown> =>
  Object.fromEntries(Object.entries(wrapped ?? {}).map(([name, box]) => [name, box?.value]));
```

Create `extralit-frontend/v2/infrastructure/repositories/AnnotationRepository.ts`:

```ts
import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";
import { unwrapResponseValues, wrapResponseValues } from "~/v2/domain/entities/review/response-values";

type BackendSuggestions = components["schemas"]["Suggestions"];
type BackendResponse = components["schemas"]["ResponseRead"];

export type ResponseStatus = "draft" | "submitted" | "discarded";

export interface RecordSuggestion {
  id: string;
  recordId: string;
  questionId: string; // suggestions key by question ID, not name (spec §7 asymmetric keying)
  value: unknown;
  score: number | number[] | null;
  agent: string | null;
}

export interface RecordResponse {
  id: string;
  recordId: string;
  userId: string;
  values: Record<string, unknown>; // unwrapped; keyed by question NAME
  status: ResponseStatus;
}

const toResponse = (backend: BackendResponse): RecordResponse => ({
  id: backend.id,
  recordId: backend.record_id,
  userId: backend.user_id,
  values: unwrapResponseValues(backend.values as Record<string, { value: unknown }> | null),
  status: backend.status as ResponseStatus,
});

export class AnnotationRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getSuggestions(recordId: string): Promise<RecordSuggestion[]> {
    const { data } = await this.axios.get<BackendSuggestions>(`/v2/records/${recordId}/suggestions`);
    return data.items.map((s) => ({
      id: s.id,
      recordId: s.record_id,
      questionId: s.question_id,
      value: s.value,
      score: (s.score ?? null) as number | number[] | null,
      agent: s.agent ?? null,
    }));
  }

  async getResponse(recordId: string): Promise<RecordResponse | null> {
    // 200 with literal null body when the user has no response yet — never a 404.
    const { data } = await this.axios.get<BackendResponse | null>(`/v2/records/${recordId}/responses`);
    return data ? toResponse(data) : null;
  }

  async upsertResponse(
    recordId: string,
    values: Record<string, unknown> | null,
    status: ResponseStatus
  ): Promise<RecordResponse> {
    const body = { values: values ? wrapResponseValues(values) : null, status };
    const { data } = await this.axios.put<BackendResponse>(`/v2/records/${recordId}/responses`, body);
    return toResponse(data);
  }
}
```

Create `extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.ts`:

```ts
import type { AxiosInstance } from "axios";
import type { components } from "../api/generated/v2-api";

type BackendProjectionView = components["schemas"]["ProjectionView"];

export interface ProjectionCellDto {
  questionName: string;
  value: unknown;
  source: "response" | "suggestion" | null;
}

export interface ProjectionRecordDto {
  recordId: string;
  schemaId: string;
  reference: string;
  cells: ProjectionCellDto[];
}

export interface ProjectionViewDto {
  reference: string;
  records: ProjectionRecordDto[];
  totalRecords: number;
}

export class ProjectionRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getProjection(reference: string, workspaceId: string): Promise<ProjectionViewDto> {
    // DOIs contain slashes — always percent-encode the path param (spec §7 / seam B).
    const { data } = await this.axios.get<BackendProjectionView>(
      `/v2/projection/references/${encodeURIComponent(reference)}`,
      { params: { workspace_id: workspaceId } }
    );
    return {
      reference: data.reference,
      totalRecords: data.total_records,
      records: data.records.map((r) => ({
        recordId: r.record_id,
        schemaId: r.schema_id,
        reference: r.reference,
        cells: r.cells.map((c) => ({
          questionName: c.question_name,
          value: c.value ?? null,
          source: (c.source ?? null) as "response" | "suggestion" | null,
        })),
      })),
    };
  }
}
```

Create `extralit-frontend/v2/infrastructure/repositories/apiErrors.ts`:

```ts
export interface V2ApiError {
  status: number | null;
  messages: string[];
}

interface PydanticDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// v2 endpoints return two 422 body shapes (spec §7): domain errors {"detail": "<string>"}
// and pydantic request errors {"detail": [{loc, msg, type}]}. Normalize both.
export const normalizeV2ApiError = (error: unknown): V2ApiError => {
  const maybeAxios = error as { isAxiosError?: boolean; response?: { status: number; data?: { detail?: unknown } } };

  if (maybeAxios?.isAxiosError && maybeAxios.response) {
    const { status, data } = maybeAxios.response;
    const detail = data?.detail;

    if (typeof detail === "string") return { status, messages: [detail] };
    if (Array.isArray(detail)) {
      return {
        status,
        messages: (detail as PydanticDetail[]).map((d) => `${(d.loc ?? []).join(".")}: ${d.msg}`),
      };
    }
    return { status, messages: [`Request failed with status ${status}`] };
  }

  return { status: null, messages: [error instanceof Error ? error.message : String(error)] };
};
```

Modify `extralit-frontend/v2/di/di.ts` — add imports and registrations:

```ts
import { AnnotationRepository } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { ProjectionRepository } from "~/v2/infrastructure/repositories/ProjectionRepository";
```

```ts
    register(AnnotationRepository).withDependency(useAxios).build(),
    register(ProjectionRepository).withDependency(useAxios).build(),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add v2
git commit -m "feat(v2-ui): annotation/projection repositories, value re-wrapping and 422 normalizer"
```

---

### Task 11: `ReferenceReview` domain, assembly use-case, review storage

**Files:**
- Create: `extralit-frontend/v2/domain/entities/review/ReferenceReview.ts`
- Create: `extralit-frontend/v2/domain/entities/review/SuggestionHint.ts`
- Create: `extralit-frontend/v2/domain/usecases/get-reference-review-use-case.ts`
- Create: `extralit-frontend/v2/infrastructure/storage/ReferenceReviewsStorage.ts`
- Modify: `extralit-frontend/v2/di/di.ts`
- Test: `extralit-frontend/v2/domain/usecases/get-reference-review-use-case.test.ts`
- Test: `extralit-frontend/v2/domain/entities/review/SuggestionHint.test.ts`

**Interfaces:**
- Consumes: Tasks 3, 4, 5, 10 (SchemaRepository, V2RecordRepository, ProjectionRepository, AnnotationRepository, entities).
- Produces:
  - `interface Provenance { agent: string | null; score: number | null; suggestedValue: unknown }` (score flattened: first element when the server sends a list)
  - `class ReviewCell { question: Question; value: unknown; source: "response" | "suggestion" | null; provenance: Provenance | null; notApplicable: boolean }`
  - `interface ContextField { column: ColumnMeta; value: unknown }`
  - `interface OrphanedValue { name: string; value: unknown }`
  - `class ReviewRecord { recordId, schemaId, schemaName, cells: ReviewCell[], contextFields: ContextField[], orphanedValues: OrphanedValue[], draft: RecordResponse | null, columnsCache: ColumnMeta[] = []; initialValues(): Record<string, unknown> }`
  - `class ReferenceReview { reference: string; records: ReviewRecord[]; totalRecords: number }`
  - `class SuggestionHint { constructor(suggestedValue: unknown, agent: string | null, score: number | null, multiple: boolean); isSuggested(v): boolean; getSuggestion(v): { agent, score?: { fixed: string } } | undefined }` — implements the leaf-widget `suggestion` duck-type (Task 9).
  - `class GetReferenceReviewUseCase { execute(reference: string, workspaceId: string): Promise<ReferenceReview> }` — parallel fetches, saves to storage.
  - `useReferenceReviews()` storage: `{ ...store, saveReview(review: ReferenceReview): void, findByReference(reference: string): ReferenceReview | undefined }` — keyed by reference, NOT by route, so Phase 5's Queue UI can drive it.

- [ ] **Step 1: Write the failing tests**

Create `extralit-frontend/v2/domain/entities/review/SuggestionHint.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { SuggestionHint } from "./SuggestionHint";

describe("SuggestionHint (leaf-widget suggestion duck-type)", () => {
  it("matches scalar values for single-select widgets", () => {
    const hint = new SuggestionHint("malaria", "gpt-4", 0.87, false);

    expect(hint.isSuggested("malaria")).toBe(true);
    expect(hint.isSuggested("dengue")).toBe(false);
    expect(hint.getSuggestion("malaria")).toEqual({ agent: "gpt-4", score: { fixed: "0.9" } });
  });

  it("matches membership for multi-select widgets", () => {
    const hint = new SuggestionHint(["a", "b"], null, null, true);

    expect(hint.isSuggested("a")).toBe(true);
    expect(hint.isSuggested("c")).toBe(false);
    expect(hint.getSuggestion("a")).toEqual({ agent: null, score: undefined });
  });
});
```

Create `extralit-frontend/v2/domain/usecases/get-reference-review-use-case.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { GetReferenceReviewUseCase } from "./get-reference-review-use-case";
import { Question } from "../entities/question/Question";
import { Schema } from "../entities/schema/Schema";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import { ColumnMeta } from "../entities/schema/ColumnMeta";
import { V2Record } from "../entities/record/V2Record";
import { RecordsPage } from "../entities/record/RecordsPage";
import { useReferenceReviews } from "~/v2/infrastructure/storage/ReferenceReviewsStorage";

const REFERENCE = "10.1000/j.x";
const WORKSPACE = "w-1";

const sizeQuestion = new Question("q-size", "s-1", "size", "Sample size", null, "text", ["size"], {}, true);
const record = new V2Record("r-1", "s-1", "v-1", REFERENCE, null, { size: "12", country: "KE" }, null, "pending", "", "");

const projectionRepository = {
  getProjection: vi.fn(async () => ({
    reference: REFERENCE,
    totalRecords: 1,
    records: [
      {
        recordId: "r-1",
        schemaId: "s-1",
        reference: REFERENCE,
        cells: [{ questionName: "size", value: "12", source: "suggestion" as const }],
      },
    ],
  })),
};

const schemaRepository = {
  getSchema: vi.fn(async () => new Schema("s-1", "sample_size", "published", WORKSPACE, "v-1", {}, "", "")),
  getQuestions: vi.fn(async () => [sizeQuestion]),
  getVersions: vi.fn(async () => [
    new SchemaVersion(
      "v-1",
      "s-1",
      1,
      [new ColumnMeta("size", "str", false, null), new ColumnMeta("country", "str", true, null)],
      {},
      ""
    ),
  ]),
};

const recordRepository = { getRecords: vi.fn(async () => new RecordsPage([record], 1)) };

const annotationRepository = {
  getSuggestions: vi.fn(async () => [
    { id: "sug-1", recordId: "r-1", questionId: "q-size", value: "12", score: 0.9, agent: "gpt" },
  ]),
  getResponse: vi.fn(async () => null),
};

const makeUseCase = () =>
  new GetReferenceReviewUseCase(
    projectionRepository as never,
    schemaRepository as never,
    recordRepository as never,
    annotationRepository as never,
    useReferenceReviews
  );

describe("GetReferenceReviewUseCase", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("joins suggestion provenance to cells through the name↔id question map", async () => {
    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    const cell = review.records[0].cells.find((c) => c.question.name === "size")!;
    expect(cell.source).toBe("suggestion");
    expect(cell.provenance).toEqual({ agent: "gpt", score: 0.9, suggestedValue: "12" });
  });

  it("exposes non-question columns as read-only context fields", async () => {
    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].contextFields).toEqual([
      { column: expect.objectContaining({ name: "country" }), value: "KE" },
    ]);
  });

  it("marks a question not-applicable when its column is missing from the pinned version cache", async () => {
    schemaRepository.getQuestions.mockResolvedValueOnce([
      sizeQuestion,
      new Question("q-new", "s-1", "added_later", "Added later", null, "text", ["added_later"], {}, false),
    ]);

    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].cells.find((c) => c.question.name === "added_later")?.notApplicable).toBe(true);
  });

  it("collects response values orphaned by deleted questions and keeps a draft for prefill", async () => {
    annotationRepository.getResponse.mockResolvedValueOnce({
      id: "resp-1",
      recordId: "r-1",
      userId: "u-1",
      values: { size: "13", ghost_question: "zzz" },
      status: "draft",
    });

    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);
    const reviewRecord = review.records[0];

    expect(reviewRecord.orphanedValues).toEqual([{ name: "ghost_question", value: "zzz" }]);
    expect(reviewRecord.draft?.status).toBe("draft");
    // draft wins over the projection cell for prefill; orphans are excluded
    expect(reviewRecord.initialValues()).toEqual({ size: "13" });
  });

  it("prefills from the projection cell when there is no draft, and saves to storage by reference", async () => {
    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].initialValues()).toEqual({ size: "12" });
    expect(useReferenceReviews().findByReference(REFERENCE)).toBe(review);
  });

  it("ignores a submitted response for prefill (projection already reflects it)", async () => {
    annotationRepository.getResponse.mockResolvedValueOnce({
      id: "resp-1",
      recordId: "r-1",
      userId: "u-1",
      values: { size: "12" },
      status: "submitted",
    });

    const review = await makeUseCase().execute(REFERENCE, WORKSPACE);

    expect(review.records[0].draft).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: new tests FAIL.

- [ ] **Step 3: Write entity, hint, storage, use-case**

Create `extralit-frontend/v2/domain/entities/review/ReferenceReview.ts`:

```ts
import { Question } from "../question/Question";
import { type ColumnMeta } from "../schema/ColumnMeta";
import { type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";

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

export interface ContextField {
  column: ColumnMeta;
  value: unknown;
}

// Response values keyed by a name no current question owns (deleted/recreated question,
// spec §10.1-E): surfaced read-only, never re-submitted (server would 422 them).
export interface OrphanedValue {
  name: string;
  value: unknown;
}

export class ReviewRecord {
  constructor(
    public readonly recordId: string,
    public readonly schemaId: string,
    public readonly schemaName: string,
    public readonly cells: ReviewCell[],
    public readonly contextFields: ContextField[],
    public readonly orphanedValues: OrphanedValue[],
    public readonly draft: RecordResponse | null, // status === "draft" only
    // Pinned version's columns_cache — table-question sub-columns derive editors from it.
    public readonly columnsCache: ColumnMeta[] = []
  ) {}

  initialValues(): Record<string, unknown> {
    const values: Record<string, unknown> = {};
    for (const cell of this.cells) {
      if (cell.notApplicable) continue;
      const draftValue = this.draft?.values[cell.question.name];
      const value = draftValue !== undefined ? draftValue : cell.value;
      if (value !== null && value !== undefined) values[cell.question.name] = value;
    }
    return values;
  }
}

export class ReferenceReview {
  constructor(
    public readonly reference: string,
    public readonly records: ReviewRecord[],
    public readonly totalRecords: number
  ) {}
}
```

Create `extralit-frontend/v2/domain/entities/review/SuggestionHint.ts`:

```ts
// Implements the duck-type the extracted leaf widgets consume as their `suggestion` prop:
// isSuggested(value) / getSuggestion(value) -> { agent, score?: { fixed } } (see Task 9 contract).
export class SuggestionHint {
  constructor(
    private readonly suggestedValue: unknown,
    private readonly agent: string | null,
    private readonly score: number | null,
    private readonly multiple: boolean
  ) {}

  isSuggested(value: unknown): boolean {
    if (this.multiple && Array.isArray(this.suggestedValue)) {
      return (this.suggestedValue as unknown[]).includes(value);
    }
    return this.suggestedValue === value;
  }

  getSuggestion(value: unknown): { agent: string | null; score?: { fixed: string } } | undefined {
    if (!this.isSuggested(value)) return undefined;
    return { agent: this.agent, score: this.score != null ? { fixed: this.score.toFixed(1) } : undefined };
  }
}
```

Create `extralit-frontend/v2/infrastructure/storage/ReferenceReviewsStorage.ts`:

```ts
import { useStoreFor } from "@/v1/store/create";
import { ReferenceReview } from "~/v2/domain/entities/review/ReferenceReview";

// Keyed by reference, not by route, so Phase 5's Queue UI can drive the same store
// with references from GET /queues/{id}/next (spec §7).
class ReferenceReviews {
  constructor(public readonly byReference: Record<string, ReferenceReview> = {}) {}
}

interface IReferenceReviewsStorage {
  saveReview(review: ReferenceReview): void;
  findByReference(reference: string): ReferenceReview | undefined;
}

const useStoreForReferenceReviews = useStoreFor<ReferenceReviews, IReferenceReviewsStorage>(ReferenceReviews);

export const useReferenceReviews = () => {
  const store = useStoreForReferenceReviews();

  const saveReview = (review: ReferenceReview) => {
    store.save(new ReferenceReviews({ ...store.get().byReference, [review.reference]: review }));
  };

  const findByReference = (reference: string): ReferenceReview | undefined => store.get().byReference[reference];

  return { ...store, saveReview, findByReference };
};
```

Create `extralit-frontend/v2/domain/usecases/get-reference-review-use-case.ts`:

```ts
import { Question } from "../entities/question/Question";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import {
  type ContextField,
  type OrphanedValue,
  type Provenance,
  ReferenceReview,
  ReviewCell,
  ReviewRecord,
} from "../entities/review/ReferenceReview";
import { SchemaRepository } from "~/v2/infrastructure/repositories/SchemaRepository";
import { V2RecordRepository } from "~/v2/infrastructure/repositories/V2RecordRepository";
import { ProjectionRepository, type ProjectionRecordDto } from "~/v2/infrastructure/repositories/ProjectionRepository";
import { AnnotationRepository, type RecordSuggestion } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { type useReferenceReviews } from "~/v2/infrastructure/storage/ReferenceReviewsStorage";

interface SchemaContext {
  schemaName: string;
  questions: Question[];
  questionsById: Map<string, Question>;
  questionsByName: Map<string, Question>;
  versionsById: Map<string, SchemaVersion>;
}

export class GetReferenceReviewUseCase {
  constructor(
    private readonly projectionRepository: ProjectionRepository,
    private readonly schemaRepository: SchemaRepository,
    private readonly recordRepository: V2RecordRepository,
    private readonly annotationRepository: AnnotationRepository,
    private readonly reviewsStorage: typeof useReferenceReviews
  ) {}

  async execute(reference: string, workspaceId: string): Promise<ReferenceReview> {
    const projection = await this.projectionRepository.getProjection(reference, workspaceId);

    const schemaIds = [...new Set(projection.records.map((r) => r.schemaId))];
    const contexts = new Map<string, SchemaContext>();
    const recordsBySchema = new Map<string, Map<string, Record<string, unknown>>>();
    const versionByRecord = new Map<string, string>();

    await Promise.all(
      schemaIds.map(async (schemaId) => {
        const [schema, questions, versions, page] = await Promise.all([
          this.schemaRepository.getSchema(schemaId),
          this.schemaRepository.getQuestions(schemaId),
          this.schemaRepository.getVersions(schemaId),
          this.recordRepository.getRecords(schemaId, { reference }),
        ]);
        contexts.set(schemaId, {
          schemaName: schema.name,
          questions,
          // The name↔id join: projection cells + response values key by NAME,
          // suggestions key by ID (spec §7). Getting this wrong detaches provenance.
          questionsById: new Map(questions.map((q) => [q.id, q])),
          questionsByName: new Map(questions.map((q) => [q.name, q])),
          versionsById: new Map(versions.map((v) => [v.id, v])),
        });
        recordsBySchema.set(schemaId, new Map(page.items.map((r) => [r.id, r.fields])));
        page.items.forEach((r) => versionByRecord.set(r.id, r.schemaVersionId));
      })
    );

    const reviewRecords = await Promise.all(
      projection.records.map((projected) => this.assembleRecord(projected, contexts, recordsBySchema, versionByRecord))
    );

    const review = new ReferenceReview(reference, reviewRecords, projection.totalRecords);
    this.reviewsStorage().saveReview(review);
    return review;
  }

  private async assembleRecord(
    projected: ProjectionRecordDto,
    contexts: Map<string, SchemaContext>,
    recordsBySchema: Map<string, Map<string, Record<string, unknown>>>,
    versionByRecord: Map<string, string>
  ): Promise<ReviewRecord> {
    const context = contexts.get(projected.schemaId)!;
    const fields = recordsBySchema.get(projected.schemaId)?.get(projected.recordId) ?? {};
    const pinnedVersion = context.versionsById.get(versionByRecord.get(projected.recordId) ?? "");

    const [suggestions, response] = await Promise.all([
      this.annotationRepository.getSuggestions(projected.recordId),
      this.annotationRepository.getResponse(projected.recordId),
    ]);
    const suggestionsByQuestionId = new Map<string, RecordSuggestion>(suggestions.map((s) => [s.questionId, s]));
    const cellsByName = new Map(projected.cells.map((c) => [c.questionName, c]));

    const cells = context.questions.map((question) => {
      const cell = cellsByName.get(question.name);
      const suggestion = suggestionsByQuestionId.get(question.id);
      const provenance: Provenance | null = suggestion
        ? {
            agent: suggestion.agent,
            score: Array.isArray(suggestion.score) ? (suggestion.score[0] ?? null) : suggestion.score,
            suggestedValue: suggestion.value,
          }
        : null;
      // Old-version tolerance (§17.3): every bound column must exist in the pinned cache.
      const notApplicable =
        pinnedVersion !== undefined && question.columns.some((c) => pinnedVersion.findColumn(c) === undefined);

      return new ReviewCell(question, cell?.value ?? null, cell?.source ?? null, provenance, notApplicable);
    });

    const questionColumns = new Set(context.questions.flatMap((q) => q.columns));
    const contextFields: ContextField[] = (pinnedVersion?.columnsCache ?? [])
      .filter((column) => !questionColumns.has(column.name))
      .map((column) => ({ column, value: fields[column.name] ?? null }));

    const orphanedValues: OrphanedValue[] = Object.entries(response?.values ?? {})
      .filter(([name]) => !context.questionsByName.has(name))
      .map(([name, value]) => ({ name, value }));

    const draft = response?.status === "draft" ? response : null;

    return new ReviewRecord(
      projected.recordId,
      projected.schemaId,
      context.schemaName,
      cells,
      contextFields,
      orphanedValues,
      draft,
      pinnedVersion?.columnsCache ?? []
    );
  }
}
```

Modify `extralit-frontend/v2/di/di.ts` — add:

```ts
import { GetReferenceReviewUseCase } from "~/v2/domain/usecases/get-reference-review-use-case";
import { useReferenceReviews } from "~/v2/infrastructure/storage/ReferenceReviewsStorage";
```

```ts
    register(GetReferenceReviewUseCase)
      .withDependencies(ProjectionRepository, SchemaRepository, V2RecordRepository, AnnotationRepository, useReferenceReviews)
      .build(),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add v2
git commit -m "feat(v2-ui): ReferenceReview assembly with name-id join, drafts, orphans and version tolerance"
```

---

### Task 12: Submit / save-draft / discard use-cases

**Files:**
- Create: `extralit-frontend/v2/domain/usecases/submit-reference-review-use-case.ts`
- Create: `extralit-frontend/v2/domain/usecases/save-review-draft-use-case.ts`
- Create: `extralit-frontend/v2/domain/usecases/discard-review-use-case.ts`
- Modify: `extralit-frontend/v2/di/di.ts`
- Test: `extralit-frontend/v2/domain/usecases/submit-reference-review-use-case.test.ts`

**Interfaces:**
- Consumes: `AnnotationRepository` (Task 10), `normalizeV2ApiError` (Task 10).
- Produces (all consumed by Task 14's form → Task 15's page):
  - `class SubmitReferenceReviewUseCase { execute(recordId: string, values: Record<string, unknown>): Promise<RecordResponse> }` — status `submitted`; on failure throws `ReviewSubmitError { messages: string[] }`.
  - `class SaveReviewDraftUseCase { execute(recordId, values): Promise<RecordResponse> }` — status `draft`.
  - `class DiscardReviewUseCase { execute(recordId: string): Promise<RecordResponse> }` — status `discarded`, `values: null`.
  - `class ReviewSubmitError extends Error { messages: string[]; status: number | null }` (exported from the submit use-case file).

- [ ] **Step 1: Write the failing test**

Create `extralit-frontend/v2/domain/usecases/submit-reference-review-use-case.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { ReviewSubmitError, SubmitReferenceReviewUseCase } from "./submit-reference-review-use-case";
import { SaveReviewDraftUseCase } from "./save-review-draft-use-case";
import { DiscardReviewUseCase } from "./discard-review-use-case";

describe("review response use-cases", () => {
  it("submits with status=submitted", async () => {
    const upsertResponse = vi.fn(async () => ({ id: "resp", status: "submitted" }));
    await new SubmitReferenceReviewUseCase({ upsertResponse } as never).execute("r-1", { size: 12 });

    expect(upsertResponse).toHaveBeenCalledWith("r-1", { size: 12 }, "submitted");
  });

  it("normalizes both 422 shapes into ReviewSubmitError", async () => {
    const upsertResponse = vi.fn(async () => {
      throw { isAxiosError: true, response: { status: 422, data: { detail: "missing value for required question" } } };
    });

    const attempt = new SubmitReferenceReviewUseCase({ upsertResponse } as never).execute("r-1", {});

    await expect(attempt).rejects.toBeInstanceOf(ReviewSubmitError);
    await expect(attempt).rejects.toMatchObject({ messages: ["missing value for required question"], status: 422 });
  });

  it("saves drafts with status=draft", async () => {
    const upsertResponse = vi.fn(async () => ({ id: "resp", status: "draft" }));
    await new SaveReviewDraftUseCase({ upsertResponse } as never).execute("r-1", { size: 12 });

    expect(upsertResponse).toHaveBeenCalledWith("r-1", { size: 12 }, "draft");
  });

  it("discards with null values", async () => {
    const upsertResponse = vi.fn(async () => ({ id: "resp", status: "discarded" }));
    await new DiscardReviewUseCase({ upsertResponse } as never).execute("r-1");

    expect(upsertResponse).toHaveBeenCalledWith("r-1", null, "discarded");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-frontend && npx vitest run v2/domain/usecases --reporter=verbose`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write the use-cases**

Create `extralit-frontend/v2/domain/usecases/submit-reference-review-use-case.ts`:

```ts
import { AnnotationRepository, type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { normalizeV2ApiError } from "~/v2/infrastructure/repositories/apiErrors";

export class ReviewSubmitError extends Error {
  constructor(
    public readonly messages: string[],
    public readonly status: number | null
  ) {
    super(messages.join("; "));
    this.name = "ReviewSubmitError";
  }
}

export class SubmitReferenceReviewUseCase {
  constructor(private readonly annotationRepository: AnnotationRepository) {}

  async execute(recordId: string, values: Record<string, unknown>): Promise<RecordResponse> {
    try {
      return await this.annotationRepository.upsertResponse(recordId, values, "submitted");
    } catch (error) {
      const { messages, status } = normalizeV2ApiError(error);
      throw new ReviewSubmitError(messages, status);
    }
  }
}
```

Create `extralit-frontend/v2/domain/usecases/save-review-draft-use-case.ts`:

```ts
import { AnnotationRepository, type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { normalizeV2ApiError } from "~/v2/infrastructure/repositories/apiErrors";
import { ReviewSubmitError } from "./submit-reference-review-use-case";

export class SaveReviewDraftUseCase {
  constructor(private readonly annotationRepository: AnnotationRepository) {}

  async execute(recordId: string, values: Record<string, unknown>): Promise<RecordResponse> {
    try {
      return await this.annotationRepository.upsertResponse(recordId, values, "draft");
    } catch (error) {
      const { messages, status } = normalizeV2ApiError(error);
      throw new ReviewSubmitError(messages, status);
    }
  }
}
```

Create `extralit-frontend/v2/domain/usecases/discard-review-use-case.ts`:

```ts
import { AnnotationRepository, type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { normalizeV2ApiError } from "~/v2/infrastructure/repositories/apiErrors";
import { ReviewSubmitError } from "./submit-reference-review-use-case";

export class DiscardReviewUseCase {
  constructor(private readonly annotationRepository: AnnotationRepository) {}

  async execute(recordId: string): Promise<RecordResponse> {
    try {
      // Discarding reverts the projection cell to the suggestion (server filters submitted only).
      return await this.annotationRepository.upsertResponse(recordId, null, "discarded");
    } catch (error) {
      const { messages, status } = normalizeV2ApiError(error);
      throw new ReviewSubmitError(messages, status);
    }
  }
}
```

Modify `extralit-frontend/v2/di/di.ts` — add:

```ts
import { SubmitReferenceReviewUseCase } from "~/v2/domain/usecases/submit-reference-review-use-case";
import { SaveReviewDraftUseCase } from "~/v2/domain/usecases/save-review-draft-use-case";
import { DiscardReviewUseCase } from "~/v2/domain/usecases/discard-review-use-case";
```

```ts
    register(SubmitReferenceReviewUseCase).withDependency(AnnotationRepository).build(),
    register(SaveReviewDraftUseCase).withDependency(AnnotationRepository).build(),
    register(DiscardReviewUseCase).withDependency(AnnotationRepository).build(),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run v2 --reporter=verbose`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add v2
git commit -m "feat(v2-ui): submit/save-draft/discard review use-cases with 422 normalization"
```

---

### Task 13: Lean `V2TableEditor` (controlled tabulator wrapper, ~300 LOC budget)

**Files:**
- Create: `extralit-frontend/components/v2/table/V2TableEditor.vue`
- Test: `extralit-frontend/components/v2/table/V2TableEditor.test.ts`

**Interfaces:**
- Consumes: `ColumnMeta`, `columnCellEditor` (Task 3); `tabulator-tables` (already a dependency; **mocked in vitest** via `__mocks__/tabulator-tables.js` alias — component tests assert wiring/emits, not real tabulator rendering).
- Produces: `<V2TableEditor :model-value="Record<string, unknown>" :columns="ColumnMeta[]" :editable="boolean" @update:model-value>`. A `table` question's value is a JSONB dict with keys ⊆ bound columns (structure-only server validation) — rendered as a single-row editable grid, one tabulator column per bound `ColumnMeta`. Deliberately NOT ported: reference-table lookups and LLM-extraction viewmodels (v1-coupled features, spec §5).

- [ ] **Step 1: Write the failing test**

Create `extralit-frontend/components/v2/table/V2TableEditor.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { tabulatorColumns, valueFromRowData } from "./V2TableEditor.vue";

describe("V2TableEditor column derivation", () => {
  it("derives one tabulator column per bound ColumnMeta with dtype-driven editors", () => {
    const columns = tabulatorColumns(
      [
        new ColumnMeta("name", "str", false, null),
        new ColumnMeta("count", "int64", false, null),
        new ColumnMeta("done", "bool", false, null),
        new ColumnMeta("when", "datetime64[ns]", true, null),
      ],
      true
    );

    expect(columns.map((c) => [c.field, c.editor])).toEqual([
      ["name", "input"],
      ["count", "number"],
      ["done", "tickCross"],
      ["when", "date"],
    ]);
  });

  it("honors the review overlay hint over the dtype default", () => {
    const columns = tabulatorColumns([new ColumnMeta("count", "int64", false, { type: "text" })], true);
    expect(columns[0].editor).toBe("input");
  });

  it("disables editors when not editable", () => {
    const columns = tabulatorColumns([new ColumnMeta("name", "str", false, null)], false);
    expect(columns[0].editor).toBe(false);
  });
});

describe("valueFromRowData", () => {
  it("keeps only bound-column keys (server validates keys ⊆ bound columns)", () => {
    const value = valueFromRowData({ name: "a", stray: "x" }, [new ColumnMeta("name", "str", false, null)]);
    expect(value).toEqual({ name: "a" });
  });

  it("drops undefined cells so absent keys stay absent", () => {
    const value = valueFromRowData({ name: undefined }, [new ColumnMeta("name", "str", false, null)]);
    expect(value).toEqual({});
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extralit-frontend && npx vitest run components/v2/table --reporter=verbose`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the component**

Create `extralit-frontend/components/v2/table/V2TableEditor.vue`:

```vue
<template>
  <div ref="tableEl" class="v2-table-editor" />
</template>

<script lang="ts">
import { defineComponent, onBeforeUnmount, onMounted, ref, watch, type PropType } from "vue";
import { TabulatorFull as Tabulator, type ColumnDefinition } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { columnCellEditor, type CellEditor } from "~/v2/domain/entities/review/widget-mapping";

const EDITOR_BY_KIND: Record<CellEditor, ColumnDefinition["editor"]> = {
  text: "input",
  number: "number",
  checkbox: "tickCross",
  date: "date",
};

// Exported for unit tests (tabulator itself is mocked in vitest).
export const tabulatorColumns = (columns: ColumnMeta[], editable: boolean): ColumnDefinition[] =>
  columns.map((column) => ({
    title: column.name,
    field: column.name,
    editor: editable ? EDITOR_BY_KIND[columnCellEditor(column)] : false,
    headerSort: false,
  }));

export const valueFromRowData = (rowData: Record<string, unknown>, columns: ColumnMeta[]): Record<string, unknown> => {
  const value: Record<string, unknown> = {};
  for (const column of columns) {
    if (rowData[column.name] !== undefined) value[column.name] = rowData[column.name];
  }
  return value;
};

export default defineComponent({
  name: "V2TableEditor",
  props: {
    modelValue: { type: Object as PropType<Record<string, unknown>>, required: true },
    columns: { type: Array as PropType<ColumnMeta[]>, required: true },
    editable: { type: Boolean, default: true },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const tableEl = ref<HTMLElement>();
    let tabulator: Tabulator | null = null;
    let emitting = false;

    const build = () => {
      tabulator?.destroy();
      tabulator = new Tabulator(tableEl.value!, {
        data: [{ ...props.modelValue }], // single-row grid: the value IS one dict
        columns: tabulatorColumns(props.columns, props.editable),
        layout: "fitDataStretch",
      });
      tabulator.on("cellEdited", (cell) => {
        emitting = true;
        emit("update:modelValue", valueFromRowData(cell.getRow().getData(), props.columns));
        emitting = false;
      });
    };

    onMounted(build);
    onBeforeUnmount(() => tabulator?.destroy());

    watch(
      () => [props.modelValue, props.columns],
      () => {
        if (!emitting) build(); // external change (e.g. draft restore): rebuild
      },
      { deep: true }
    );

    return { tableEl };
  },
});
</script>

<style lang="scss" scoped>
.v2-table-editor {
  width: 100%;
}
</style>
```

If the vitest tabulator mock (`__mocks__/tabulator-tables.js`) doesn't export `TabulatorFull` as a constructible class with an `on` method, extend the mock minimally (add missing no-op methods) — do not unalias the real library in tests.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run components/v2/table --reporter=verbose`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add components/v2/table __mocks__
git commit -m "feat(v2-ui): lean V2TableEditor tabulator wrapper for table questions"
```

---

### Task 14: `ProjectionReviewForm` + widget adapters + review i18n

**Files:**
- Create: `extralit-frontend/v2/domain/entities/review/widget-adapters.ts`
- Create: `extralit-frontend/components/v2/review/ReviewCellInput.vue`
- Create: `extralit-frontend/components/v2/review/ReviewProvenance.vue`
- Modify: `extralit-frontend/translation/en.js` (add `review.*` keys)
- Test: `extralit-frontend/v2/domain/entities/review/widget-adapters.test.ts`

**Interfaces:**
- Consumes: `ReferenceReview` / `ReviewRecord` / `ReviewCell` / `SuggestionHint` (Task 11), extracted leaves (Task 9), `V2TableEditor` (Task 13), `Question` (Task 3).
- Produces:
  - Widget adapters (pure, tested): `buildLabelOptions(question, selected: unknown): {id,text,value,description,isSelected}[]`; `selectedFromLabelOptions(options, multiple): string | string[] | null`; `buildRatingOptions(question, selected: unknown): {id,value,isSelected}[]`; `selectedFromRatingOptions(options): number | null`; `buildRankingValues(question, ranked: unknown): {id,text,value,description,rank}[]`; `rankingAnswerFromValues(values): {value,rank}[]`; `suggestionHintFor(cell: ReviewCell): SuggestionHint | null`.

- [ ] **Step 1: Write the failing adapter tests**

Create `extralit-frontend/v2/domain/entities/review/widget-adapters.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { Question } from "../question/Question";
import { ReviewCell } from "./ReferenceReview";
import {
  buildLabelOptions,
  buildRankingValues,
  buildRatingOptions,
  rankingAnswerFromValues,
  selectedFromLabelOptions,
  selectedFromRatingOptions,
  suggestionHintFor,
} from "./widget-adapters";

const labelQuestion = new Question("q-1", "s-1", "label", "Label", null, "label_selection", ["label"], {
  type: "label_selection",
  options: [
    { value: "a", text: "A", description: null },
    { value: "b", text: "B", description: null },
  ],
}, false);

const ratingQuestion = new Question("q-2", "s-1", "stars", "Stars", null, "rating", ["stars"], {
  type: "rating",
  options: [{ value: 1 }, { value: 2 }, { value: 3 }],
}, false);

const rankingQuestion = new Question("q-3", "s-1", "rank", "Rank", null, "ranking", ["rank"], {
  type: "ranking",
  options: [
    { value: "x", text: "X", description: null },
    { value: "y", text: "Y", description: null },
  ],
}, false);

describe("label adapters", () => {
  it("builds leaf options with isSelected from a scalar (single) or array (multi) value", () => {
    expect(buildLabelOptions(labelQuestion, "b").map((o) => o.isSelected)).toEqual([false, true]);
    expect(buildLabelOptions(labelQuestion, ["a", "b"]).map((o) => o.isSelected)).toEqual([true, true]);
    expect(buildLabelOptions(labelQuestion, null).map((o) => o.isSelected)).toEqual([false, false]);
  });

  it("derives the server value shape back from options", () => {
    const options = buildLabelOptions(labelQuestion, "b");
    expect(selectedFromLabelOptions(options, false)).toBe("b");
    expect(selectedFromLabelOptions(options, true)).toEqual(["b"]);
    expect(selectedFromLabelOptions(buildLabelOptions(labelQuestion, null), false)).toBeNull();
  });
});

describe("rating adapters", () => {
  it("round-trips a numeric rating", () => {
    const options = buildRatingOptions(ratingQuestion, 2);
    expect(options).toEqual([
      { id: "stars_1", value: 1, isSelected: false },
      { id: "stars_2", value: 2, isSelected: true },
      { id: "stars_3", value: 3, isSelected: false },
    ]);
    expect(selectedFromRatingOptions(options)).toBe(2);
  });
});

describe("ranking adapters", () => {
  it("round-trips the [{value, rank}] server shape", () => {
    const values = buildRankingValues(rankingQuestion, [{ value: "y", rank: 1 }]);
    expect(values.find((v) => v.value === "y")?.rank).toBe(1);
    expect(values.find((v) => v.value === "x")?.rank).toBeNull();

    values.find((v) => v.value === "x")!.rank = 2;
    expect(rankingAnswerFromValues(values)).toEqual([
      { value: "y", rank: 1 },
      { value: "x", rank: 2 },
    ]);
  });
});

describe("suggestionHintFor", () => {
  it("returns a hint only for suggestion-sourced cells", () => {
    const suggested = new ReviewCell(labelQuestion, "a", "suggestion", { agent: "gpt", score: 0.5, suggestedValue: "a" }, false);
    const responded = new ReviewCell(labelQuestion, "a", "response", null, false);

    expect(suggestionHintFor(suggested)?.isSuggested("a")).toBe(true);
    expect(suggestionHintFor(responded)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail, then write the adapters**

Run: `cd extralit-frontend && npx vitest run v2/domain/entities/review --reporter=verbose` — expected FAIL.

Create `extralit-frontend/v2/domain/entities/review/widget-adapters.ts`:

```ts
import { Question } from "../question/Question";
import { type ReviewCell } from "./ReferenceReview";
import { SuggestionHint } from "./SuggestionHint";

// Adapters between server value shapes and the extracted leaf-widget option shapes
// (see Task 9 contracts). Ids follow v1's `${questionName}_${value}` convention.

export interface LabelOption {
  id: string;
  text: string;
  value: string;
  description: string | null;
  isSelected: boolean;
}

export const buildLabelOptions = (question: Question, selected: unknown): LabelOption[] => {
  const selectedValues = Array.isArray(selected) ? (selected as string[]) : selected != null ? [selected as string] : [];
  return question.options.map((option) => ({
    id: `${question.name}_${option.value}`,
    text: option.text,
    value: option.value,
    description: option.description,
    isSelected: selectedValues.includes(option.value),
  }));
};

export const selectedFromLabelOptions = (options: LabelOption[], multiple: boolean): string | string[] | null => {
  const selected = options.filter((o) => o.isSelected).map((o) => o.value);
  if (multiple) return selected;
  return selected[0] ?? null;
};

export interface RatingOption {
  id: string;
  value: number;
  isSelected: boolean;
}

export const buildRatingOptions = (question: Question, selected: unknown): RatingOption[] =>
  question.ratingValues.map((value) => ({
    id: `${question.name}_${value}`,
    value,
    isSelected: selected === value,
  }));

export const selectedFromRatingOptions = (options: RatingOption[]): number | null =>
  options.find((o) => o.isSelected)?.value ?? null;

export interface RankingValue {
  id: string;
  text: string;
  value: string;
  description: string | null;
  rank: number | null;
}

export const buildRankingValues = (question: Question, ranked: unknown): RankingValue[] => {
  const ranks = new Map<string, number>(
    Array.isArray(ranked) ? (ranked as { value: string; rank: number }[]).map((r) => [r.value, r.rank]) : []
  );
  return question.options.map((option) => ({
    id: `${question.name}_${option.value}`,
    text: option.text,
    value: option.value,
    description: option.description,
    rank: ranks.get(option.value) ?? null,
  }));
};

export const rankingAnswerFromValues = (values: RankingValue[]): { value: string; rank: number }[] =>
  values
    .filter((v) => v.rank != null)
    .sort((a, b) => (a.rank as number) - (b.rank as number))
    .map((v) => ({ value: v.value, rank: v.rank as number }));

export const suggestionHintFor = (cell: ReviewCell): SuggestionHint | null => {
  if (cell.source !== "suggestion" || !cell.provenance) return null;
  return new SuggestionHint(
    cell.provenance.suggestedValue,
    cell.provenance.agent,
    cell.provenance.score,
    cell.question.type === "multi_label_selection"
  );
};
```

Re-run: `npx vitest run v2/domain/entities/review --reporter=verbose` — expected PASS.

- [ ] **Step 3: Add `review.*` i18n keys**

In `extralit-frontend/translation/en.js`, add:

```js
  review: {
    suggestion: "Suggestion",
    response: "Response",
    agent: "Agent",
    score: "Score",
```


- [ ] **Step 5: Write the components**

Create `extralit-frontend/components/v2/review/ReviewProvenance.vue`:

```vue
<template>
  <span class="review-provenance">
    <span class="review-provenance__badge" :class="`--${source}`" v-text="$t(`review.${source}`)" />
    <template v-if="provenance">
      <span v-if="provenance.agent">{{ $t("review.agent") }}: {{ provenance.agent }}</span>
      <span v-if="provenance.score != null">{{ $t("review.score") }}: {{ provenance.score.toFixed(2) }}</span>
    </template>
  </span>
</template>

<script lang="ts">
import { type PropType } from "vue";
import { type Provenance } from "~/v2/domain/entities/review/ReferenceReview";

export default {
  name: "ReviewProvenance",
  props: {
    source: { type: String as PropType<"response" | "suggestion">, required: true },
    provenance: { type: Object as PropType<Provenance | null>, default: null },
  },
};
</script>

<style lang="scss" scoped>
.review-provenance {
  display: inline-flex;
  gap: $base-space;
  font-size: 0.8em;
  color: var(--fg-tertiary);

  &__badge {
    padding: 2px $base-space;
    border-radius: $border-radius;

    &.--suggestion {
      background: var(--bg-opacity-10);
    }

    &.--response {
      background: var(--bg-opacity-20);
    }
  }
}
</style>
```

Create `extralit-frontend/components/v2/review/ReviewCellInput.vue` — the §6.1 dispatch (question.type → widget), keeping the leaves controlled:

```vue
<template>
  <div class="review-cell" :data-question="cell.question.name">
    <label class="review-cell__title">
      {{ cell.question.title }}
      <span v-if="cell.question.required" class="review-cell__required">*</span>
    </label>
    <ReviewProvenance v-if="cell.source" :source="cell.source" :provenance="cell.provenance" />

    <p v-if="cell.notApplicable" class="review-cell__na" v-text="$t('review.notApplicable')" />

    <template v-else>
      <ContentEditableFeedbackTask
        v-if="cell.question.type === 'text'"
        :value="String(modelValue ?? '')"
        :original-value="String(cell.value ?? '')"
        @change-text="$emit('update:modelValue', $event)"
      />

      <LabelSelectionComponent
        v-else-if="cell.question.isLabelType"
        v-model="labelOptions"
        :component-id="cell.question.id"
        :multiple="cell.question.type === 'multi_label_selection'"
        :suggestion="suggestionHint"
        :visible-shortcuts="false"
        @on-selected="onLabelChanged"
      />

      <RatingMonoSelectionComponent
        v-else-if="cell.question.type === 'rating'"
        v-model="ratingOptions"
        :suggestion="suggestionHint"
        @on-selected="onRatingChanged"
      />

      <DndSelectionComponent
        v-else-if="cell.question.type === 'ranking'"
        :ranking="ranking"
        :suggestion="suggestionHint"
        @on-reorder="onReordered"
      />

      <V2TableEditor
        v-else-if="cell.question.type === 'table'"
        :model-value="(modelValue as Record<string, unknown>) ?? {}"
        :columns="tableColumns"
        @update:model-value="$emit('update:modelValue', $event)"
      />
    </template>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, ref, watch, type PropType } from "vue";
import { type ReviewCell } from "~/v2/domain/entities/review/ReferenceReview";
import { type ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import {
  buildLabelOptions,
  buildRankingValues,
  buildRatingOptions,
  rankingAnswerFromValues,
  selectedFromLabelOptions,
  selectedFromRatingOptions,
  suggestionHintFor,
} from "~/v2/domain/entities/review/widget-adapters";
import { adaptQuestionsToSlots } from "@/components/base/inputs/ranking/ranking-adapter";
// Explicit imports (not Nuxt auto-import) so plain vitest `mount` resolves the children
// and name-based `global.stubs` can replace them.
import ReviewProvenance from "./ReviewProvenance.vue";
import ContentEditableFeedbackTask from "@/components/base/inputs/text-area/ContentEditableFeedbackTask.vue";
import LabelSelectionComponent from "@/components/base/inputs/label-selection/LabelSelection.component.vue";
import RatingMonoSelectionComponent from "@/components/base/inputs/rating/RatingMonoSelection.component.vue";
import DndSelectionComponent from "@/components/base/inputs/ranking/DndSelection.component.vue";
import V2TableEditor from "@/components/v2/table/V2TableEditor.vue";

export default defineComponent({
  name: "ReviewCellInput",
  components: {
    ReviewProvenance,
    ContentEditableFeedbackTask,
    LabelSelectionComponent,
    RatingMonoSelectionComponent,
    DndSelectionComponent,
    V2TableEditor,
  },
  props: {
    cell: { type: Object as PropType<ReviewCell>, required: true },
    modelValue: { type: null as unknown as PropType<unknown>, default: null },
    // table questions: the bound columns' ColumnMeta from the pinned version cache
    tableColumns: { type: Array as PropType<ColumnMeta[]>, default: () => [] },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const question = props.cell.question;
    const suggestionHint = computed(() => suggestionHintFor(props.cell));

    // Leaves mutate their option arrays in place; hold them locally and translate on change.
    const labelOptions = ref(buildLabelOptions(question, props.modelValue));
    const ratingOptions = ref(buildRatingOptions(question, props.modelValue));
    const rankingValues = ref(buildRankingValues(question, props.modelValue));
    const ranking = computed(() => adaptQuestionsToSlots({ options: rankingValues.value }));

    watch(
      () => props.modelValue,
      (value) => {
        // External resets (draft restore / discard) — rebuild local option state.
        labelOptions.value = buildLabelOptions(question, value);
        ratingOptions.value = buildRatingOptions(question, value);
        rankingValues.value = buildRankingValues(question, value);
      }
    );

    const onLabelChanged = () =>
      emit("update:modelValue", selectedFromLabelOptions(labelOptions.value, question.type === "multi_label_selection"));
    const onRatingChanged = () => emit("update:modelValue", selectedFromRatingOptions(ratingOptions.value));
    const onReordered = (newRanking: { getRanking(option: unknown): number | undefined }) => {
      rankingValues.value.forEach((option) => {
        option.rank = newRanking.getRanking(option) ?? null;
      });
      emit("update:modelValue", rankingAnswerFromValues(rankingValues.value));
    };

    return { suggestionHint, labelOptions, ratingOptions, ranking, onLabelChanged, onRatingChanged, onReordered };
  },
});
</script>

<style lang="scss" scoped>
.review-cell {
  display: flex;
  flex-direction: column;
  gap: $base-space;
  margin-bottom: $base-space * 2;

  &__title {
    font-weight: 500;
  }

  &__required {
    color: var(--color-danger, #c00);
  }

  &__na {
    color: var(--fg-tertiary);
    font-style: italic;
  }
}
</style>
```


- [ ] **Step 6: Run tests to verify they pass**

Run: `cd extralit-frontend && npx vitest run components/v2 v2 --reporter=verbose && npm run test`
Expected: all PASS (including updated Task 11 tests for the `columnsCache` field).

- [ ] **Step 7: Commit**

```bash
git add components/v2/review v2 translation/en.js
git commit -m "feat(v2-ui): pure ProjectionReviewForm with per-type widgets, provenance and orphan surfacing"
```

---

---

### Task 16: e2e infrastructure (remote-chromium project, seed script) + scenarios 1–2

**Files:**
- Modify: `extralit-frontend/playwright.config.ts` (v2 project; isolate old projects from `e2e/v2`)
- Create: `extralit-frontend/e2e/v2/fixtures.ts`
- Create: `extralit-frontend/e2e/v2/seed/seed_v2_e2e.py`
- Create: `extralit-frontend/e2e/v2/auth-smoke.spec.ts` (scenario 1)
- Create: `extralit-frontend/e2e/v2/README.md` (how to run on this host)

**Interfaces:**
- Consumes: the real backend stack (no network mocks — seams A/B are the point), the seeded data contract below, Tasks 6–15 UI.
- Produces:
  - `test`/`expect` re-exports from `e2e/v2/fixtures.ts` with a worker-scoped `browser` fixture: `chromium.connectOverCDP(process.env.E2E_CDP_URL)` when set, plain `chromium.launch()` otherwise (CI).
  - Seed contract (JSON written to `e2e/v2/seed/seed-output.json`): `{ workspaceId, schemaId, schemaName, reference, recordId, questions: { size: {id, name}, label: {id, name} } }` with `reference = "10.1000/j.e2e-v2"` (contains a slash by design).
  - Env vars: `E2E_BASE_URL` (frontend URL reachable FROM the remote browser, e.g. `http://192.168.1.79:3000`), `E2E_CDP_URL` (remote chromium CDP endpoint, e.g. `http://ccui:9222`), `E2E_API_URL` (server, default `http://localhost:6900`), `E2E_USERNAME`/`E2E_PASSWORD` (owner credentials).

Host context (from repo memory/CLAUDE.md): local chromium cannot launch on this Orin host (missing OS libs, no sudo) — the CDP path is the local runway; plain launch is for CI. The stale Argilla `e2e/` specs are not a gate; only `e2e/v2/` is.

- [ ] **Step 1: Playwright config — dedicated v2 project**

In `extralit-frontend/playwright.config.ts`:

1. Add `testIgnore: "v2/**"` to each of the three existing project entries, e.g.:

```ts
    { name: "chromium", testIgnore: "v2/**", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", testIgnore: "v2/**", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", testIgnore: "v2/**", use: { ...devices["Desktop Safari"] } },
```

2. Append the v2 project:

```ts
    {
      name: "v2",
      testMatch: "v2/**/*.spec.ts",
      retries: 0, // real backend: retries mask seeding/state bugs
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.E2E_BASE_URL ?? process.env.BASE_URL ?? "http://localhost:3000",
      },
    },
```

3. Leave `webServer` as is (`reuseExistingServer: !process.env.CI` — locally you start `npm run dev -- --host` yourself so the remote browser can reach it).

- [ ] **Step 2: CDP browser fixture**

Create `extralit-frontend/e2e/v2/fixtures.ts`:

```ts
import { test as base, chromium, type Browser } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export interface SeedOutput {
  workspaceId: string;
  schemaId: string;
  schemaName: string;
  reference: string;
  recordId: string;
  questions: Record<string, { id: string; name: string }>;
}

export const loadSeed = (): SeedOutput =>
  JSON.parse(readFileSync(join(__dirname, "seed", "seed-output.json"), "utf-8"));

export const credentials = () => ({
  username: process.env.E2E_USERNAME ?? "extralit",
  password: process.env.E2E_PASSWORD ?? "12345678",
});

// Local chromium cannot launch on the Orin dev host — connect to the remote ccui
// chromium over CDP when E2E_CDP_URL is set; fall back to a plain launch (CI).
export const test = base.extend<object, { browser: Browser }>({
  browser: [
    async ({}, use) => {
      const cdpUrl = process.env.E2E_CDP_URL;
      const browser = cdpUrl ? await chromium.connectOverCDP(cdpUrl) : await chromium.launch();
      await use(browser);
      await browser.close();
    },
    { scope: "worker" },
  ],
});

export const expect = test.expect;

// Real-backend sign-in through the actual UI: this is seam A — the first bearer-token
// client of /api/v2. No route mocking anywhere in e2e/v2.
export const signIn = async (page: import("@playwright/test").Page) => {
  const { username, password } = credentials();
  await page.goto("/sign-in");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"));
};
```

- [ ] **Step 3: Seed script**

Create `extralit-frontend/e2e/v2/seed/seed_v2_e2e.py` (run with the server project's env so `pandera` matches the server's version — the schema `body` must be a Pandera `DataFrameSchema.to_json()` string, exactly as the server's own tests build it):

```python
"""Seed deterministic v2 fixtures for the frontend e2e suite.

Usage (from extralit-frontend/):
    uv run --project ../extralit-server python e2e/v2/seed/seed_v2_e2e.py \
        --api-url http://localhost:6900 --username extralit --password 12345678

Writes e2e/v2/seed/seed-output.json. Idempotent: deletes and recreates the e2e schema.
"""

import argparse
import json
from pathlib import Path

import httpx
import pandera.pandas as pa

SCHEMA_NAME = "e2e_v2_slice"
REFERENCE = "10.1000/j.e2e-v2"  # slash on purpose: seam B
WORKSPACE_NAME = "e2e-v2"

BODY = pa.DataFrameSchema(
    columns={
        "size": pa.Column(pa.String, nullable=True),
        "label": pa.Column(pa.String, nullable=True),
        "country": pa.Column(pa.String, nullable=True),
    }
).to_json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:6900")
    parser.add_argument("--username", default="extralit")
    parser.add_argument("--password", default="12345678")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_url, timeout=30) as client:
        token = client.post(
            "/api/v2/token", data={"username": args.username, "password": args.password}
        ).raise_for_status().json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Workspace (v1 API): reuse if it exists.
        workspaces = client.get("/api/v1/me/workspaces").raise_for_status().json()["items"]
        workspace = next((w for w in workspaces if w["name"] == WORKSPACE_NAME), None)
        if workspace is None:
            workspace = client.post("/api/v1/workspaces", json={"name": WORKSPACE_NAME}).raise_for_status().json()

        # Schema: recreate for determinism.
        schemas = client.get("/api/v2/schemas", params={"workspace_id": workspace["id"]}).raise_for_status().json()["items"]
        for schema in schemas:
            if schema["name"] == SCHEMA_NAME:
                client.delete(f"/api/v2/schemas/{schema['id']}").raise_for_status()
        schema = client.post(
            "/api/v2/schemas", json={"name": SCHEMA_NAME, "workspace_id": workspace["id"]}
        ).raise_for_status().json()

        client.post(f"/api/v2/schemas/{schema['id']}/versions", json={"body": BODY}).raise_for_status()

        questions = {}
        for name, qtype, settings in [
            ("size", "text", {}),
            (
                "label",
                "label_selection",
                {
                    "type": "label_selection",
                    "options": [
                        {"value": "intervention", "text": "Intervention", "description": None},
                        {"value": "control", "text": "Control", "description": None},
                    ],
                },
            ),
        ]:
            question = client.post(
                f"/api/v2/schemas/{schema['id']}/questions",
                json={"name": name, "title": name.title(), "type": qtype, "columns": [name], "settings": settings, "required": name == "size"},
            ).raise_for_status().json()
            questions[name] = {"id": question["id"], "name": question["name"]}

        records = client.post(
            f"/api/v2/schemas/{schema['id']}/records:bulk-upsert",
            json={"items": [{"fields": {"size": "120", "label": "control", "country": "KE"}, "reference": REFERENCE}]},
        ).raise_for_status().json()["items"]
        record = records[0]

        client.put(
            f"/api/v2/records/{record['id']}/suggestions",
            json={"question_id": questions["size"]["id"], "value": "120", "score": 0.87, "agent": "e2e-seeder"},
        ).raise_for_status()

        # Fresh index so the search scenario has something to find.
        client.post(f"/api/v2/schemas/{schema['id']}:rebuild-index").raise_for_status()

    output = {
        "workspaceId": workspace["id"],
        "schemaId": schema["id"],
        "schemaName": SCHEMA_NAME,
        "reference": REFERENCE,
        "recordId": record["id"],
        "questions": questions,
    }
    out_path = Path(__file__).parent / "seed-output.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
```

Add npm script in `extralit-frontend/package.json`:

```json
"e2e:v2:seed": "uv run --project ../extralit-server python e2e/v2/seed/seed_v2_e2e.py",
"e2e:v2": "playwright test --project=v2"
```

Add `e2e/v2/seed/seed-output.json` to `extralit-frontend/.gitignore`.

- [ ] **Step 4: Scenario 1 — auth + smoke**

Create `extralit-frontend/e2e/v2/auth-smoke.spec.ts`:

```ts
import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam A (spec §10.1-A): first bearer-token client of /api/v2 — no server test sends
// Authorization: Bearer or a CORS Origin to a v2 route. Nothing here is mocked.
test("signs in with a bearer token, lists schemas, opens records", async ({ page }) => {
  const seed = loadSeed();

  const schemasRequest = page.waitForResponse(
    (r) => r.url().includes("/api/v2/schemas") && r.request().method() === "GET"
  );
  await signIn(page);
  await page.goto("/schemas");

  const schemasResponse = await schemasRequest;
  expect(schemasResponse.status()).toBe(200);
  expect(schemasResponse.request().headers()["authorization"]).toMatch(/^Bearer /);

  await expect(page.getByText(seed.schemaName)).toBeVisible();

  await page.getByText(seed.schemaName).click();
  await expect(page.getByText(seed.reference)).toBeVisible();
});
```

Note: the schema list loads for the *selected workspace* — if the seeded workspace isn't the first, switch to it via the workspace selector before asserting (check the home header UI for the selector; add the interaction here once visible).


- [ ] **Step 6: README + run**

Create `extralit-frontend/e2e/v2/README.md`:

```markdown
# v2 e2e suite (real backend, remote chromium)

Prereqs: full local stack up (`docker-compose up -d`, server on :6900), then:

1. Seed:      `npm run e2e:v2:seed`
2. Dev server reachable from the browser container: `npm run dev -- --host`
3. Run:
   E2E_CDP_URL=http://ccui:9222 \
   E2E_BASE_URL=http://<this-host-lan-ip>:3000 \
   npm run e2e:v2

Without `E2E_CDP_URL` (e.g. CI) a local chromium is launched. No network mocking:
these specs gate real auth (bearer on /api/v2), slashed-DOI encoding, the
suggestion→response loop, drafts and search freshness. The legacy Argilla specs
under e2e/* are not a gate for v2 work.
```

Run scenarios 1–2 per the README. Expected: both green against the live stack. Debug tips: `page.waitForResponse` timeouts usually mean the devProxy or workspace selection, not the assertion.

- [ ] **Step 7: Commit**

```bash
git add e2e/v2 playwright.config.ts package.json .gitignore
git commit -m "test(v2-ui): e2e infra (CDP remote chromium, API seeding) + auth and slashed-DOI scenarios"
```

---

### Task 17: e2e scenarios 3–5 (review loop, draft lifecycle, search round-trip)

**Files:**
- Create: `extralit-frontend/e2e/v2/search-roundtrip.spec.ts` (scenario 5)

**Interfaces:**
- Consumes: Task 16 fixtures/seed (`loadSeed`, `signIn`, seeded suggestion on question `size` with agent `e2e-seeder`), Task 14 form DOM contract (`[data-question]`, `[data-test='submit-<id>']`, provenance badges rendering `review.suggestion`/`review.response` copy — i.e. "Suggestion"/"Response" in English).
- Produces: the remaining slice-gating scenarios (spec §10.2 items 3–5). Scenarios 6–8 are follow-ups, out of this plan.



- [ ] **Step 3: Scenario 5 — search round-trip**

Create `extralit-frontend/e2e/v2/search-roundtrip.spec.ts`:

```ts
import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam D (spec §10.1-D): first real write→search freshness check anywhere. The index is
// best-effort/eventually consistent — poll with expect.toPass instead of asserting once.
test("FTS finds the seeded record; filters and empty results render gracefully", async ({ page }) => {
  const seed = loadSeed();
  await signIn(page);
  await page.goto(`/schemas/${seed.schemaId}`);
  await expect(page.getByText(seed.reference)).toBeVisible();

  const searchBox = page.getByPlaceholder("Search records…");

  await expect(async () => {
    await searchBox.fill("control");
    await searchBox.press("Enter");
    await expect(page.getByText(seed.reference)).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 30_000 }); // eventual consistency window

  // Filtered search: status filter travels through the :search body.
  await page.locator("select").selectOption("pending");
  await expect(page.getByText(seed.reference)).toBeVisible();

  // Graceful empty state — copy must not claim "0 records exist" (total is approximate).
  await searchBox.fill("zzz-no-such-token-zzz");
  await searchBox.press("Enter");
  await expect(page.getByText("No records match this search.")).toBeVisible();
});
```

- [ ] **Step 4: Run the full v2 e2e suite**

```bash
cd extralit-frontend
npm run e2e:v2:seed
E2E_CDP_URL=http://ccui:9222 E2E_BASE_URL=http://<lan-ip>:3000 npm run e2e:v2
```

Expected: 5 specs green. Scenario 4's failure mode is informative, not just red: if the draft DOES project, that's the seam-C server bug — report upstream (spec ledger §10.3 pattern) with the curl reproduction from the task preamble.

- [ ] **Step 5: Commit**

```bash
git add e2e/v2
git commit -m "test(v2-ui): e2e review loop, draft lifecycle and search round-trip scenarios"
```

---

## Final verification (after all tasks)

- [ ] `cd extralit-server && uv run pytest tests/unit --disable-warnings` — green.
- [ ] `cd extralit-frontend && npm run gen:api && git diff --exit-code -- v2/infrastructure/api` — no drift.
- [ ] `cd extralit-frontend && npm run test && npm run lint && npx nuxi typecheck` — green (typecheck may surface pre-existing v1 issues; only new `v2/`/`components/v2` errors block).
- [ ] Boundary audit: `grep -rn "from \"[~@]/v1" extralit-frontend/v2/ | grep -v "store/create\|infrastructure/services"` → empty; `grep -rn "v2/" extralit-frontend/v1/` → empty.
- [ ] Use superpowers:finishing-a-development-branch — PR against `develop`.

## Deferred / ledger (do not build now)

- Scenarios 6–8 (multi-annotator isolation, old-version rendering e2e, required-422 rendering e2e) — follow the slice (spec §10.2).
- Column filters on the schema detail page derived from `columns_cache` (only `status` ships now).
- Markdown/table sub-modes of the text widget; span questions; schema authoring UI; Queue UI (Phase 5); v1 retirements (Phase 6).
