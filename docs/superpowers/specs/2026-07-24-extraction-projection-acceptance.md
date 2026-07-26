# Extraction Projection Viewer — Acceptance Criteria

**Date:** 2026-07-24
**Branch:** `feat/v2-ui-extraction-grid`
**Derives from:** `2026-07-20-extraction-table-design.md` §3.1–§3.4 (grid semantics,
backend projection, frontend page, table-value fan-out) and §4 (testing strategy).

## Why this document exists

PRs #233 (server projection endpoint + data layer) and #234 (`/extractions` Perspective
grid) were built against **synthetic fixtures only** — invented studies in
`extralit-frontend/demo/seed_demo_workspace.py` plus a single-reference e2e seed. Nothing
has exercised the viewer against real extraction data, and the unit suite structurally
cannot see the Perspective lifecycle at all (happy-dom never upgrades the custom element).

A real-data seed is being built from `itn-recal_postgresql_v16_08-07-2025.dump` — 58 papers
× 4 table schemas plus flat `Publication` records. These criteria are written **first**, so
that the seed is built against a stated target rather than retrofitted to whatever it
happens to produce.

Each criterion names the gate that owns it:

| Tag | Gate |
|---|---|
| **[srv]** | `extralit-server` pytest |
| **[unit]** | `extralit-frontend` vitest |
| **[e2e]** | Playwright against a live stack + the itn-recal seed |

---

## AC1 — The grid is a complete coverage map

Rows are the union of every distinct reference across all schemas in the workspace; columns
are every question of every schema (`Schema.question[.subcol]`), **including schemas with
zero records**. A missing (reference, schema) pair renders as empty cells — never as an
absent row or a dropped column.

- **Given** schema A has records for refs r1,r2 and schema B only for r2, **when** the
  viewer loads, **then** rows exist for both r1 and r2 and B's columns render empty on
  r1. *[srv, e2e]*
- **Given** a schema with questions but zero records, **when** the viewer loads, **then**
  its columns still appear in the manifest with every cell empty. *[srv, e2e]*
- **Given** N distinct references spanning more than one page of the endpoint, **when** the
  viewer finishes loading, **then** all N references are displayed and `total_references`
  equals N. *[srv, unit]*

## AC2 — Every cell shows the winning value, with its provenance

Precedence is latest **submitted** response `??` suggestion `??` empty, applied server-side.
Drafts never appear. Cells carry `record_id` + `source` (+ `agent`/`score` for suggestions).

Note the deliberate **record-level** semantic (`contexts/v2/projection.py:166-175`): the
latest submitted *envelope* wins outright; a question absent from that envelope falls back
to its suggestion even when an earlier submitted response answered it. Envelopes are not
merged per cell.

- **Given** a question with both a suggestion and a differing submitted response, **when**
  the viewer loads, **then** the response value renders and the suggestion value appears
  nowhere. *[srv, e2e]*
- **Given** a question with only a suggestion, **when** the viewer loads, **then** the
  suggestion renders and the cell reports `source: "suggestion"` with its agent/score.
  *[srv, unit]*
- **Given** a **draft** (non-submitted) response, **when** the viewer loads, **then** the
  draft value never renders — the suggestion or empty shows instead. *[srv, e2e]*
- **Given** two users have submitted responses to the same record, **when** the viewer
  loads, **then** the latest-updated envelope's values render. *[srv]*
- **Given** raw `record.fields` values that differ from the suggestion/response values,
  **when** the viewer loads, **then** no raw field value appears anywhere in the grid.
  *[e2e — this is the assertion that caught the hollow gate in `9ab8d5242`]*

## AC3 — Table questions fan out into stacked rows without fabricating joins

Per-reference row count = max fan-out across all its table questions, minimum 1. Scalars
repeat identically on every fan-out row. No cartesian product; shorter tables leave empty
cells on trailing rows. Cross-schema row alignment is **positional only and carries no
meaning** — join keys are ordinary cell values.

- **Given** a reference with a 3-row table question plus scalar questions, **when** the
  viewer loads, **then** it occupies 3 rows and each scalar repeats identically on all 3.
  *[srv, e2e]*
- **Given** table question X with 2 rows and table question Y with 5 rows on one reference,
  **when** the viewer loads, **then** the reference occupies 5 rows (not 10) and X's
  columns are empty on rows 3–5. *[srv]*
- **Given** a table value delivered as a bare dict rather than a list, **when** the viewer
  loads, **then** it fans out to exactly 1 row. *[srv]*
- **Given** two schemas related by a join key (`observation_ref` → `Observation.reference`),
  **when** the viewer loads, **then** the join key renders as an ordinary readable cell. *[e2e]*

## AC4 — Reference grouping is legible and the grid is static

Row-banding flips on reference change (Perspective is flat-columnar and cannot merge
cells); toolbar/settings hidden; no sort or filter affordance in v1.

- **Given** consecutive references each fanning out to several rows, **when** rendered in a
  real browser, **then** all rows of one reference share a background tint and adjacent
  references differ — asserted on **computed style**, not class presence. *[e2e]*
- **Given** the viewer has loaded, **when** the surface is inspected, **then** no toolbar,
  settings, sort or filter control is *usable* — asserted on visibility, not DOM presence.
  Perspective does not remove `#settings_button` under `settings: false`; it collapses it to
  0×0 while leaving `display: flex; visibility: visible` (verified in-browser 2026-07-24), so
  a DOM-absence assertion fails against a correctly static grid. *[e2e]*

## AC5 — The viewer survives real data at scale and fails loudly

Scale target is ~100s of references × ~5 schemas × ~30 columns loaded into one Perspective
table. Non-scalar values must not blank the grid; failures must surface rather than
presenting as an empty or perpetually-loading grid.

- **Given** the full itn-recal seed (58 references × 5 schemas, ~70 columns), **when** the
  viewer loads, **then** the grid paints and every manifest column is present on every row.
  *[e2e]*
- **Given** a cell value that is an array or object (`multi_label_selection`, `ranking`,
  `span`), **when** the viewer loads, **then** it renders as a stable stringified value and
  the `client.table()` call does not reject. *[unit]*
- **Given** the projection request fails, **when** the viewer loads, **then** an explicit
  load-error state is shown — not an indefinite spinner or a silently blank grid. *[unit]*
- **Given** the user switches workspace mid-load, **when** the superseded response arrives,
  **then** it is discarded and the grid shows the selected workspace. *[unit]*

---

## Coverage note

AC1–AC3 are largely provable today by `[srv]`. AC4 and the scale half of AC5 are provable
**only in a browser** — happy-dom never upgrades the `<perspective-viewer>` custom element,
so vitest cannot observe the Perspective lifecycle at all. That is precisely the gap the
itn-recal seed closes.

## The seed the browser-only gates run against

Built outside this repo (`~/Projects/Extralit/data/`), loaded through the **v2 HTTP API**
rather than direct SQLAlchemy inserts so that `QuestionBindingValidator` and schema
publication gates are genuinely exercised, then snapshotted as a SQLite file.

| Legacy (dump) | v2 |
|---|---|
| workspace `itn-recalibration` | workspace, same name |
| `data/schemas/*.json` (pandera) | `Schema` + `SchemaVersion.body` |
| `records.metadata->>'type'` | which `Schema` the record belongs to |
| `records.metadata->>'reference'` (bibtex key) | `V2Record.reference` |
| `fields.extraction` (LLM, `to_json(orient="table")`) | **suggestion**, `agent="gpt-3.5-turbo"` |
| `responses.extraction-correction` | **response** on the same question |
| `data: [{...row}, …]` | table-question value = `list[dict]` → fan-out |

Mapping the LLM blob to a suggestion and the human correction to a response is what makes
AC2's coalescing actually exercised, and it matches the source semantics exactly.
`record.fields` is never projected, so it carries a minimal provenance stub — deliberately
**distinct** from the annotation values, which is what AC2's last criterion asserts against.

Shapes covered:

- **Publication** — flat, one scalar question per column (proves AC1, AC2).
- **Observation**, **ITNCondition** — table, one `table` question bound to data columns
  **plus `reference`** (proves AC3 fan-out, stacking, scalar repetition).
- **ClinicalOutcome**, **EntomologicalOutcome** — table, bound to data columns **plus
  `observation_ref` and `itncondition_ref`** (proves AC3's join-keys-as-columns criterion
  and AC5's scale criterion).

**Non-obvious transform:** pandera declares `reference` / `observation_ref` /
`itncondition_ref` under `index`, not `columns`. `columns_cache` derives only from pandera
`columns`, and questions can only bind what is in `columns_cache`. The transform therefore
**promotes index entries into `columns`** in the SchemaVersion body. Without that, the join
keys are unbindable and invisible, and AC3's last criterion cannot pass.

**Cleaning is auditable, not asserted:** unparseable `extraction` blobs are dropped,
`""`/`"NA"`/`"n/a"` become null, all scalars are stringified; ~3% dangling
`observation_ref`/`itncondition_ref` are **kept** — real mess is the point. A
`transform-report.json` records counts of everything dropped or coerced.

## What the grid will honestly look like

Fan-out is global across all five schemas, so a paper with 30 `ClinicalOutcome` rows and 1
`Publication` row yields 30 grid rows with `Publication` repeated and `Observation` blank
past its own row count. Five schemas × ~70 columns is a very wide, sparse grid with no sort,
filter, or column visibility. Join keys are readable as cells; the *positional* alignment
between schemas is meaningless — and that will be visible.
