# Python SDK v2 — schema-centric client, agentic CLI, async performance

**Date:** 2026-07-13
**Status:** Approved design, pending implementation plan
**Companions:** `2026-06-27-schema-centric-data-model-design.md` (server model),
`2026-07-09-v2-frontend-vertical-slice-design.md` (frontend precedent this design mirrors)

## Problem

The backend grew a second data model (`/api/v2`: schema-centric, versioned,
projection-based) alongside the Argilla-lineage one (`/api/v1`). The Python SDK
(`extralit/`, v0.6.1) is hardcoded to `/api/v1`: sync-only `httpx.Client`, Argilla
entities (Dataset → Record → Question → Response), and a human-oriented Rich CLI.
It cannot drive the v2 extraction loop at all, and three of its properties block the
intended consumers:

1. **Wrong model.** No client for schemas/versions, version-pinned records,
   column-bound questions, reference grouping, or projections.
2. **Not agentic.** CLI output is Rich tables only — unparseable by agents; no
   stable JSON, no meaningful exit-code contract, heavy imports make every
   short-lived invocation slow.
3. **Sequential I/O.** All HTTP is blocking and serial; pushing large record sets
   or fanning out per-record reads requires user-written loops.

## Decision summary

| Decision | Choice |
|---|---|
| Coexistence | Parallel `extralit.v2` package; v1 untouched; one wheel |
| Contract | Committed `openapi-dump` snapshot → generated Pydantic DTOs (Approach A) |
| Transport | Async-native (`httpx.AsyncClient`) + sync facade |
| CLI | `extralit v2 …` subtree, JSON-first, lazy-imported |
| Primary workflow | LLM extraction pipeline (publish schema → bulk-upsert → suggestions → projections) |
| Scope | Vertical slice (below); responses-write, exports, admin verbs deferred |

Alternatives rejected: **evolve-in-place** (recreates the name-collision /
entity-bending trap the frontend explicitly avoided — a v2 `Record` is not a v1
`Record`); **fully generated client** via `openapi-python-client` (generated
ergonomics fight the agentic-CLI and pipeline goals on every regen); **hand-written
wire models** (silent drift against a quirky contract we already have a dump tool for).

## 1. Package architecture

```
src/extralit/v2/
├── __init__.py           # exports AsyncClient, Client, domain classes
├── _api/
│   ├── openapi.json      # committed snapshot (server `openapi-dump`)
│   ├── _generated.py     # datamodel-code-generator → Pydantic v2 DTOs
│   ├── _transport.py     # httpx.AsyncClient wrapper: bearer auth + refresh, retries
│   └── _errors.py        # error hierarchy + 422 normalizer
├── _sync.py              # sync facade (background-thread event-loop portal)
├── models/               # hand-written domain classes (Schema, SchemaVersion, Record, …)
├── resources/            # Schemas, Records, Questions, Suggestions, Projections
└── cli/                  # `extralit v2 …` subcommands (lazy-registered)
```

Python namespacing removes the frontend's need for `V2`-prefixed names:
`extralit.v2.Record` cannot collide with `extralit.Record`. Entry points are
explicit — `from extralit.v2 import Client` (sync) / `AsyncClient` — never re-exported
from the top-level `extralit` namespace.

**Import wall (reuse-don't-fork, with a hard boundary).** `extralit.v2` imports
nothing from v1 modules, with one documented exception: a shared credentials helper
(env vars + `~/.extralit/credentials.json`), which survives v1 retirement anyway.
v1 never imports v2. The boundary is grep-checkable and gated in CI. Phase 6
retirement deletes v1 packages mechanically.

## 2. Contract layer

`_api/openapi.json` is a checked-in dump of the server's v2 OpenAPI schema, produced
by the existing server CLI (`uv run python -m extralit_server openapi-dump`).
`datamodel-code-generator` (dev dependency, `--output-model-type pydantic_v2.BaseModel`)
turns it into `_generated.py`. Resources type every wire payload from generated DTOs;
hand-written shapes never touch the wire.

Two CI gates, mirroring the frontend's:

- **No-drift:** regenerate from the committed snapshot and diff; any change fails.
- **Snapshot-vs-server:** the committed snapshot must match a fresh `openapi-dump`
  from the server tree at the same monorepo revision.

## 3. Transport & performance

- **Async-native.** One `httpx.AsyncClient` per client instance: pooled connections,
  transport `retries=5`, 60s default timeout — matching v1's proven settings.
- **Auth.** v2 routes accept both backends (verified: `security/authentication/
  provider.py` registers `APIKeyAuthenticationBackend` and
  `BearerTokenAuthenticationBackend` on `get_current_user`). The SDK default is the
  API-key header — same credentials as v1, no token lifecycle. Bearer JWT via
  `POST /api/v2/token` (username/password, 30-min access / 30-day refresh) is also
  supported; the transport transparently refreshes once on 401, then re-raises.
- **Sync facade.** `Client` mirrors every `AsyncClient` method by dispatching to a
  background-thread event loop (a "portal"), not `asyncio.run` — so sync usage works
  inside Jupyter, where a loop is already running. Sync mirrors are generated
  mechanically from the async resource surface, not hand-maintained.
- **Bulk pipeline.** `records.bulk_upsert()` auto-chunks at the server's 500-item
  cap and dispatches chunks with bounded concurrency (default semaphore of 4,
  configurable) plus an optional progress callback. Deletes chunk at the 100-id cap.
  Pushing 50k records is one SDK call.
- **Immutable-data caching.** Schema versions are immutable → cached in-client by
  `(schema_id, version)`. Question name↔id maps cached per schema, invalidated on
  question writes through the same client.

## 4. Domain resources — the extraction loop

The resource layer is the anti-corruption layer: every wire quirk lives here once,
so nothing above it knows about `snake_case` bodies, double-wrapping, or id-vs-name
keying.

```python
async with AsyncClient(api_url=..., api_key=...) as xl:
    schema  = await xl.schemas.get_by_name(workspace_id, "clinical_trials")
    version = await xl.schemas.publish(schema.id, pandera_schema, review_widgets={...})
    await xl.records.bulk_upsert(schema.id, rows, reference="10.1000/xyz")   # auto-chunked
    page    = await xl.records.search(schema.id, text="tumor size",
                                      filters=[("patient_age", "ge", 18)])
    await xl.suggestions.upsert(record.id, question="dosage", value=..., score=0.9,
                                agent="claude")
    proj    = await xl.projections.get(workspace_id, reference="10.1000/xyz")
```

Resources and the quirks they encapsulate (all confirmed against the server and the
frontend's PR #230 findings):

- **Schemas** — create/get/list/update; `publish()` posts a Pandera body plus
  out-of-band `review_widgets` (Pandera's `to_json()` drops column metadata);
  versions list/get; `columns()` from the current version's cache.
- **Records** — `bulk_upsert` (idempotent on `external_id`, `metadata` is
  patch-like), `search` (text + `(column, op, value)` filters with
  `op ∈ {eq,in,ge,le}`; `total` is approximate — stale index ids are skipped and
  FTS saturates, so pagination never promises exact counts), `list`, `delete`,
  and `references.get()` for the cross-schema reference view. `bulk_upsert`
  accepts list-of-dicts or a pandas DataFrame (pandas imported lazily inside that
  path only).
- **Questions** — list/get per schema. Callers address questions by **name**;
  the resource resolves to **id** via the cached map (suggestions key by id;
  cells and response values key by name — getting this wrong silently detaches
  provenance).
- **Suggestions** — upsert per (record, question) with `value`, `score`, `agent`,
  `type`; list per record.
- **Projections** — `get(workspace_id, reference)` → cells of response ∨ suggestion
  per question with `source` provenance. **Responses (read-only this slice)** —
  `GET` returns literal `null` with 200 when absent (mapped to `None`, not an
  error); values are double-wrapped `{name: {"value": …}}` and unwrapped here.

Domain classes are thin Pydantic models with behavior (e.g. `SchemaVersion.find_column`,
`SearchPage.records`), constructed from DTOs by the resources — same layering the
frontend proved testable without a live backend.

## 5. Agentic CLI

`extralit v2` subcommand tree over the sync facade:

```
extralit v2 schemas     list | get | create | publish | versions
extralit v2 records     upsert | search | list | delete
extralit v2 questions   list
extralit v2 suggestions upsert
extralit v2 projection  get
extralit v2 references  get
```

- **JSON-first.** Every command accepts `--json`; when stdout is not a TTY, JSON is
  the default automatically. JSON shapes are the serialized DTOs — stable because
  they are drift-gated by the contract layer. Rich tables remain the TTY default
  for humans.
- **Exit-code and stream contract.** stdout carries data only; errors are structured
  JSON on stderr (`{"error": {"type", "status", "detail"}}`). Exit codes:
  0 success, 1 API/runtime error, 2 usage error, 3 validation (422).
- **Non-interactive by construction.** Env vars (`EXTRALIT_API_URL`,
  `EXTRALIT_API_KEY` or username/password) and the credentials file; no prompt is
  ever emitted when stdin is not a TTY.
- **Piping.** `records upsert` reads JSONL from stdin or `--file`; `records search
  --limit/--offset` page through cleanly for chaining.
- **Startup budget.** The v2 subtree registers into `cli/app.py` via a lazy callback;
  heavy deps (pandas, pandera, datasets) import only inside the commands that use
  them. Budget: `extralit v2 --help` completes in < 300 ms on the Orin dev host,
  verified with `python -X importtime` in a CI check.

## 6. Error handling

`V2APIError(status, detail)` base → `AuthError` (post-refresh 401),
`NotFoundError`, `ValidationError` (normalizes both server 422 body shapes —
`detail: str` and `detail: [{loc, msg}]`). The CLI maps this hierarchy onto the
exit-code contract. Search totals are documented as approximate rather than
pretending exactness.

## 7. Testing

- **Unit (no server):** pytest + pytest-asyncio + pytest-httpx. Resource tests pin
  each wire quirk by name: double-wrap/unwrap, name↔id suggestion join,
  both 422 shapes, null-response-200, bulk chunking + bounded concurrency +
  mid-batch failure behavior, token refresh on 401. Sync-facade smoke tests run
  inside a live event loop (Jupyter simulation). CLI tests via Typer's runner
  assert `--json` output shapes, stderr error JSON, and exit codes.
- **CI gates:** codegen no-drift, snapshot-vs-server, import-boundary grep
  (`extralit/v2` must not import v1 modules), CLI startup-time budget.
- **Integration (opt-in marker, live stack):** one end-to-end extraction-loop test
  (publish → upsert → suggest → search → projection) reusing the deterministic
  seeding approach from the frontend's `e2e/v2/`.

## Scope

**In this slice:** everything above — contract layer, transport + sync facade,
the five resources, the CLI subtree with JSON-first output, unit tests + CI gates.

**Deferred by design:** responses *write* (submit/draft/discard — the review loop
belongs to a follow-up once the frontend's Phase 5 queue lands), DataFrame/parquet/HF
export, `rebuild-index` and other admin verbs, webhooks, span questions, and the
v1 CLI/SDK retirement (Phase 6) this boundary exists to enable.
