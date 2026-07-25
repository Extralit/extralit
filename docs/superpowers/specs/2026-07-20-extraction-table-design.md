# Extraction Table — Design Spec

**Date:** 2026-07-20
**Branch:** `feat/v2-ui-extraction-table` (based on `develop` @ `52eab556f`, PR #232 merged)
**Predecessors:** `2026-06-27-schema-centric-data-model-design.md` (§17.4 projection),
`2026-07-09-v2-frontend-vertical-slice-design.md` (§7 review form + ledger),
`2026-07-19-reference-review.md` (interrogation brief that triggered this redesign).

## 1. Problem

The v2 review slice (#230/#232) shipped a per-reference review page whose client-side
assembly (`entities/review/ReferenceReview` + `get-reference-review-use-case`) composes
projection + questions + records + versions + suggestions + responses across 5+
endpoints per reference. That is exactly the chattiness §7's ledger item predicted
("if the multi-endpoint composition proves chatty, enrich the projection payload
server-side"), and it duplicates derivation that belongs on the server: review state
**is** submitted suggestions/responses — it should not exist as a parallel
client-side entity.

Meanwhile the product's first-order surface — the view a user actually starts from —
is missing: a workspace-level **extraction table** aggregating references (rows) ×
schemas (column groups), with cell values coalesced over suggestions/responses and
cells linking to their source record.

This build executes the ledger item (server-side enrichment), ships the extraction
table, and deletes the reference-review page whose function is superseded (review
embeds into the annotation + projection flow going forward).

## 2. Inherited decisions (from prior specs — restated, not reopened)

- **§17.4:** the projection view is *the* product surface; precedence
  `submitted response → suggestion → empty` is applied **server-side**; the endpoint
  contract reserves a backing swap (OLAP/materialized) without shape changes.
- **Contract gotchas** that move from client to server-side derivation: asymmetric
  keying (responses by question *name*, suggestions by question *id* — join through
  the questions list), double-wrapped `{question_name: {value}}` response values,
  `GET /records/{id}/responses` returning bare object **or literal `null`** with 200.
- **Reuse-don't-fork:** widget adapters, `ReviewCellInput`, `ReviewProvenance`, and
  the submit/draft/discard use-cases are the reuse base for the future embedded
  review drawer. v0's Tabulator `RenderTable` lineage is **not** reused — Perspective
  replaces it.
- **DDD layering** as in the rest of `v2/`: repository → use-case → Pinia storage →
  page/composable; openapi-typescript types via the `gen:api` drift gate.

## 3. Decisions (from 2026-07-20 interview)

### 3.1 Grid semantics

| Decision | Choice |
|---|---|
| Rows | Every distinct reference in the workspace (union across schemas' records); schemas with no record for a reference render empty cells — the grid doubles as a coverage map |
| Columns | Per-schema column groups; **all** question columns shown (visibility config deferred); flat names `Schema.question` / `Schema.question.subcol` |
| Cell content | Coalesced data values: latest **submitted** response (any user) `??` suggestion `??` empty. Drafts never appear — endpoint stays user-agnostic and cacheable |
| Record multiplicity | One **effective record** per (reference, schema); row multiplicity comes only from `table`-type question values fanning out into N sub-rows |
| Multi-table alignment | Independent stacking: row count = max(fan-outs) per reference; no cartesian product, no fabricated row pairing across unrelated table questions |
| Fan-out scalars | **Repeat scalar values on every fan-out row** (true denormalized rows — correct for pivots/Arrow/CSV later); visual grouping via row-banding by reference, not rowspan (Perspective is flat-columnar and cannot merge cells) |
| Scale target | ~100s of references (typical review), ~5 schemas, ~30 columns; one paginated endpoint, no virtualization work needed (Perspective handles far more) |
| Sorting/filtering | None — static grid in v1 |

### 3.2 Backend — workspace-level denormalized projection

**New endpoint** `GET /api/v2/projection?workspace_id=…&offset=0&limit=50`
(reference-page granularity; `limit` counts references, not fan-out rows):

```jsonc
{
  "columns": [
    { "name": "Design.type", "schema_id": "…", "schema_name": "Design",
      "question_name": "type", "sub_column": null, "dtype": "…" },
    { "name": "Outcomes.results.value", "schema_id": "…", "schema_name": "Outcomes",
      "question_name": "results", "sub_column": "value", "dtype": "…" }
  ],
  "rows": [
    { "reference": "10.1234/abc", "row_index": 0,
      "cells": { "Design.type": { "value": "RCT", "source": "response",
                                   "record_id": "…" },
                 "Outcomes.results.value": { "value": "12%", "source": "suggestion",
                                             "record_id": "…", "agent": "gpt-x",
                                             "score": 0.92 } } }
  ],
  "total_references": 213
}
```

- Server performs the full denormalization (coalesce → table fan-out → independent
  stacking → scalar repetition); the client only renders.
- **Enriched cells** carry `record_id` + `source` (+ `agent`/`score` when the value
  came from a suggestion) so any consumer links and shows provenance with zero
  extra calls.
- Absent cells (no record / no value) are omitted from `cells`; the client renders
  them as null.
- **Assembly must be batch-queried** — all schemas → all records in workspace →
  bulk latest-submitted-responses + suggestions — not the per-record N+1 the
  2026-07-19 brief flagged in `contexts/v2/projection.py`.
- The per-reference `GET /projection/references/{reference:path}` **stays** (SDK #231
  consumes it) and adopts the same enriched cell shape **additively**
  (`record_id`/`agent`/`score` added to `ProjectionCell`).
- The `/projection/…` prefix convention is kept (avoids the greedy
  `GET /references/{reference:path}` shadowing).

### 3.3 Frontend — `/extractions` page on Perspective

- **New route `pages/extractions/index.vue`** ("Extractions") — full-page standalone
  view; **not** wired into `index.vue`/nav in this build. (`/schemas/*` remains
  reserved for schema-editor functions.)
- **Grid engine:** Perspective **4.x** under the `@perspective-dev/*` npm scope
  (`@perspective-dev/client`, `@perspective-dev/viewer`,
  `@perspective-dev/viewer-datagrid`) — the actively-developed line matching
  <https://perspective-dev.github.io/guide/how_to/javascript/importing.html>.
  `@finos/*` is frozen at 3.8.0 and not used.
  - ESM WASM bootstrap via Vite `?url` imports:
    `perspective.init_server(fetch(SERVER_WASM))` +
    `perspective_viewer.init_client(fetch(CLIENT_WASM))`; Vite `target: esnext`.
  - Lazy-loaded route chunk so the WASM/bundle cost is paid only on this page.
- **Data path:** client pages through the endpoint (50–100 refs/page) and loads all
  pages into **one** Perspective table as flat JSON records keyed by the
  `columns[].name` manifest. Arrow IPC streaming is a recorded follow-up (§5), not
  built now.
- **Static grid:** viewer toolbar/settings hidden; no sort/filter UI; row-banding by
  reference.
- **Interaction v1:** native row hover + pointer cursor on linkable cells.
  Cell click emits the **future annotation URL contract**
  `/dataset/{schema_id}/annotation-mode?_search={reference}` (schema id in the
  dataset slot) behind a feature guard — **disabled** until annotation-mode resolves
  v2 schema ids (ledger, §5). Click plumbing (`record_id`, `schema_id`, `reference`
  per cell) ships and is testable now.
- **Layering:** `ProjectionRepository.getWorkspaceProjection()` →
  `get-workspace-projection-use-case` → Pinia storage → `useExtractionsViewModel` →
  page.
- **Vue 3 / Nuxt 4 integration notes** (verified against this repo's config):
  - The app is `ssr: false` (SPA) — no `<client-only>` wrapper needed; the WASM
    bootstrap just runs once client-side (page/component `onMounted` or a lazy
    module-level init guard).
  - `<perspective-viewer>` is a **web Custom Element**: Vue must be told not to
    resolve it as a component via
    `vue.compilerOptions.isCustomElement = (tag) => tag.startsWith("perspective-")`
    in `nuxt.config.ts` (see §7 refs).
  - Vite needs `build.target`/`optimizeDeps.esbuildOptions.target: "esnext"` for
    the Perspective ESM/WASM builds, and the `?url` asset-import syntax for the
    two `.wasm` binaries (§7 refs).
  - There is **no official Vue/Nuxt Perspective example** — the repo's
    `vite-example` (bundler wiring) and `react-example` (wrapping the custom
    element in a component framework) are the transferable templates (§7).

### 3.4 Discovered constraint — table-question values are single-row today

Found during spec refinement (2026-07-20), affects the fan-out design:

- The server validator (`validators/v2/values.py::_validate_table`) accepts a table
  value only as **a dict keyed by bound columns** — i.e. **one row**.
- The frontend editor agrees: `V2TableEditor.vue` renders
  `data: [{ ...modelValue }]` — "single-row grid: the value IS one dict".
- A table question's **sub-columns are its `V2Question.columns` binding** (the ≥1
  schema columns it binds; non-table types bind exactly 1). Denormalized column
  names `Schema.question.subcol` come from this list.

**Resolution (recommended, in scope for this build's backend task):** extend the
table value contract **additively** to also accept `list[dict]` (N rows), keeping
bare `dict` valid as the 1-row case — `_validate_table` validates each row's keys
against the binding; `V2TableEditor` keeps emitting the dict form until the
embedded-review work touches it. The projection fan-out handles both shapes from
day one (`dict → [dict]` normalization), so the grid is correct now (fan-out = 1)
and automatically right when multi-row values start arriving from the SDK/agents.

### 3.5 Deletions — review derives from suggestions/responses, no parallel entity

The reference-review **page is deleted**; its function is superseded by the
extraction table now and the embedded annotation/review flow later.

**Delete in this build:**
- `pages/references/[...reference].vue` + `useReferenceReviewViewModel` (+ test)
- `components/v2/review/ProjectionReviewForm.vue`, `ReviewRecordCard.vue`
- `v2/domain/entities/review/ReferenceReview.ts`
- `v2/domain/usecases/get-reference-review-use-case.ts` (+ test) — superseded by the
  server-side enriched projection
- `v2/infrastructure/storage/ReferenceReviewsStorage.ts` (page-scoped cache, dies
  with the page)
- The `/references/…` entry link in `components/v2/schemas/V2RecordsTable.vue`
- e2e specs `e2e/v2/{review-loop,draft-lifecycle,slashed-reference}.spec.ts`
- Corresponding `v2/di/di.ts` registrations

**Keep (powers the future embedded-review drawer):**
- `entities/review/widget-adapters.ts`, `widget-mapping.ts`, `SuggestionHint.ts`,
  `response-values.ts` (each with tests)
- `components/v2/review/ReviewCellInput.vue`, `ReviewProvenance.vue`
- `submit-reference-review-use-case.ts`, `save-review-draft-use-case.ts`,
  `discard-review-use-case.ts`

**Accepted risk:** deleting the three e2e specs removes end-to-end coverage of the
suggestion→response submit path until the drawer lands (kept use-cases retain unit
tests). Replacement gate in this build: a new `e2e/v2/extractions-grid.spec.ts`
(seed → grid renders coalesced values → empty cells correct).

## 4. Testing strategy

**Acceptance criteria:** the properties these gates exist to prove are enumerated in
[`2026-07-24-extraction-projection-acceptance.md`](./2026-07-24-extraction-projection-acceptance.md)
(AC1 coverage map, AC2 coalescing + provenance, AC3 fan-out without fabricated joins,
AC4 banding + static grid, AC5 real-data scale + loud failure). Each criterion names its
owning gate. AC4 and AC5's scale half are browser-only — happy-dom never upgrades the
Perspective custom element — which is why that document also specifies the real-data
itn-recal seed the Playwright gate runs against.

- **Server unit/integration:** denormalization (coalesce precedence, table fan-out,
  independent stacking, scalar repetition, empty-cell omission), row universe
  (union of references, refs with zero records in a schema), pagination
  (`total_references`, offset/limit on references), enriched-cell provenance,
  latest-submitted-wins across users, batch query count (guard against N+1).
- **Frontend unit (vitest):** repository/use-case against the new contract; grid
  row/column adapter (manifest → Perspective schema + rows); click-URL contract
  builder; guard behavior.
- **Contract:** `gen:api` drift gate regenerated for the new endpoint + enriched
  `ProjectionCell`.
- **e2e (Playwright):** `extractions-grid.spec.ts` as above; existing v2 e2e suite
  minus the three deleted specs stays green.

## 5. Ledger (recorded, not built)

- **Arrow IPC streaming** from server to Perspective (the reason Perspective was
  chosen; contract already columnar-friendly).
- **Annotation-mode v2 upgrade** — resolve v2 schema ids at
  `/dataset/{schema_id}/annotation-mode`; flips the cell-click guard on.
- **Embedded review drawer** on the extraction table (reuses kept `ReviewCellInput`,
  widget adapters, submit/draft/discard use-cases); restores e2e submit-path
  coverage.
- **Column visibility config** (which columns per schema appear), then sort/filter.
- **Record-extent hover glow + provenance tooltip** via the datagrid style listener.
- **Migrate `V2RecordsTable`/search surfaces** onto enriched projection cells where
  useful.
- Nav/`index.vue` integration of `/extractions`.

## 6. Scope boundary

In: new workspace projection endpoint + enriched `ProjectionCell`, table-value
`list[dict]` extension (§3.4), `/extractions` Perspective page, deletions per §3.5,
tests per §4.
Out: everything in §5; any v1 dataset/annotation-mode changes; SDK changes beyond
regenerated types (additive cell fields are backward-compatible for #231).

## 7. Integration references — Perspective × Vue 3 / Nuxt 4

Perspective 4.x (`@perspective-dev/*`, all at 4.5.2 as of 2026-07-20):

- **Importing & WASM bootstrap** (the page this design's bundling follows):
  <https://perspective-dev.github.io/guide/how_to/javascript/importing.html> —
  Vite `?url` imports of `perspective-server.wasm` + `perspective-viewer.wasm`,
  `perspective.init_server(fetch(…))` / `perspective_viewer.init_client(fetch(…))`,
  Vite `target: esnext`.
- **Loading data**: <https://perspective-dev.github.io/guide/how_to/javascript/loading_data.html> —
  `client.table(data | schema)`, `viewer.load(table)`, sharing one `Table` across
  viewers (relevant if the review drawer later mounts a second viewer).
- **Guide root / architecture**: <https://perspective-dev.github.io/guide/>
- **`@perspective-dev/viewer` web-component API** (attributes, `restore()` for
  locking the static config, plugin selection, themes):
  <https://perspective-dev.github.io/> → "JavaScript → `@perspective-dev/viewer`
  Web Component".
- **Bundler example (closest to our Nuxt 4/Vite setup)**:
  <https://github.com/perspective-dev/perspective/tree/master/examples/vite-example>
- **Framework-wrapper example (pattern for our Vue wrapper component)**:
  <https://github.com/perspective-dev/perspective/tree/master/examples/react-example>
  — note there is **no official Vue/Nuxt example**; the React one shows the
  custom-element lifecycle (load on mount, `delete()` on unmount) to mirror in
  `onMounted`/`onBeforeUnmount`.

Vue 3 / Nuxt 4 custom-element integration:

- **Vue 3 — using web components in Vue**:
  <https://vuejs.org/guide/extras/web-components.html> — `compilerOptions.isCustomElement`
  so `<perspective-viewer>` isn't resolved as a Vue component; passing DOM
  properties vs attributes.
- **Nuxt 4 — vue compiler options in `nuxt.config.ts`**:
  <https://nuxt.com/docs/api/configuration/nuxt-config#vue> (`vue.compilerOptions`).
- **Nuxt 4 — client components** (background; not needed here since `ssr: false`):
  <https://nuxt.com/docs/guide/directory-structure/components#client-components>
- **Vite — explicit `?url` asset imports** (WASM binaries):
  <https://vite.dev/guide/assets.html#explicit-url-imports>
- **Vite — `build.target`** (`esnext` requirement):
  <https://vite.dev/config/build-options.html#build-target>
