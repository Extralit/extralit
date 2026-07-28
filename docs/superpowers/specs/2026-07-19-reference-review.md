# Handoff — ReferenceReview slice: design/correctness interrogation brief

> **Historical note (2026-07-26):** The `/api/v2` parallel tree described in this document was folded back into `/api/v1`. See `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`. This document is kept as a historical record; its API paths, models, and file references may no longer exist.

**Date:** 2026-07-19
**Context branch:** `polish/v2-ui-shell-integration` (PR #232). The ReferenceReview slice itself is **already on `develop`** (merged via #230).
**Goal of next session:** interrogate the Presentation, Domain/infra, and Backend layers for **user design, API design, correctness, and performance** — then decide whether to redesign-in-place, or replace.

---

## Why this brief exists (the reframing)

I was asked whether the reference-review files are half-baked sprawl worth deleting, this is a critical review of the ReferenceReview vertical slice across three layers to determine if it is worth redesigning.

**Where the value actually sits:** the *presentation* (~360 LOC) is the under-designed, replaceable part. The *domain/infra + backend contract* (~1,200 LOC, well-tested) is the asset a redesign reuses — deleting it means rebuilding it.

---

## The full surface (the "any others")

### Presentation (~360 LOC) — the redesign target
- `components/v2/review/ReviewRecordCard.vue` (137) — one card per schema-record; renders context as raw `<dl>`, **dumps orphaned values as `JSON.stringify`**, per-record submit/save-draft/discard footer.
- `components/v2/review/ProjectionReviewForm.vue` (32) — thin list wrapper over records.
- `components/v2/review/ReviewCellInput.vue` (151) — dispatches to existing annotation widgets by question type.
- `components/v2/review/ReviewProvenance.vue` (44) — agent/score/source line.
- `pages/references/[...reference].vue` (69) — catch-all route (slashed DOIs), shell-wrapped in #232.

### Domain / infra (~1,100 LOC) — the asset
- `v2/domain/entities/review/ReferenceReview.ts` (65) — aggregate: reference → ReviewRecord[] (+ cells, context, orphaned values, draft).
- `v2/domain/entities/review/widget-adapters.ts` (88, +120 test) — **maps v2 questions ↔ existing annotation widget option models** (label/rating/ranking/table). High reuse value.
- `v2/domain/entities/review/widget-mapping.ts` (25, +43 test), `SuggestionHint.ts` (22, +20 test), `response-values.ts` (9, +24 test).
- `v2/domain/usecases/get-reference-review-use-case.ts` (131, **+245 test**) — assembles projection + suggestions + responses + drafts into the review model.
- `v2/domain/usecases/submit-reference-review-use-case.ts` (25, +38 test), `save-review-draft-use-case.ts` (16), `discard-review-use-case.ts` (17).
- `v2/infrastructure/storage/ReferenceReviewsStorage.ts` (27) — Pinia store keyed by reference.
- `v2/infrastructure/repositories/ProjectionRepository.ts` (49) — GET `/v2/projection/references/{encoded}`.
- `v2/di/di.ts` — registrations (partial file).
- `components/v2/schemas/V2RecordsTable.vue` — the **entry-point link** `/references/${encodeURIComponent(reference)}?workspace_id=…` (partial file).

### Backend (~124 LOC + 2 integration tests)
- `extralit-server/src/extralit_server/api/v2/projection.py` (31) — `GET /projection/references/{reference:path}` → `ProjectionView`. Note the deliberate `/projection/...` prefix to avoid the greedy `:path` on `GET /references/{reference:path}` shadowing it.
- `extralit-server/src/extralit_server/contexts/v2/projection.py` (70) — cross-schema assembly.
- `extralit-server/src/extralit_server/api/schemas/v2/projection.py` (23) — `ProjectionView` DTO.
- Tests: `tests/integration/api/v2/test_projection.py`, `tests/integration/contexts/v2/test_projection.py`.

### e2e (depend on the slice)
- `e2e/v2/{review-loop,draft-lifecycle,slashed-reference}.spec.ts` — `goto` the `/references/<encoded>` URL directly; exercise suggestion→response, drafts, slashed-DOI. (These pass **serially**; parallel flakes on shared-schema `rebuild-index` contention — see the PR #232 HANDOVER.)

---

## Interrogation matrix (start here next session)

Concrete hotspots I noticed while mapping — not yet verified as defects, but the places to point the review.

### Presentation — **user design** (the weakest layer)
- Orphaned values rendered via `JSON.stringify` (`ReviewRecordCard`) — placeholder, not a designed affordance.
- Context shown as bare `<dl>`; provenance is a minimal agent/score line — no visual hierarchy for "what am I reviewing / what changed."
- Multi-record references: one card stacked per schema-record with **no overview, no navigation, no bulk/keyboard flow**; submit/save-draft/discard are per-card only.
- Loading/empty/error states are minimal (single `V2Empty`/`BaseLoading`).
- **Question for design:** what *is* the review unit — a reference, a schema, a single projected record? The current model shows all records for a reference flat; is that the intended mental model?

### Domain/infra — **correctness**
- `ReviewRecordCard.cleanValues()` drops `null`/`undefined`/`""` before emit. Interaction with **required-question enforcement** (server-side) and with legitimately-empty answers needs a hard look — can a user intentionally clear a value, and does that round-trip?
- `get-reference-review-use-case.ts` merges projection + suggestions + responses + drafts. Check merge precedence (draft vs saved response vs suggestion), and staleness (Pinia `ReferenceReviewsStorage` cache vs re-fetch).
- `ProjectionRepository` does `encodeURIComponent(reference)` and the backend uses `{reference:path}` — verify no double-encode / slash-decoding mismatch (the `slashed-reference` spec covers the happy path; probe `%2F` vs `/`, `#`, `?` in DOIs).
- `widget-adapters` rebuild option arrays on every `modelValue` change (watch in `ReviewCellInput`) — verify no state loss on external resets (draft restore/discard).

### Domain/infra + Presentation — **performance**
- No pagination on the review page — loads **all** records for a reference at once. Fan-out cost if a reference spans many schemas/records.
- `ReviewCellInput` watch rebuilds label/rating/ranking option arrays per keystroke/change — check re-render cost with many cells.
- Repeated single-record hydration vs batch.

### Backend — **API design + performance**
- `ProjectionView` shape: is one endpoint returning the whole cross-schema projection the right granularity, or should it paginate / stream / split per schema?
- `contexts/v2/projection.py` (70 LOC) assembles across schemas — check query count (N schemas × per-record hydration from Postgres); watch for N+1.
- `workspace_id` is a **required query param** on the projection GET — confirm that's the right scoping contract (vs deriving from auth/reference).
- Suggestion/response/draft are **separate PUT/POST** calls from the client (see `submit`/`save-draft`/`discard` use-cases) — is a batched review-submit endpoint warranted?
- The `/projection/...` vs `/references/{reference:path}` routing split (shadowing workaround) — is the URL design coherent for the SDK (#231) too?

### Backend — **correctness**
- FTS/index eventual consistency already characterized (see PR #232 HANDOVER): reseed leaves a cold index; `:rebuild-index` is needed to warm it. Relevant if projection reads from the index anywhere.
- The `prefilter`-kwarg 500 (FTS + scalar filter) was fixed in #232 (`4fa777343`) — confirm the projection path doesn't have a sibling issue.

---

## Options on the table (decision pending — this is yours)

1. **Leave #232 as-is** — reference-review stays shell-integrated; a later redesign replaces only the presentation (~360 LOC), reusing domain + backend. Lowest friction. The BaseButton fix + 3 e2e specs need the page to render regardless.
2. **Hide the entry point in #232** *(my recommendation if you want it visibly parked)* — remove the `V2RecordsTable → /references` link (and optionally un-shell the page) so it's unreachable/unblessed, but the code + backend + domain remain for the redesign. e2e specs still pass (they `goto` directly).
3. **Revert the whole slice** — separate PR removing frontend + backend projection + e2e, reconciled against SDK #231. Only if the product call is "pull this direction entirely." **Not recommended** — throws away ~1,200 LOC of tested, reusable machinery + a working backend contract you'd rebuild.

**Recommendation:** #2 to park it pending design, #1 if fine leaving it reachable. Avoid #3.

---

## Next steps

1. **Decide the parking option** (#1/#2/#3 above) for PR #232 before it merges. If #2, the change is small: drop the `/references` link in `components/v2/schemas/V2RecordsTable.vue` (and optionally revert the `pages/references/[...reference].vue` shell wrap).
2. **Run the design/brainstorm session** on the *presentation* using `superpowers:brainstorming` — anchor on the "what is the review unit?" question above.
3. **Do the layer interrogation** using the matrix: consider a focused `/code-review` (or the multi-agent `/code-review ultra`) scoped to the review + projection files for correctness/perf, in parallel with the UX design work.
4. **Backend API review** — validate the `ProjectionView` granularity and the projection query fan-out (N+1) before building new UI on top.
5. Keep the domain/infra + backend contract as the stable base; treat the four `components/v2/review/*.vue` + the page as replaceable.

---

## Map of important files

**Presentation (redesign target)**
- `extralit-frontend/components/v2/review/ReviewRecordCard.vue`
- `extralit-frontend/components/v2/review/ProjectionReviewForm.vue`
- `extralit-frontend/components/v2/review/ReviewCellInput.vue`
- `extralit-frontend/components/v2/review/ReviewProvenance.vue`
- `extralit-frontend/pages/references/[...reference].vue`
- `extralit-frontend/pages/references/useReferenceReviewViewModel.ts` (+ `.test.ts`)

**Domain / infra (asset — reuse)**
- `extralit-frontend/v2/domain/entities/review/` — `ReferenceReview.ts`, `widget-adapters.ts`, `widget-mapping.ts`, `SuggestionHint.ts`, `response-values.ts` (each with tests)
- `extralit-frontend/v2/domain/usecases/` — `get-reference-review-use-case.ts`, `submit-reference-review-use-case.ts`, `save-review-draft-use-case.ts`, `discard-review-use-case.ts`
- `extralit-frontend/v2/infrastructure/storage/ReferenceReviewsStorage.ts`
- `extralit-frontend/v2/infrastructure/repositories/ProjectionRepository.ts`
- `extralit-frontend/v2/di/di.ts` (registrations)
- `extralit-frontend/components/v2/schemas/V2RecordsTable.vue` (entry-point link)

**Backend**
- `extralit-server/src/extralit_server/api/v2/projection.py`
- `extralit-server/src/extralit_server/contexts/v2/projection.py`
- `extralit-server/src/extralit_server/api/schemas/v2/projection.py`
- `extralit-server/tests/integration/api/v2/test_projection.py`
- `extralit-server/tests/integration/contexts/v2/test_projection.py`

**e2e**
- `extralit-frontend/e2e/v2/{review-loop,draft-lifecycle,slashed-reference}.spec.ts`

**Cross-references**
- `HANDOVER.md` — PR #232 (v2 UI shell) session handoff, incl. the serial-vs-parallel e2e reliability note.
- #230 (`8343da1f8`) — original merge of this slice. #231 — open SDK slice that shares the v2 API surface.
