# Fold v2-into-v1 — Deferred Follow-ups

> Source: final whole-branch review of `feat/ENG-36-server-v2-to-v1` (base plan
> `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`), plus the `minor (deferred)` items
> logged throughout `.superpowers/sdd/2026-07-26-fold-v2-into-v1/progress.md`. Nothing here
> blocks merge — the two Critical and the Important-3/5 findings from that review were fixed
> in the same commit(s) that added this file. This is the punch list of what was deliberately
> left for later, with enough context to act on each item without re-deriving it.
>
> **Update (2026-07-28):** the 19 open roborev reviews on this branch (jobs 283–301, one per
> commit) were triaged and closed. Roughly half of their findings were already stale — fixed by
> a later commit on the same branch. Of the rest, six were fixed in the roborev pass (see
> §0), two Highs need a product decision and are recorded as §7 and §8, and the remainder are
> folded into §9 below. Section 1's description of the republish consequence was wrong and has
> been corrected.

## 0. Fixed in the 2026-07-28 roborev pass (no longer open)

For the record, so these are not re-derived from the closed reviews:

- **`SchemaQuestion` rename** (job 297): the fold left two `export class Question` and two
  incompatible `QuestionType` symbols side by side under `v1/domain/entities/` — the
  annotation one (`question/QuestionType.ts`, a `class extends String`) and the schema one
  (`schema/Question.ts`, a string union). Renamed to `SchemaQuestion`/`SchemaQuestionType`/
  `SchemaQuestionOption` in `schema/SchemaQuestion.ts`, matching the `SchemaRecord` precedent,
  and updated the three importers.
- **Republish now emits `dataset.updated`** (job 301): gating `published` on the draft→ready
  transition left a republish emitting *nothing*, so a consumer never learned versions 2..n
  existed. `publish_version` now emits `updated` on the `else` branch, with context- and
  handler-level tests asserting the event type differs between first publish and republish.
- **Webhook assertion on the `PUT /publish`-then-schema-version flow** (job 301): that flow is
  what distinguishes the implemented `was_already_ready` guard from a "this is not version 1"
  alternative; it now has its own `WebhookFactory` + `HIGH_QUEUE.count` assertions.
- **`"boolean"` added to `_ES_TYPE_BY_COLUMN_DTYPE`** (job 284): pandas emits `bool` for a numpy
  bool column and `boolean` for the nullable extension dtype. Only the former was mapped, so the
  same logical type took two incompatible ES mappings depending on the Pandera spelling.
- **`test_list_dataset_questions` unskipped** (job 290): its skip reason (`missing 'use_table'`)
  no longer held; the expected settings dict gained `use_table`/`columns` and the test passes.
- **e2e `auth-smoke` matcher** (job 299): the `waitForResponse` was armed *before* `signIn`, and
  `/api/v1/me/datasets` has a second in-app caller (`DatasetRepository.fetchFeedbackDatasets`)
  that fires param-less on the post-login landing page — so the assertions were latching onto the
  home page's request, not the schemas page's. Now armed after `signIn` and matched on the
  `workspace_id` param only `getSchemas` sends. Also dropped the dead `/references/` guard in
  `extractions-grid.spec.ts` and the stale "first bearer-token client" rationale.

## 1. ES mapping evolution: `put_mapping` for republish-added columns is not implemented

**What's missing:** `contexts/schema_versions.publish_version` now guards `create_index` with
an `index_exists` check (Critical 2's fix), so a republish against an already-existing index
skips index creation entirely. That is correct for *not crashing*, but it means a column added
by a republish (a legal operation — dtypes are immutable, but new columns are always allowed)
is tracked as a `Field` row and nowhere else. It is not added to the Elasticsearch/OpenSearch
mapping.

**Corrected 2026-07-28 — the consequence is a write failure, not a query gap.** This doc
previously hedged that values would be "silently dropped or rejected … depending on how the
record write path handles unmapped fields". The answer is deterministic and checkable:
`_configure_index_mappings` sets `"dynamic": "strict"` at the mapping root and
`_mapping_for_fields` adds no override of its own (unlike `metadata`), while
`_map_record_to_es_document` → `_map_record_fields_to_es` emits an entry for *every*
`dataset.fields` row. So the next record write after such a republish carries
`fields.<new_column>` into a strict index with no mapping for it and Elasticsearch rejects it
with `strict_dynamic_mapping_exception` — `PUT /datasets/{id}/records/bulk` fails outright.
**Until this item lands, a republish that introduces new column names leaves the dataset
unwritable.** The interim options are (a) accept that and document it (current state — the code
comment in `publish_version` now says so), or (b) reject a republish that introduces new column
names with an `UnprocessableEntityError` in the same pre-write pass as `_reject_dtype_changes`,
so the failure stays localized to the publish call instead of surfacing later at an unrelated
endpoint. (b) is a semantic narrowing of "new columns are always allowed" and needs a decision.

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

## 7. DECISION NEEDED — annotators lost read access to the schema/extraction record views

**Severity: High.** Introduced by this fold (roborev job 295), and a real user-visible
regression rather than a code-hygiene issue.

`SchemaRecordRepository` (`v1/infrastructure/repositories/SchemaRecordRepository.ts`) — which
backs the whole `pages/schemas/[id]/` view via `useSchemaRecordsViewModel` — calls:

- `GET /v1/datasets/{id}/records`, authorized by `DatasetPolicy.list_records_with_all_responses`
- `POST /v1/datasets/{id}/records/search`, authorized by `DatasetPolicy.search_records_with_all_responses`

Both are `actor.is_owner or (actor.is_admin and await actor.is_member(...))` — **admin/owner
only**. The deleted `SchemaPolicy.list_records` they replaced was
`actor.is_owner or await actor.is_member(...)`, i.e. any workspace member including annotators.
So an annotator who could browse and search `/schemas/{id}` under v2 now gets 403 on both calls
and the page is empty for them.

Every current test is an axios mock asserting a URL the test itself supplies, so nothing catches
the role change. The sibling `ProjectionRepository` in the same commit *did* pick the `/me/`
variant, so the inconsistency is internal to this change.

**Options:**
- **(a)** Point `searchRecords` at `/v1/me/datasets/{id}/records/search`
  (`api/handlers/v1/datasets/records.py:341`, the annotator-scoped twin, already exists). There
  is **no `/me/` equivalent for the list path**, so this alone does not restore the annotator —
  the initial page load still 403s.
- **(b)** Relax the list route to `DatasetPolicy.list_records` (member-readable), restoring v2's
  behaviour. Widens who can see all responses on a v1 route that annotation datasets also use.
- **(c)** Add a `/me/datasets/{id}/records` list twin scoped like the search one.
- **(d)** Declare `/schemas` admin-only by design and hide the nav entry for annotators.

(c) is the cleanest and matches the existing `/me/` precedent; (b) is the smallest diff but
changes an existing v1 route's authorization for annotation datasets too. Needs a call before
implementation, plus a policy-level test pinning the intended role either way.

## 8. DECISION NEEDED — `publish_version` can create a `ready` dataset with zero questions

**Severity: High** as filed (roborev jobs 286/287/290), **partially resolved in practice.**

The original finding was that `publish_version` sets `dataset.status = DatasetStatus.ready`,
while `QuestionCreateValidator._validate_dataset_is_not_ready` (`validators/questions.py`)
rejects question creation on a `ready` dataset — making "publish the Pandera body, then bind a
question to a declared column" impossible.

**What actually happened:** the e2e seed (commit `4256b7f`) established a working order —
**create questions before publish, then `PATCH /questions/{id}` the `columns` bindings after** —
because `QuestionUpdateValidator` does *not* call `_validate_dataset_is_not_ready`. So the flow
is reachable; it is just non-obvious. That ordering is now the de-facto contract and §4 below
depends on it.

**What is still genuinely open:** `publish_version` bypasses `DatasetPublishValidator`
(`validators/datasets.py`), so it can put a dataset in `ready` with **zero questions** — a state
`PUT /datasets/{id}/publish` explicitly refuses to create, and from which no question can ever be
added (create is blocked by `ready`; there is nothing to PATCH). That dataset is permanently
unconfigurable.

**Options:** (a) run the relevant `DatasetPublishValidator` checks in `publish_version` too;
(b) relax `_validate_dataset_is_not_ready` for `current_schema_version_id IS NOT NULL` so
schema-backed datasets stay configurable after publish; (c) don't flip `status` in
`publish_version` at all and leave `PUT /datasets/{id}/publish` as the sole ready transition.
(b) also removes the need for the create-before-publish dance entirely, which would simplify §4.
Whichever is chosen, document the intended lifecycle — it is currently only discoverable by
reading the e2e seed.

## 9. Open roborev findings carried forward (jobs 283–301)

Triaged 2026-07-28; the reviews are closed, so this is the surviving record. Grouped by area,
each with the job it came from. None block merge.

### Server — correctness / semantics

- **(287)** `test_schema_versions.py`'s `_mock_put_object` patches `files_ctx.put_object` but not
  the `Depends(files_ctx.get_s3_client)` that resolves *before* the handler body — so every one
  of those requests still constructs a `LocalFileClient(settings.home_path)`, creates
  directories under the developer's `~/.extralit`, and caches it in the process-global
  `shared_resources`. Register `files_ctx.get_s3_client` in `api_v1.dependency_overrides`, or
  patch `helpers.create_s3_client`.
- **(288)** The `reference` predicate is written twice — inside `_build_list_records_query` and
  hand-rolled onto `total_query` in `contexts/records.list_dataset_records`. The next filter
  added to the builder will silently not apply to the count, reproducing the bug that fix closed.
- **(290)** `columns` is only on the `text` and `table` settings triples, but
  `QuestionColumnBindingValidator`'s error message advertises every scalar type. With pydantic's
  default `extra='ignore'`, `{"type": "label_selection", "columns": ["a"]}` returns **201** with
  the binding silently discarded. Either add `columns` to the remaining bindable types or
  restrict the validator to `QuestionType.text` and say so.
- **(290)** `QuestionUpdateValidator` dumps settings without `exclude_unset=True`, so it cannot
  distinguish an omitted `columns` from an explicit `null`, while `contexts/questions.update_question`
  dumps *with* it and therefore does persist the clear. Nothing breaks today (clearing needs no
  validation) but the two disagree.
- **(292)** `contexts/projection.py`'s DuckDB staging layer still speaks v2 vocabulary
  (`questions(question_id, schema_id, schema_name, …)`, `q.schema_id`) while the Python half is
  renamed to `dataset_*`. `_INSERTS` binds **positionally** into all-`VARCHAR` columns, so
  reordering either side silently produces wrong column names in the grid instead of raising.
  Rename and switch to named inserts.
- **(292)** A `table` question whose `settings["columns"]` is absent or empty contributes no
  manifest column and no cells — it vanishes from the grid with no error. Reachable:
  `TableQuestionSettings.columns` defaults to `None` and the binding validator returns early on
  `None`. The non-table branch emits a column unconditionally, so the two paths treat "no
  binding" in opposite ways. Pick one.
- **(294)** `index/mapping.py`'s module docstring says the manifest is "the list of column dicts
  derived from a schema version's `Field` rows", but every function reads `column["dtype"]` at
  the *top level* — the flat `columns_cache` shape. A `Field` row nests `dtype` under `settings`,
  so passing them raises `KeyError`. No adapter exists. Since `index/` has no production callers,
  this docstring is the only spec of the contract — and it is wrong for the ENG-36 implementer.

### Server — tests

- **(286, 285, 284)** Three `pytest.raises(Exception)` broad catches remain in fold-touched files
  (`tests/unit/contexts/test_schema_versions.py:150`, `tests/unit/validators/test_column_fields.py:68`);
  narrow to the typed exception with `match=`. Several new assertions also lack `match=`
  anchors (`test_field_settings.py`).
- **(285)** The `ColumnFieldSettingsUpdate` dict-merge path — the entire reason that schema is
  partial — is untested. Nothing asserts a `dtype`-only PATCH preserves the stored
  `nullable`/`review`, so a switch to `fill(replace_dict=True)` would pass the whole suite.
- **(291)** `test_patch_rejects_an_invalid_column_binding`'s non-persistence assertion is vacuous:
  `TextQuestionFactory.settings` never sets `columns`, so `stored.settings.get("columns") is None`
  holds whether or not the PATCH was rejected. Seed a valid binding first.
- **(291)** The column-binding PATCH tests do not pin the `selectinload(Dataset.fields)` eager
  load they were written to protect — the handler shares the test's session and identity map, so
  `dataset.fields` is served from session state. Add `db.expunge_all()` before the PATCH.
- **(293)** `test_extraction_response_side_effects.py` never asserts
  `search_engine.partial_record_update` — the index write that actually carries the derived
  `completed` status, and the exact junction the module's docstring names. Delete that line from
  `distribution.py` and all four tests stay green.
- **(293)** No `discarded` case: `ResponseUpsert` is a three-member union and only submitted and
  draft are covered. Discard is the branch this fold reasoned about explicitly when removing
  `V2RecordStatus.discarded`.
- **(293)** Index assertions are argument-blind (`assert_awaited()` with no args pinned).
- **(293)** Third hand-rolled copy of the "redirect a context's own session back at the test
  session" workaround; promote to a shared `tests/conftest.py` fixture.
- **(296)** The non-null `current_schema_version_id` case is pinned only on `GET /datasets/{id}`,
  not the `GET /me/datasets` list the frontend filter actually uses.
- **(300)** `api_v1.dependency_overrides.pop(get_search_engine, None)` in a `finally` deletes the
  key rather than restoring the `async_client` fixture's own override — harmless as written, but
  it is the copy-paste template for the next one, and the failure it produces (a later test
  reaching a real Elasticsearch) is slow to diagnose.
- **(301)** `_RealMappingSearchEngine` constructs a real `ElasticSearchEngine`, which constructs a
  real `AsyncElasticsearch` client that is never closed — surfaces as an "Unclosed client
  session" `ResourceWarning` at GC in an unrelated later test. `_configure_index_mappings` reads
  nothing off `self`, so the client is pure overhead.
- **(283)** `tests/unit/api/test_api_mounts.py`'s comment claims a `base_url` fix that did not
  happen — `_app.py`'s module-level `app` *is* `create_server_app()`'s return value, wrapper
  included, so the assertion still fails under a non-`/` `EXTRALIT_BASE_URL`.
- **(283)** The alembic recovery instructions in
  `13da2d87e660_add_schema_versions_and_record_reference.py` are dialect-wrong (the collision hits
  SQLite too) and internally out of order (`schema_versions` cannot be dropped "BEFORE upgrading"
  while five tables still FK into it). `extralit-server/CLAUDE.md` points readers there.

### Server — API shape

- **(287)** `list_schema_versions` returns a bare JSON array while every other v1 collection
  endpoint returns an `{items: [...]}` envelope. Adding pagination later becomes breaking.
- **(288)** `reference` is filterable on `GET /datasets/{id}/records` but is not in the ES
  document or mapping, so it cannot be filtered or sorted on the search endpoint — two listing
  surfaces on one resource disagree about what is queryable, with nothing recording that the
  omission is deliberate.
- **(294)** `settings.lancedb_uri`'s pydantic `description` embeds the Linear id "ENG-36" — a
  user-facing string surfacing in operator config docs. Keep the ticket pointer in
  `index/__init__.py`'s docstring instead.
- **(294)** `index/base.py` and `index/mapping.py` still take `schema_id: UUID` and build
  `schema_`-prefixed table names, and `union_columns(caches:)` keeps the `columns_cache`-era
  parameter name, though `Schema` no longer exists as a model.
- **(296)** The SDK's `DatasetModel` (`extralit/_models/_dataset.py`) omits
  `current_schema_version_id`, and its default `extra="ignore"` drops it silently — so the
  frontend can tell a schema-backed dataset from a plain one and the SDK cannot, from the same
  endpoint.

### Frontend

- **(295)** `RecordsPage`'s comment claims `total` is "Authoritative: v1's Elasticsearch-backed
  list/search endpoints return an exact count", but only the search path is ES-backed; the list
  path is Postgres with `total: int | None = None` and a standing server TODO. When the
  `?? 0` fallback fires the page renders a literal `0` above populated results. Relatedly,
  `pages/schemas/[id]/index.vue` still gates "next" on a full page rather than
  `currentOffset + pageSize < page.total`, so it can advance onto an empty page.
- **(297)** `v1/domain/entities/search/SearchCriteria.ts` sits beside the unrelated annotation
  `SearchTextCriteria extends Criteria` with nothing in either file saying which family it
  belongs to and no compiler-visible collision to force the issue. Add a docstring naming the
  endpoint, or move it under `v1/domain/entities/schema/`.

### e2e / demo

- **(298)** `e2e/extraction/seed/seed_v2_e2e.py` still carries the v2 name in its filename and in
  the values it writes — `SCHEMA_NAME = "e2e_v2_slice"`, `EMPTY_SCHEMA_NAME = "e2e_v2_empty"`,
  `WORKSPACE_NAME = "e2e-v2"`, `REFERENCE = "10.1000/j.e2e-v2"`, output key `schemaId`. A freshly
  seeded stack renders "e2e_v2_slice" in the UI the extraction specs assert against.
- **(298)** The `country` fixture comment justifies parking `"KE-control"` by citing
  `index/mapping.py::record_to_row`, which has zero production callers. The live invariant is
  `search_engine/commons.py::_build_text_query` scoping a fieldless `q` to `fields.*` — same
  outcome, different reason. A change to that scoping would break `search-roundtrip.spec.ts`
  while the comment kept vouching for the old reasoning.
- **(298)** `demo/seed_demo_workspace.py` — see §4. It fails fast rather than 404ing obscurely,
  but is still unmigrated.
