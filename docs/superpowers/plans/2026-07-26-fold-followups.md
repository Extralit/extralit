# Fold v2-into-v1 — Deferred Follow-ups

> Source: final whole-branch review of `feat/ENG-36-server-v2-to-v1` (base plan
> `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`), plus the `minor (deferred)` items
> logged throughout `.superpowers/sdd/2026-07-26-fold-v2-into-v1/progress.md`. Nothing here
> blocks merge — the two Critical and the Important-3/5 findings from that review were fixed
> in the same commit(s) that added this file. This is the punch list of what was deliberately
> left for later, with enough context to act on each item without re-deriving it.

## 1. ES mapping evolution: `put_mapping` for republish-added columns is not implemented

**What's missing:** `contexts/schema_versions.publish_version` now guards `create_index` with
an `index_exists` check (Critical 2's fix), so a republish against an already-existing index
skips index creation entirely. That is correct for *not crashing*, but it means a column added
by a republish (a legal operation — dtypes are immutable, but new columns are always allowed)
is tracked as a `Field` row and nowhere else. It is not added to the Elasticsearch/OpenSearch
mapping, so records written after the republish will have that column's value silently dropped
or rejected by the `"dynamic": "strict"` index (`search_engine/commons.py::_configure_index_mappings`),
depending on how the record write path handles unmapped fields.

**Why it wasn't done here:** explicitly out of scope per the human partner's decision for this
fix wave — "Do not attempt to fix ES mapping evolution now."

**What it would take:** on a republish where `index_exists` is true, diff the newly-derived
`field_payloads` against the fields that existed before the upsert, and call
`search_engine.put_index_mapping_request` (already implemented on both backends —
`elasticsearch.py:116-117`, `opensearch.py:108-109` — and already used by
`configure_metadata_property`/`configure_index_vectors` in `commons.py`) with the mapping for
just the new columns, built the same way `_configure_index_mappings` builds column mappings
today. Needs a `_ES_TYPE_BY_COLUMN_DTYPE`-driven mapping-fragment builder factored out of
`_configure_index_mappings` so it can be reused for both the whole-index and the incremental
case.

**Note:** ENG-36 (registering the LanceDB engine as a `SearchEngine` implementation) may
supersede Elasticsearch entirely for schema-backed extraction datasets. If ENG-36 lands first,
check whether this ticket is still needed before implementing it — LanceDB's column-add story
may already be simpler (Arrow schema evolution) than hand-rolling `put_mapping` diffing.

## 2. Field pruning: a column dropped from a new Pandera body leaves its `Field` row behind

**What's missing:** `derive_column_fields` + `Field.upsert_many` only ever *add or update*
fields. If a republish's new Pandera body no longer declares a column that a prior version
did, the old `Field` row for that column is never deleted — it stays in `GET /datasets/{id}/fields`
and in the ES mapping (if 1. above ever gets built) forever.

**Why it wasn't done here:** deferred by explicit instruction — "Field pruning and
name-collision semantics are deferred to tickets."

**Semantic note:** this is a real regression introduced by the fold, not a pre-existing v1
gap. v2's `SchemaVersion.columns_cache` was a wholesale replacement of the column list on every
publish — there was nothing to prune because there was no persisted-and-forgotten row. v1's
`Field` table is append/upsert-only by construction (`Field.upsert_many`'s
`__upsertable_columns__` only ever updates `title`/`required`/`settings` for a matching
`(name, dataset_id)`, and nothing in this codebase issues a `DELETE` against `fields` for a
schema-version-driven column). Fixing this means either (a) diffing old vs. new column names on
every publish and deleting the `Field` rows that dropped out, checking first whether any
`Question.settings["columns"]` binds to the dropped name (and deciding what that means — dangle
the binding? reject the publish?), or (b) deciding pruning is undesirable and instead exposing
"declared by current version" vs. "declared by some prior version" as a `Field` attribute.

## 3. Name collision: a Pandera column colliding with an existing annotation field

**What's missing:** `Field.upsert_many`'s conflict target is `(Field.name, Field.dataset_id)`.
If a Pandera schema declares a column whose name matches an existing `text`/`image`/`chat`/
`custom`/`table` field (created via `POST /datasets/{id}/fields`, not via a schema version),
the upsert overwrites that field's `settings` with `{"type": "column", "dtype": ..., ...}` —
silently converting an annotation-input field into a schema column, which removes it from
record value validation (column fields are "deliberately not value-validated" per
`enums.py`'s `FieldType.column` docstring) without any warning.

**Why it wasn't done here:** deferred by the same explicit instruction as item 2.

**What it would take:** before the `Field.upsert_many` call in `publish_version`, check
whether any `field_payloads[i]["name"]` already exists as a `Field` with
`settings["type"] != FieldType.column`, and reject the publish (`UnprocessableEntityError`
naming the colliding field) rather than silently overwrite. Symmetrical with the dtype
immutability check added in this fix wave (`contexts/schema_versions._reject_dtype_changes`) —
could plausibly live in the same pre-write validation pass.

## 4. Repointing `demo/seed_demo_workspace.py`

**Current state:** the script now fails fast with a clear stderr message and `SystemExit(1)`
(see the header comment and the `if __name__ == "__main__":` guard) instead of hard-failing
obscurely on its first `/api/v2/*` request. It was NOT repointed at `/api/v1` — that's real,
separate work.

**What it would take:** every one of its 13 raw HTTP calls targets a deleted `/api/v2/*` route
and needs a v1-shaped replacement:
- `POST/GET/DELETE /api/v2/schemas` → the v1 `Dataset` CRUD (`POST /api/v1/datasets`, etc.) —
  a "schema" is now just a `Dataset` with a schema version.
- `POST /api/v2/schemas/{id}/versions` → `POST /api/v1/datasets/{id}/schema-versions`
  (`api/handlers/v1/datasets/schema_versions.py`).
- `POST /api/v2/schemas/{id}/questions` → `POST /api/v1/datasets/{id}/questions`, and per Task
  15's finding (`progress.md` Task 15 entry), questions must be created *before* publish and
  PATCHed with `columns` bindings *after* — `QuestionCreateValidator._validate_dataset_is_not_ready`
  rejects binding creation once the dataset is `ready`, which `publish_version` sets
  unconditionally.
- `POST /api/v2/schemas/{id}/records:bulk-upsert` → the v1 records bulk-upsert endpoint, with
  `reference` moved from being implicit to an explicit field (`api/schemas/v1/records.py`).
- `PUT /api/v2/records/{id}/suggestions` / `.../responses` → the v1 suggestions/responses
  endpoints, which take `question_id` rather than a schema-scoped question name.
- `POST /api/v2/schemas/{id}:rebuild-index` → no v1 equivalent exists as a dataset action;
  the closest analog is `cli/search_engine/reindex.py`'s `Reindexer`, not an HTTP route — decide
  whether the demo script should shell out to the CLI or whether this step is simply dropped
  once schema-version publish creates the index itself.
- `GET /api/v2/projection` → `GET /api/v1/workspaces/{id}/projection` (or wherever
  `contexts/projection.build_workspace_view` is mounted — check `api/handlers/v1/`).
- `POST /api/v2/token` → `POST /api/v1/token` (this one is a same-shape rename, not a
  behavior change).

Not part of any CI gate (confirmed in `progress.md`'s Task 15 leftover note), so this can be
scheduled independently of any test-suite concern.

## 5. `_next_version_number` max()+1 race

**Location:** `contexts/schema_versions.py::_next_version_number`.

```python
async def _next_version_number(db: AsyncSession, dataset_id: UUID) -> int:
    stmt = select(SchemaVersion.version).where(SchemaVersion.dataset_id == dataset_id)
    return max((await db.execute(stmt)).scalars().all(), default=0) + 1
```

Two concurrent `POST /datasets/{id}/schema-versions` calls for the same dataset can both read
the same max and both attempt to insert the same `(dataset_id, version)` — the second loses to
the `SchemaVersion` unique constraint with a raw `IntegrityError`. Confirmed (ledger, Task 6
minor (a)) to roll back cleanly; the only residue is an orphaned S3 object at
`schemas/{dataset_id}/v{n}.json` from the loser's `put_object` call, which happened before the
DB insert. Worth fixing only if concurrent publish to the same dataset is a real usage pattern
(e.g. two agents racing to publish); the fix is a `SELECT ... FOR UPDATE` on a per-dataset lock
row, or moving version assignment into the same statement as the insert
(`INSERT ... SELECT max(version)+1 ...`) to make it atomic.

## 6. Remaining deferred minors carried over from the ledger

Everything below is copied from `.superpowers/sdd/2026-07-26-fold-v2-into-v1/progress.md`'s
`minor (deferred)` lines, for the items not otherwise covered above or fixed in this wave
(T7 and T9(a) were fixed in this wave; not repeated here).

- **Task 6 (b):** `schema_versions.py`'s `getattr(metadata, "version_id", None)` is needless —
  `ObjectMetadata.version_id` always exists on the return type of `files_ctx.put_object`.
- **Task 6 (c):** `tests/unit/contexts/test_schema_versions.py`'s
  `test_publish_creates_the_search_index` used `mock_search_engine.create_index.assert_awaited()`
  without pinning the argument; `assert_awaited_with(dataset)` would be tighter. (Note: this
  test's assertion style is unchanged by this fix wave; the new republish tests added alongside
  it do pin arguments/call counts.)
- **Task 8 (a):** the `total` count query under `contexts/records.py`'s reference filter
  (`:220-225`) is correct but untested directly — only `items` is asserted in the existing
  suite.
- **Task 8 (b):** the full-dict-equality test-literal style used across `tests/unit/api/handlers/v1/`
  (e.g. asserting an entire JSON response body as a literal dict) is a pre-existing blast-radius
  problem — any schema field addition touches dozens of test files. A
  `response_model_exclude_unset`-aware partial-assertion helper deserves its own cleanup ticket.
- **Task 9 (b):** `QuestionColumnBindingValidator` has no `min_length` on column-name strings,
  so `columns: [""]` reaches the validator and is rejected only as "not declared" — harmless,
  but asymmetric with field-name validation elsewhere in the codebase.
- **Task 11 (a):** `@pytest.mark.asyncio` markers are redundant under `asyncio_mode="auto"`
  (`pyproject.toml:137`) in several test files touched by the fold; carried verbatim from the
  brief rather than cleaned up.
- **Task 11 (b):** a test `get_async_db` override dropped the `IsolationLevel | None`
  annotation present in the original `conftest.py` — cosmetic typing regression, no behavior
  change.
- **Task 13 (a):** `ExtractionsGrid.client.vue:207` still emits the payload key `schemaId`
  while it now carries a v1 dataset id — the value is correct, only the key name is stale
  relative to the fold.
- **Task 13 (b):** the "discarded" status filter option (`pages/schemas/[id]/index.vue:32`) and
  `V2RecordStatus.discarded` (`V2Record.ts:1`) will silently return zero rows against v1's
  `RecordStatus` (`pending`/`completed` only — `enums.py:53-55`). Pre-existing, not a regression
  from this fold, but a real dead UI affordance worth removing or wiring up.
- **Task 13 (c):** `extralit-frontend/package.json` still lists the now-unused
  `openapi-typescript` devDependency. Removing it touches the lockfile, so it was left for a
  dedicated dependency-cleanup pass.
- **Task 14 (a):** `v1/di/di.ts` imports 16 repositories via the barrel export but the 3
  merged-from-v2 ones by direct path — two import styles in one file. Add the 3 to
  `v1/infrastructure/repositories/index.ts` for consistency.
- **Task 14 (b):** `ExtractionsStorage.ts:4`'s comment still says "v1/v2 useStoreFor" — no v2
  namespace remains anywhere in the frontend tree as of this fold.
- **Task 14 (c):** `composables/useV2Breadcrumbs.ts` still carries a `V2` prefix in its name,
  but it predates this fold's base commit and was never under `v2/` — flagged only because it
  reads as if it violates "nothing carries a V2 prefix" scope, when it's actually pre-existing
  and out of this fold's scope.
