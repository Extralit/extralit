# Session Handover — Extralit OSS Audit & Issue Filing

**Date:** 2026-05-10
**Branch at start:** `sparshr04/github-copilot-auth-ui`
**Outcome:** 11 GitHub issues filed (#203–#213) covering security, CI, docs, backend/frontend architecture, and a new schema-agnostic data model.

---

## What we worked on and what got done

1. **Full-repo OSS audit** across four areas, run as parallel Explore agents:
   - Documentation (root + per-component)
   - Backend (`extralit-server/`)
   - Frontend (`extralit-frontend/`)
   - CI/CD (`.github/workflows/`, Docker, Tilt, compose)

2. **Deeper structural audit** focused on architecture, organization, and cross-cutting issues (layering, god modules, coexisting patterns, monorepo coordination, type drift).

3. **Architecture redesign for the frontend**, with Vuex+Pinia preserved:
   - Drafted a feature-sliced layout (`src/features/<x>/{api,store,types,components,composables}.ts`) to replace the heavy DDD pattern in `/v1`.
   - Strangler migration policy: legacy `/v1` and `/store` frozen; new work goes in `features/`.

4. **Schema-agnostic data-model design** (architecture only, not the schema language):
   - One `payloads` table with JSONB `data`, immutable versioned `schemas` resource.
   - `SchemaEngine` interface for pluggable validation.
   - Validation runs once at the write boundary; queryable fields via projections.

5. **Distillation + filing**: deduped all findings into 27 candidate issues presented as a checkbox list. User selected 11. All filed against `Extralit/extralit` as #203–#213.

---

## What worked and what didn't

### Worked
- **Parallel Explore agents** for the four audit areas — produced ~2000 words of concrete findings with file:line references in one round.
- **User-driven prioritization** via the checkbox interview pattern — let the user pick from a deduped list rather than receiving a top-down recommendation.
- **Direct `gh issue create`** in parallel once the label mapping was known — all 11 issues filed in one batch.

### Didn't work / got fixed
- **`gh` permission prompts timed out twice** before the first issue could be filed. Fix: user retried; once approved, subsequent calls in the same session were auto-allowed.
- **Initial `gh issue create` failed**: used invented labels (`ci`, `docker`, `bug`, `architecture`, `tooling`, `lint`, `cleanup`, `repo`) that don't exist in the repo.
  - Fix: ran `gh label list` once, then mapped requested labels to the existing set: `infrastructure`, `deployment`, `refactor`, `documentation`, `good first issue`, `backend`, `frontend`, `epic`.
- **Audit produced surface-level findings on first pass** (security/bugs only). Fix: user pushed for "structural, organizational, architectural" — second pass with re-scoped agents surfaced the high-leverage items (DDD overhead, type duplication, layering violations).

---

## Key decisions made and why

| Decision | Why |
|---|---|
| **Keep both Vuex and Pinia** | User constraint. Avoids big-bang migration risk; new code uses Pinia, legacy untouched. |
| **Replace DDD with feature-sliced** | DDD imposes 4–6 file hops per call (DI registry → repo → use-case → view-model → component). Optimizes for human + agent ergonomics: one folder = one feature = everything you need. |
| **Strangler migration, not rewrite** | `/v1` is too large to port at once. Rule: only migrate when feature is already being touched substantively. |
| **Schema-agnostic via JSONB + versioned schemas** | Avoids per-shape table migrations as users define new extraction schemas. Architecture is opaque to schema language — JSON Schema today, swappable. |
| **Validation at boundary only** | Trust internal data after write. Avoids defensive re-validation in handlers. Tradeoff: must be religious about the boundary, since Postgres can't enforce JSONB shape. |
| **File 11 issues, not all 27** | User curated. Higher signal-to-noise; everything filed has a real owner intent behind it. |
| **Map invented labels to existing ones** | Avoid label sprawl. Repo already has a small, coherent label set; respect it. |

---

## Lessons learned and gotchas

- **Always run `gh label list` before `gh issue create --label …`** — invented labels fail the whole call (no partial creation).
- **First-pass audits skew toward security/bugs.** To surface architectural issues, the prompt has to explicitly exclude surface-level findings and name the structural categories you want.
- **`gh` permission prompts can time out** in this environment. If the first call times out, the user has to actively click approve; subsequent calls in the same session reuse the grant.
- **Heavy DDD in a JS/TS codebase is expensive for LLMs**: the `useResolve()` indirection means an agent reading a component must traverse DI registrations to find the implementation. Plain imports + colocation drastically reduce cognitive load.
- **Three-way type drift (server / SDK / frontend) is the single biggest invisible risk.** Each side hand-codes the same types. Worth its own issue (filed concept lives inside #209/#210 follow-ups; not a standalone issue yet).
- **Argilla→Extralit rebrand is half-done in frontend only.** SDK and server are clean. Filed as #211.

---

## Clear next steps

### Immediate (security — not filed but flagged in audit)
1. **Rotate compromised secrets**: `extralit-server/.env.dev` (JWT key, MinIO creds), `docker-compose.yaml` Postgres/MinIO passwords, `constants.py` `DEFAULT_PASSWORD`/`DEFAULT_API_KEY`. Treat as leaked.
2. **Remove wildcard CORS** in `api/handlers/v1/files.py:62,135`.
3. **Sanitize `v-html`** sites in frontend (5+ components).
4. Consider filing these as issues — they were in the deduped list as **S1, S2, S3** but not selected.

### Filed (just need owners)
- **Quick wins first** (low risk, high signal): #203 (uv cache), #204 (docs), #210 (uv workspaces), #211 (rebrand sweep), #212 (untrack editor dirs), #213 (bd decision).
- **Architecture sequence**: #206 (ARCHITECTURE.md) → #207 (ESLint rules) → #208 (reference feature). These three should land in order.
- **Backend cleanup**: #205 (route handlers through `contexts/`).
- **Big new capability**: #209 (schemas + payloads tables). Foundation only; downstream issues will be needed for migration of existing entities, indexed projections, and frontend `<SchemaForm>`.

### Not filed but worth considering
- **OpenAPI codegen for frontend types** — kills the three-way type drift. Was R2 in the dedup list.
- **SDK ↔ Server contract tests** — was R3.
- **`continue-on-error` removal in CI** — was C1; concrete security hardening.
- **Top-level `permissions:` on workflows** — was C2.

---

## Map of important files

### Audit context (read these to understand what was reviewed)
- `extralit-server/src/extralit_server/api/handlers/v1/files.py` — wildcard CORS bug
- `extralit-server/src/extralit_server/constants.py:24-26` — committed default credentials
- `extralit-server/.env.dev` — committed secrets (rotate)
- `extralit-server/src/extralit_server/models/database.py:38` — model→schema layering violation
- `extralit-server/src/extralit_server/contexts/workflows.py` — 909 LOC god module
- `extralit-server/src/extralit_server/search_engine/commons.py` — 1010 LOC god module
- `extralit-frontend/v1/` — legacy DDD; frozen under new architecture
- `extralit-frontend/components/.../RenderTable.vue` — 1207 LOC god component
- `extralit-frontend/nuxt.config.ts:80` — `disableVuex: false` (both Vuex and Pinia loaded)
- `extralit-frontend/tsconfig.json:11` — `strict: false`
- `docker-compose.yaml` — hardcoded passwords, floating `latest` tags, no healthchecks
- `.github/workflows/extralit.yml`, `extralit-server.yml` — `continue-on-error` on tests
- `AGENTS.md` — Python version mismatch with pyproject.toml; references nonexistent per-component AGENTS.md

### New files to be created (per filed issues)
- `extralit-frontend/ARCHITECTURE.md` (#206)
- `extralit-frontend/src/features/<reference-feature>/` (#208)
- `extralit-frontend/src/features/<x>/{api,store,types}.ts` pattern (#206 documents, #208 exemplifies)
- `extralit-server/src/extralit_server/.../schemas/` and `payloads/` modules (#209)
- Root `pyproject.toml` with `[tool.uv.workspace]` (#210)
- `examples/README.md` (#204)
- Per-component `AGENTS.md` files or removed references (#204)

### Generated this session
- `HANDOVER.md` (this file)

### Issue references
- All filed issues: https://github.com/Extralit/extralit/issues/203 through /213
