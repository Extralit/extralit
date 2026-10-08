# v2 Frontend Vertical Slice — Design Spec

> **Historical note (2026-07-26):** The `/api/v2` parallel tree described in this document was folded back into `/api/v1`. See `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`. This document is kept as a historical record; its API paths, models, and file references may no longer exist.

**Date:** 2026-07-09
**Status:** Proposed design (frontend phase of the schema-centric v2 model)
**Parent spec:** `2026-06-27-schema-centric-data-model-design.md` (§19 points here)
**Author:** brainstorming session (Jonny + Claude)

## 1. Goal & scope

Build the first v2 UI vertical slice — **schemas → records → search → annotation** — as
an isolated module alongside the v1 frontend, consuming the shipped `/api/v2` surface
(spec §7, §17.5). The slice proves the schema-centric UX end-to-end.

**In scope (this build):**
- Schema list page; schema detail page (records table + FTS search via `:search`).
- Read-only schema inspection: columns (`columns_cache`), versions, questions.
- v2 module skeleton (`v2/` DDD layout, DI registration, generated API types),
  vitest component tests with mocked repositories, one e2e happy path (remote chromium).

**Out of scope (ledger, §8):** schema authoring/creation wizard (SDK covers authoring),
question CRUD UI, span questions (server rejects, spec §17.3), Queue UI (Phase 5),
markdown/table sub-modes of the text widget, similarity search, v1 retirements (§9 of
the parent spec — recorded there, executed at Phase 6).

## 2. Module architecture — isolated `v2/` mirroring v1's DDD layout

New top-level `v2/` directory, structurally a sibling twin of `v1/`:

```
v2/
  domain/
    entities/        # Schema, SchemaVersion, ColumnMeta, V2Record, RecordsPage,
                     # Question
    usecases/        # get-schemas, get-schema-records, search-records,
                     # submit-reference-review, save-review-draft
  infrastructure/
    api/
      openapi.json         # checked-in snapshot of GET /api/v2/openapi.json
      generated/v2-api.ts  # openapi-typescript output (types only, committed)
    repositories/    # SchemaRepository, V2RecordRepository, AnnotationRepository,
                     # ProjectionRepository — thin, hand-written, v1 pattern
    storage/         # Pinia stores via v1/store/create.ts::useStoreFor (reused as-is)
  di/                # loadV2DependencyContainer(nuxtApp)
components/v2/       # feature components for this slice (reuse components/base/*)
pages/schemas/…      # (routes, §3)
```

Rules of the boundary:
- `v2/` may import from `v1/` only: `v1/store/create.ts`, `v1/infrastructure/services/*`
  (axios extension, auth, routes, notifications), and extracted shared leaf inputs
  (§5). It must NOT import v1 entities (`Dataset`, `Record`, `Question`,
  `QuestionAnswer`) or v1 repositories — those die at Phase 6.
- v1 never imports from `v2/`.
- DI: `plugins/3.di.ts` calls `loadDependencyContainer(...)` then
  `loadV2DependencyContainer(...)` — same ts-injecty container, disjoint registrations.
- Reuse-don't-fork: shared leaf inputs are **extracted** to a v1-free location and v1
  is re-pointed at them (§5); nothing is copy-pasted into `v2/`.

## 3. Decision 1 — Route namespace & terminology: `/schemas/*`, UI says "Schema"

**Routes** (no `/v2/` prefix in user-facing URLs; v1 owns `/dataset/*`, so the
namespaces are disjoint by noun):

| Route | Page |
|---|---|
| `/schemas` | Schema list (per workspace) |
| `/schemas/[id]` | Records table + search for one schema |
| `/schemas/[id]/settings` | Read-only: columns, versions, questions |

**Terminology: the v2 UI says "Schema", superseding parent-spec §3's "UI calls it a
Dataset" for the v1/v2 coexistence window.** Rationale:
- During coexistence, "Dataset" would label **two different entities** (v1 Argilla
  dataset, v2 schema) in one navigation — actively confusing.
- One name across UI ↔ API ↔ SDK ↔ docs; the API and SDK already say schema.
- All copy goes through i18n keys (`schemas.*`, `review.*`), so a product-driven
  rename after v1 retires is a translation-file change, not a refactor.

Alternatives rejected: keep "Dataset" (coexistence collision, above); "Extraction
Table" (three-syllable label for nav chrome; revisit post-retirement if user feedback
wants it).

## 4. Decision 2 — API client: openapi-typescript types + hand-written v1-pattern repositories

**Generate types, hand-write repositories.**

- A small server script dumps `api_v2.openapi()` to the checked-in
  `v2/infrastructure/api/openapi.json` (deterministic; no running server needed in CI).
- `openapi-typescript` (devDependency, zero runtime) generates
  `generated/v2-api.ts` (`paths` / `components` types), committed.
- Repositories stay thin hand-written classes in the exact v1 pattern — constructor
  takes the shared axios instance (baseURL `/api`, so paths are `/v2/...`), methods
  map endpoints to domain entities — but request/response shapes are the **generated
  types**, so contract drift becomes a compile error.
- Drift gate: an npm script `gen:api` regenerates both files; CI re-runs it and fails
  on `git diff` (same pattern as generated icons).

Alternatives rejected:
- **Hand-written types (v1 status quo):** the v2 API is evolving phase-by-phase;
  silent drift is the known failure mode of v1's `infrastructure/types`.
- **Full client codegen (orval / openapi-generator / openapi-fetch):** generates its
  own HTTP runtime, bypassing the shared axios interceptors (auth header injection,
  `AxiosCache`, `AxiosErrorHandler`) and fighting the ts-injecty repository DI. Types
  are the valuable artifact; the transport already exists.

## 5. Decision 3 — Widgets: extract 4 leaves, rebuild the container, rebuild table lean

Grounded in a survey of the Argilla-inherited widgets. The universal v1 pattern:
every widget takes a live `Question` entity prop and **mutates**
`question.answer.values` in place (emits are navigation-only). The container and the
`QuestionAnswer` lifecycle are therefore not portable; several leaves are.

| Widget | v1 shape | Verdict |
|---|---|---|
| `LabelSelection` (serves single + multi label) | ~750 LOC, renders a plain `{id, text, value, isSelected}[]` | **Extract** — already data-shaped; add `modelValue`/`update:modelValue` |
| `RatingMonoSelection` | ~300 LOC, plain value list | **Extract** |
| Ranking `DndSelection` | ~450 LOC, already has an adapter seam (`ranking-adapter.js`) | **Extract** — re-point the adapter at plain data |
| `ContentEditableFeedbackTask` (text leaf) | portable core of ~530 LOC text-area | **Extract leaf only** — drop suggestion-tabs + markdown/table sub-modes from the slice |
| Table (`base-render-table/RenderTable.vue`) | ~2,200 LOC tabulator subsystem hard-wired to `v1/domain/entities/table`, `Question`, and 3 v1 viewmodels (LLM extraction, reference tables) | **Rebuild lean** (below) |
| `Questions.component.vue` container + `QuestionAnswer` entities | mutable-entity lifecycle, keyboard-loop orchestration | **Rebuild** as `ProjectionReviewForm` (§7) |
| Span | — | **Excluded** — server 422s `type=span` (§17.3) |

**Extraction mechanics (reuse-don't-fork):** move the four leaves to
`components/base/inputs/` as controlled, v1-free components (props + `modelValue` +
emits; no `Question` import). v1's thin wrappers (`SingleLabel.component.vue` etc.)
are re-pointed to the moved files and keep doing entity↔props adaptation on the v1
side. Net: one implementation, two consumers, v1 deletable at Phase 6 without
touching the leaves.

**Lean table cell editor (rebuild, ~300 LOC target):** a controlled tabulator-tables
wrapper (dependency already present) for `table` questions. Column definitions derive
from the question's bound columns' `columns_cache` entries (dtype → editor, §6);
value is the question's JSONB dict (keys ⊆ bound columns, matching the server's
structure-only validation). The v1 subsystem's reference-table lookups and
LLM-extraction viewmodels are v1-coupled features, not table editing — they do not
port. If the lean editor grows toward feature parity later, that is a new design
conversation, not scope creep here.

## 6. Decision 4 — `review_widgets` → widget selection: a four-level precedence

`columns_cache` entries are `{name, dtype, nullable, review}` where `review` is the
out-of-band per-column overlay (parent spec §13). Questions are the review-config
primitive (§3, §17). The mapping:

1. **Reviewable cells (questions): `question.type` + `question.settings` select the
   form widget.** Authoritative — the server validates values against exactly these
   settings (§17.3), so the UI must render from the same source.
2. **Inside a `table` question:** each bound column's cell editor comes from that
   column's `columns_cache.review.type` if present, else the dtype default:
   `str→text`, `int/float→number`, `bool→checkbox`, `datetime→date`.
3. **Non-question context fields** (read-only, §17.0): renderer from
   `columns_cache.review` hint if present, else dtype default. `review.type` values
   mirror question-type names where applicable; an unknown `review.type` falls back
   to the dtype default (forward-compatible — the overlay is free-form JSONB).
4. **Question-creation defaults (future schema editor):** `review` pre-fills the
   suggested question type per column. Recorded so the vocabulary is designed for it;
   not built in this slice.

So `review_widgets` never *overrides* a question's widget — it covers the two places
questions don't reach (table sub-columns, context fields) plus authoring defaults.

## 8. Testing strategy

- **Domain unit (vitest):** dtype→widget defaults; search criteria serialization.
- **Component (vitest + @vue/test-utils, mocked repositories):** register mock
  repositories in the ts-injecty container (v1's `di/__mocks__/useResolveMock`
  pattern); schema list/detail pages against mocked
  `SchemaRepository`.
- **Contract:** the `gen:api` drift gate (§4) is the API contract test.
- **e2e (Playwright, remote chromium via ccui):** the prioritized scenario set in
  §10.2 — not just one happy path; a review of merged PRs #225/#227/#228/#229 found
  the frontend will be the first client to exercise several server seams end-to-end.
  Runs against `npm run dev` on `0.0.0.0` with the browser at the ccui container;
  The stale Argilla `e2e/` specs are explicitly not a gate. New specs live in `e2e/v2/`.
- **Lint:** the existing eslint 10 flat config + prettier 3 cover `v2/` with no new
  config surface.

## 9. Open items (resolve during planning)

- Exact server home for the openapi-dump script (`extralit_server` CLI subcommand vs
  a `scripts/` one-liner) — planning detail, not design.
- Whether the schema list becomes the app home (`/` currently lists v1 datasets) or
  a nav sibling during coexistence — recommend nav sibling now, home swap at Phase 6.
- i18n: new `schemas.*` / `review.*` key families; no reuse of "dataset"-keyed copy.
- Whether the schema detail page exposes a "rebuild index" affordance
  (`POST /schemas/{id}:rebuild-index` → `{indexed: n}`, may take tens of seconds) —
  the only recovery from a silently-swallowed sync failure (§10.1-D).

## 10. E2E review addendum (2026-07-10) — from merged PRs #225/#227/#228/#229

A subagent review of the merged server phases (Phase 2 records = #225/#227, Phase 3
LanceDB = #228, Phase 4 annotation = #229) mapped what the pytest integration suites
already cover versus what only a real-stack E2E exercises. Integration coverage is
strong (real Postgres, real app object over ASGI, real lancedb on tmp dirs, real
Pandera validation), but every API test authenticates with an `X-API-Key` header,
mocks the S3 body fetch, and drives ASGI in-process — so the seams below reach
production untested until this slice's E2E runs them.

### 10.1 Spec sections to review carefully (highest-risk assumptions)

- **A — §4 API client / auth: the frontend is the first bearer-token client of
  `/api/v2`.** No server test sends `Authorization: Bearer` or a CORS `Origin` to a
  v2 route (v1's auth router is mounted on v2 but only API-key auth is exercised).
  The axios-interceptor-parity argument in §4 therefore rests on an untested server
  path — the token flow must be the *first* E2E scenario, not an assumed given.
- **B — §3 routes: DOI-with-slash encoding through the real chain.** Server tests
  send literal slashes via ASGI; `encodeURIComponent`'d `%2F` through uvicorn — and
  through the Nuxt dev proxy, which already bit the Vue 3 migration once with `/api`
  path-stripping — is untested, and the `/projection/references/{reference:path}`
  route has no slash test at all (only the Phase-3 records route does).
- **C — §7 draft support: the draft/discarded response lifecycle has ZERO server
  tests at any level.** The form's `save-draft` emit depends on: a draft response
  must NOT surface in the projection (its `status==submitted` filter), and a
  discarded response must revert the cell to the suggestion. Verify server behavior
  early in implementation — before building draft UX on it.
- **D — schema detail page (§1/§8) search: eventual consistency is the contract.**
  Search may miss a just-written record (best-effort sync), `total` can exceed
  returned items even within a page (stale Lance ids skipped on PG hydration), FTS
  totals saturate at 10,000, an unknown filter column raises a 500-class error (not
  422) so the UI must only offer known columns, and `ge`/`le` with `null` silently
  matches nothing. Pagination math must treat `total` as approximate.
- **E — §6/§7 question-name keying fragility.** Questions can't be renamed
  (`QuestionUpdate` has no `name`), but delete+recreate changes the name and
  orphans stored `response.values` keys — they vanish from the projection and
  re-submitting them 422s ("non-configured").

### 10.2 E2E scenario set (priority order)

1. **Auth + smoke:** sign in (bearer token via the v1 auth router on `/api/v2`) →
   schema list → schema detail renders records. Covers seam A.
5. **Search round-trip:** upsert a record (fixture) → FTS search finds it → filtered
   search (status/scalar) → assert graceful rendering when the index is empty/stale
   (seam D; also the first real write→search freshness check anywhere).
6. **Multi-annotator isolation:** users A and B submit different values for the same
   record; each sees only their own value in the projection (server filters by
   requesting user — untested with two users at the projection level).
8. **Required-question 422 rendering:** submit with a required question empty →
   both 422 body shapes render as actionable form errors.

### 10.3 Out of frontend scope (reported upstream, recorded here so they're not lost)

- **compose `worker` service mounts no `extralitdata` volume** — its Lance dir is a
  throwaway container FS; a reindex run in the worker builds an invisible index.
  **FIXED 2026-07-10:** `docker-compose.yaml` worker now mounts
  `extralitdata:/var/lib/extralit`, sharing the server's Lance dir (the mount
  parent spec §15 said Phase 5 would need).
- **MinIO `object_version_id` pinning degrades silently on unversioned buckets**
  (pre-existing/HF-Spaces buckets); version-pin correctness needs a server-side E2E
  (publish v1 → publish stricter v2 → upsert pinned to v1 must pass).
- **`:bulk-upsert` custom verb + `base_url` sub-mount through HF-Spaces ingress** —
  SDK/deployment E2E, not this slice (the slice never bulk-upserts).
- Cheap integration-test gaps worth adding server-side: the "Lance hit id missing
  from PG is skipped" branch; float/datetime field JSON round-trip through Pandera
  coercion.
