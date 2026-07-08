# Schema-Centric Data Model — Design Spec

**Date:** 2026-06-27
**Status:** Approved design (server data model + API; SDK/frontend follow)
**Author:** brainstorming session (Jonny + Claude)

## 1. Problem

Extralit inherited Argilla's general-purpose-yet-static model. A dataset's "schema"
is only an implicit bag of `Field` rows; records store extracted data as a flat
`records.fields` JSON blob with **no formal binding to a schema or its version**. The
Pandera `DataFrameSchema` that actually describes the extraction shape lives only in
the SDK and as JSON files in workspace object storage — the server never validates
against it. Search runs on an Elasticsearch/OpenSearch abstraction.

We want the **data record to be a first-class citizen that maps to a group of columns
defined by a user-defined, versioned Schema**, building toward a **project-level
extraction table that every record maps toward**. Annotation (Questions / Responses /
Suggestions) becomes a thin per-cell review layer on top of schema columns, not a
parallel primitive. LanceDB (with native schema evolution + vector/FTS indexes)
replaces Elasticsearch.

## 2. Fixed constraints (decided)

1. **Pivot depth — Schema-first, annotation as a thin layer.** Schema + its columns
   are *the* core model. Questions / Responses / Suggestions are an optional per-cell
   review/validation layer. Records are LLM-generated, so span / ranking / rating
   surfaces and distribution/overlap remain important for human-in-the-loop.
2. **Schema home — object-store body + thin DB registry pointer.** The Pandera
   `DataFrameSchema` body lives in object storage with its native versioning
   (`etag` / `version_id` / `last_modified`). A DB registry row carries schema
   identity + version pointer + lineage. (Object store vs DB source-of-truth dynamics
   stay flexible while LanceDB↔annotation↔schema dynamics settle.)
3. **Delivery — parallel v2, migrated gradually.** New schema-centric tables/endpoints
   are built alongside v1 using Alembic. Datasets migrate over gradually; **v1 is then
   deleted — back-compat is explicitly NOT a goal** (keep v1 only as a migration source
   and where a piece is independently useful).
4. **First target — server data model + API.** Fix Schema-as-entity and the
   `Record → schema_version` binding first. SDK and frontend follow.

## 3. Core model decisions (from interview)

- **Postgres is the source of truth** for record cell-values; **LanceDB is a derived
  index** (rebuildable from Postgres), replacing ES entirely.
- **Cell storage = structured JSONB + schema FK.** `record.fields` stays a JSONB map
  keyed by column name, gains a formal `schema_version_id` FK, and is **validated
  server-side against the Pandera schema on write**. No per-schema DDL churn.
- **Schema ↔ Dataset is 1:1, collapsed into one primitive.** The `schema` row *is* the
  extraction table. UI calls it a "Dataset"; the model calls it `Schema`. This removes
  a redundant entity. (If schema-reuse-across-datasets is needed later, split into two
  FK-linked rows then.)
- **A Record pins its own `schema_version_id`.** The Dataset/Schema carries a
  `current_version_id` pointer that advances; older records keep the shape they were
  extracted under. The backing LanceDB table evolves to the column **superset** via
  Lance schema evolution.
- **`reference` (the document) is the cross-schema join key.** A document's full
  "project-level extraction" = the union of its records across every schema that share
  the `reference` (one document-level/singleton row + N table rows per schema).
- **Question is the review-config primitive**, reframed as a binding to schema
  **column(s)**: one column normally, **multiple columns when `type=table`** (a
  sub-table). Suggestion/Response hang off a Question, which resolves to cell(s).
- **The Queue is the first-class UI citizen**, not the Dataset. It is a **persisted**
  entity: ordered walk over `reference`s, cross-Dataset scope, distribution/overlap and
  assignment for human-in-the-loop on LLM output.

## 4. Architecture (Approach A — isolated v2 module)

New isolated module set sharing only `workspaces`, `users`, `documents`, and
auth/security with v1:

- `models/v2/` — SQLAlchemy models for the tables in §5.
- `contexts/v2/` — business logic (schemas, records, validation, index sync, queues).
- `api/v2/` — FastAPI routers mounted at `/api/v2`.
- `index/` (new) — LanceDB index engine + sync; replaces `search_engine/`.

Three stores, clear roles:

- **Postgres** — source of truth: registry, record cell-values, annotation, queue.
- **Object store (S3/MinIO)** — Pandera `DataFrameSchema` bodies, versioned via native
  `version_id`/`etag` (reuse `contexts/files.py`).
- **LanceDB** — one table per schema, derived from Postgres; owns vector + full-text +
  scalar filtering. The `search_engine/` ES/OpenSearch stack is **deleted, not
  reimplemented behind the old ABC.**

## 5. Relational schema (new v2 tables, additive Alembic)

As built: tables `schemas`, `schema_versions`, `v2_records` (v1 owns `records`); renamed
to canonical names on v1 retirement.

| Table | Purpose | Key columns |
|---|---|---|
| `schema` (`schemas`) | **Core entity** = extraction table (≙ "Dataset" in UI). Registry pointer to the Pandera body. Singleton-vs-table is *emergent* from question/column bindings, not a stored kind (§14). | `id`, `workspace_id`→workspaces, `name`, `status` (`draft`\|`published`), `current_version_id`→schema_version (nullable until first publish), `settings` JSONB (guidelines, etc.), `inserted_at`, `updated_at`; uniq(`workspace_id`,`name`) |
| `schema_version` (`schema_versions`) | Immutable version → object-store body + lineage + denormalized column cache. | `id`, `schema_id`, `version` (monotonic int), `object_key`, `object_version_id`, `etag`, `checksum`, `parent_version_id` (lineage, nullable), `columns_cache` JSONB (per-column name/dtype/nullable/review-widget, derived from the S3 body — UI/inspection cache, not a validation source), `review_widgets` JSONB (out-of-band per-column widget overlay, §13), `created_by`→users, `inserted_at`; uniq(`schema_id`,`version`) |
| `record` (`v2_records`, ORM `V2Record`) | One typed row; pins its version; carries the cross-schema join key. | `id`, `schema_id` (CASCADE), `schema_version_id` (pinned, CASCADE), `reference` (indexed), `external_id` (nullable), `fields` JSONB (cells keyed by column; permissive — unknown fields pass through, §14), `metadata` JSONB, `status` (`pending`\|`completed`\|`discarded`, PG enum `v2_record_status_enum`), `inserted_at`, `updated_at`; idx(`schema_id`,`reference`), idx(`reference`); uniq(`schema_id`,`external_id`) |
| `question` | Review config bound to column(s): 1 normally, N if `type=table`. | `id`, `schema_id`, `name`, `title`, `description`, `type` (`text`\|`label`\|`multi_label`\|`rating`\|`ranking`\|`span`\|`table`), `columns` JSONB (bound column names), `settings` JSONB, `required`, `inserted_at`, `updated_at`; uniq(`schema_id`,`name`) |
| `suggestion` | LLM output per (record, question). | `id`, `record_id`, `question_id`, `value` JSONB, `score` JSONB (float \| float[]), `agent`, `type`, `inserted_at`, `updated_at`; uniq(`record_id`,`question_id`) |
| `response` | Human review per (record, user); `values` keyed by question/column → resolves to cells; multiple users per record = overlap. | `id`, `record_id`, `user_id`, `values` JSONB, `status` (`draft`\|`submitted`\|`discarded`), `inserted_at`, `updated_at`; uniq(`record_id`,`user_id`) |
| `queue` | First-class review surface; spans schemas; owns distribution. | `id`, `workspace_id`, `name`, `scope` JSONB (schema ids + filters), `ordering` JSONB, `distribution` JSONB (annotators/reference, completion rule), `status`, `inserted_at`, `updated_at` |
| `queue_item` | One **reference** (document) to review, ordered. | `id`, `queue_id`, `reference`, `position`, `status` (`pending`\|`in_progress`\|`completed`); uniq(`queue_id`,`reference`) |
| `queue_assignment` | Distribution/overlap: who reviews which reference. | `id`, `queue_item_id`, `user_id`, `status`, `inserted_at`; uniq(`queue_item_id`,`user_id`) |

**Reused as-is:** `workspaces`, `users`, `documents` (`documents.reference`/`pmid`/`doi`
become the queue join key).
**Dropped vs v1:** `vectors` + `vectors_settings` (LanceDB owns vectors inline);
`fields` + `metadata_properties` as standalone entities (folded into the Pandera
schema body + `columns_cache`).

## 6. Storage, indexing & validation flow

**Schema publish.** Client/SDK uploads a Pandera `DataFrameSchema` body → object store
(versioned). Server creates a `schema_version` row capturing `object_key` +
`object_version_id` + `etag` + `checksum`, derives `columns_cache` from the body, links
`parent_version_id`, and advances `schema.current_version_id`. The schema's LanceDB
table is created or **evolved** to the new column superset.

**Record write (bulk upsert).** Resolve each record's `schema_version_id` (default =
`current_version_id`). Validation always fetches the Pandera body from the object store
(pinned to the stored S3 `object_version_id`), once per distinct version per request —
Pandera checks (ranges, regexes) exist only in the body, so `columns_cache` is a
UI/inspection cache, not a validation source. Every item is validated (coerce + check)
*before any write*, so one invalid item fails the whole request (all-or-nothing 422).
Non-null fields absent from the schema pass through to `record.fields` unvalidated —
permissive JSONB is intentional (§14). Persist to Postgres (truth). Then **sync** the
row into the schema's LanceDB table (record_id, reference, schema_version_id, status,
column values, metadata; embeddings deferred, §15): Postgres commits first, Lance sync is best-effort,
and `rebuild(schema_id)` is the recovery path — search is eventually consistent by
design. Validation-throughput optimization is deferred (§14 future-work ledger).

**Index engine.** New `index/` package: a LanceDB engine exposing `upsert_records`,
`delete_records`, `search` (scalar filter + FTS), and `rebuild(schema_id)`. Postgres is
authoritative; the Lance table is always rebuildable. Sync is inline on commit for the
first cut (job-queue offload is a later optimization), mirroring v1's proven sync
architecture (same hook points, DI-injected engine, reindex CLI) with a new v2-shaped
engine — not the old `SearchEngine` ABC. `similarity_search` (vector) is deferred to a
separate PDF-chunk-retrieval design session. Phase 3 decisions: §15.

**Reference grouping.** `GET /api/v2/references/{reference}` returns all records across
every schema in the workspace sharing that `reference` — the document's project-level
extraction view that the Queue UI renders.

## 7. API surface (`/api/v2`)

- **Schemas (= Datasets):** `POST /schemas`, `GET /schemas`, `GET /schemas/{id}`,
  `PUT /schemas/{id}`, `DELETE /schemas/{id}`; `GET /schemas/{id}/columns`.
- **Schema versions:** `POST /schemas/{id}/versions` (register body + evolve Lance
  table), `GET /schemas/{id}/versions`, `GET /schemas/{id}/versions/{version}`
  (single-version read: unimplemented; the Phase-4 annotation UI needs it to render
  old-version shapes — see §14 future-work ledger).
- **Records:** `POST /schemas/{id}/records:bulk-upsert` (AIP-136 custom method; ≤500
  items), `GET /schemas/{id}/records?offset&limit&status&reference` (50 default /
  1000 max, exact total), `DELETE /schemas/{id}/records?ids=<csv>` (≤100, 204),
  `POST /schemas/{id}/records:search` (Phase 3, LanceDB: text FTS + scalar filter;
  vector deferred to the chunk-retrieval session, §15).
- **References:** `GET /references/{reference:path}?workspace_id=` (cross-schema
  document view; `:path` because DOIs contain slashes; unknown reference → empty 200 —
  a reference is a join key, not an entity).
- **Questions:** `POST|GET|PUT|DELETE /schemas/{id}/questions`.
- **Annotation:** `PUT /records/{id}/suggestions`, `PUT /records/{id}/responses`.
- **Queues:** `POST|GET|PUT|DELETE /queues`; `GET /queues/{id}/next` (next reference
  for current user per distribution); `POST /queues/{id}/items` (build/refresh from
  scope); `GET /queues/{id}/progress`; assignment endpoints.

## 8. Migration (v1 → v2, gradual)

A per-dataset migrator: for each v1 `Dataset` → synthesize a Pandera `DataFrameSchema`
from its `Field` rows, upload as the first `schema_version`, create the `schema` row;
copy `records` (`fields` JSON → v2 `record.fields`, derive `reference` from the
document link / `external_id` / metadata); copy `questions` (map to column bindings),
`responses`, `suggestions`; build the LanceDB table. Idempotent and re-runnable per
dataset. Once a workspace's datasets are migrated and verified, delete the
corresponding v1 rows/handlers.

## 9. Retirement ledger (lean-up; v1 back-compat not a goal)

### Server (`extralit-server`)

**Delete (replaced by LanceDB / schema-centric model):**
- `search_engine/elasticsearch.py`, `search_engine/opensearch.py`,
  `search_engine/commons.py` (`BaseElasticAndOpenSearchEngine` + ES DSL builders),
  ES-coupled methods in `search_engine/base.py`.
- `cli/search_engine/reindex.py`, `cli/search_engine/__main__.py` (ES reindex CLI).
- `models` `Vector` + `VectorSettings`; `api/handlers/v1/vectors_settings.py`;
  `contexts/records_bulk.py::_upsert_records_vectors`.

**Fold into schema/record v2 (then drop v1 handler):**
- `api/handlers/v1/fields.py`, `metadata_properties.py` → schema `columns_cache`.
- `api/handlers/v1/questions.py`, `suggestions.py`, `responses.py` → thin v2 annotation.
- `contexts/datasets.py` (674 LOC) → split into `contexts/v2/{schemas,records,
  annotation,index}.py`.
- `contexts/distribution.py` → fold into queue distribution logic.

**Audit / likely peripheral (decide per use case):** `api/handlers/v1/chat.py`
(RAG → rewrite on LanceDB or externalize), `models.py` proxy, `webhooks/` +
`webhook_jobs.py`, `imports.py`/`contexts/imports.py`, `contexts/hub.py`.
**Keep:** auth/security, `workspaces`, `users`, `documents`, `files.py` (object store),
`alembic/`, `validators/`, `utils/`, `errors/`.

### Frontend (`extralit-frontend`) — later phase, recorded now

**High (architectural):** `components/features/dataset-creation/*` (creation wizard +
question/field builders), `pages/dataset/[id]/*` routing, `pages/index.vue` (dataset
list home), `pages/new/*`; `v1/domain/entities/{dataset,record,page}`;
`v1/infrastructure/repositories/{DatasetRepository,RecordRepository}.ts`;
the criteria chain (`SortCriteria`, `MetadataCriteria`, `SimilarityCriteria`,
`ResponseCriteria`, `SearchTextCriteria`).
**Medium (Argilla annotation widgets → schema-driven forms):**
`components/features/annotation/container/questions/form/*`
(span, rating, ranking, single/multi-label, text-area), `header/filters/*`,
`header/responses-filter/*`, `container/similarity/*`, `progress/*`,
`v1/domain/entities/distribution`.
**Low (naming/branding/test debt):** `*FeedbackTask*` naming, `e2e/` Argilla baselines,
"dataset"-heavy translation keys, `nuxt.config.ts` argilla doc link.
*(Replaced by: a Queue-first navigation, a schema editor, and schema-driven cell
forms — designed in the frontend phase.)*

## 10. Testing strategy

- **Unit:** Pandera validation (coerce/reject), `columns_cache` derivation, version
  lineage, reference grouping, queue distribution/assignment selection.
- **Contexts (async pytest):** schema publish + version evolution, record bulk-upsert
  with validation, annotation upsert resolving to cells.
- **Index:** LanceDB engine against an ephemeral (tmp-dir) table — upsert/search/
  rebuild; schema-evolution to superset; Postgres↔Lance parity after `rebuild`;
  best-effort sync failure never fails the write request. (Similarity tests arrive
  with the chunk-retrieval phase.)
- **API:** `/api/v2` happy-path + validation-failure + authz per router.
- **Migration:** v1 fixture dataset → v2; record/annotation parity; idempotent re-run.

## 11. Scope boundary (this build)

**In:** v2 Alembic tables (§5); `models/v2` + `contexts/v2` + `api/v2`; Pandera
server-side validation; LanceDB `index/` engine + inline sync + rebuild; reference
grouping; persisted Queue with distribution; v1→v2 migrator; server-side retirements
in §9 that are unblocked by the above.
**Out (later phases):** SDK threading; frontend Queue UI + schema editor + frontend
retirements; job-queue offload of index sync; RAG/chat rewrite.

## 12. Open items to resolve during planning

- Whether a draft version can be edited in place before publish. (The `version` format
  half of this item is resolved: monotonic int, implemented in Phase 1.)
- `reference` derivation rules during migration when no `documents` link exists.
- Whether `response.values` stays keyed-by-question (v1-style) or moves per-question
  rows — current design keeps the v1-style keyed map for minimal churn.

## 13. Resolved during Phase 1 implementation

- **Review-widget storage — side map, not Pandera body metadata (RESOLVED 2026-06-27).**
  The installed Pandera (0.32.0, with pandas 3.0.1) does **not** preserve per-`Column.metadata`
  through `DataFrameSchema.to_json()` / `from_json()` — the metadata is silently dropped. Per the
  Phase-1 plan's documented fallback, the per-column review widget is therefore **not** stored
  inside the Pandera body. Instead it is carried in a side map `review_widgets: dict[str, dict]`
  (column name → widget config): accepted on `SchemaVersionCreate`, persisted as a
  `schema_versions.review_widgets` JSONB column, and merged into each column's `review` entry by
  `derive_columns_cache(body_json, review_widgets=...)`. The Pandera body remains the source of
  truth for column name/dtype/nullable; `review_widgets` is an out-of-band annotation overlay.
- **Single-row record validation tolerates nulls in nullable numpy-int columns (RESOLVED
  2026-06-27).** `pa.Int` maps to numpy `int64`, which cannot hold `None`; coercing a null in a
  nullable Int column to `int64` fails. `validate_record_fields` therefore separates null-valued
  fields out, raises only when a null lands in a non-nullable column, validates+coerces the
  remaining non-null fields against a reduced sub-schema, and re-attaches nulls as `None` in the
  returned mapping. It also rejects a required (non-nullable) column that is entirely omitted
  from `fields` (a `missing` error), and converts coerced values to native JSON types without a
  lossy `DataFrame.to_json` round-trip (numpy scalars via `.item()`, Timestamps as ISO strings)
  so high-precision floats and datetimes survive into `record.fields`.

### Review findings — accepted/deferred (roborev jobs 55–61)

- **`put_object` now propagates the S3 `VersionId` (FIXED).** `contexts/files.py::put_object`
  previously dropped `VersionId`, so `schema_versions.object_version_id` was always NULL on
  versioned buckets; it now mirrors `get_object`.
- **Concurrent same-schema publish race (ACCEPTED for Phase 1, Low).** `publish_version` computes
  `max(version)+1` in Python; two simultaneous publishes can collide on the `(schema_id, version)`
  unique constraint (uncaught → 500) and orphan an uploaded object. Same-schema concurrency is
  rare; inline sync is already slated for job-queue offload later, where this is hardened.
- **Fetch-then-authorize existence signal (ACCEPTED, Low).** v2 read/write handlers return 404 for
  a missing id and 403 for an existing-but-unauthorized one, mirroring the v1 pattern. IDs are
  UUIDs; the disclosure surface is negligible and kept consistent with v1.
- **Models + their migration live in adjacent commits (NOTED).** The roborev per-commit review of
  the models commit flagged the absence of the table migration in that same commit; the migration
  lands in the immediately following commit, and the branch is internally consistent and green.

## 14. Resolved during Phase 2 implementation & 2026-07-06 spec review

- **`kind` (`singleton`|`table`) removed as a schema concept (DECIDED 2026-07-06).**
  Singleton behavior is not a special schema type: a record whose questions are all
  non-table is *implicitly* one row per `reference`. The distinction is emergent from
  question/column bindings (Phase 4), not a stored discriminator, so nothing enforces
  "one row per reference" at the record layer. Code follow-up: drop `schemas.kind` +
  `SchemaKind` (small migration) before Phase 4 builds question bindings on top.
- **Unknown-field passthrough is intentional (DECIDED 2026-07-06).** `record.fields`
  keeps permissive-JSONB semantics: non-null fields absent from the Pandera schema pass
  through unvalidated. No strict/reject mode.
- **Concurrency races stay accepted (REAFFIRMED 2026-07-06).** Publish `max(version)+1`
  and concurrent bulk-upserts on `(schema_id, external_id)` can 500 on unique-constraint
  collision; hardened when record writes move to the job queue.
- **As-built naming.** Tables `schemas` / `schema_versions` / `v2_records`; ORM class
  `V2Record` (a second declarative class named `Record` breaks v1's string-based
  `relationship("Record")` lookups in the shared registry); PG enum
  `v2_record_status_enum`. Canonical names return at Phase 6 retirement. Full Phase 2
  decision table: `docs/superpowers/plans/2026-07-03-v2-records.md`.
- **Upsert update semantics.** Patch-like for `metadata`/`status` (omitted preserves the
  existing value); `fields`/`reference`/version pin always overwritten.

## 15. Resolved during Phase 3 design (2026-07-07)

- **Embeddings deferred out of Phase 3 (DECIDED 2026-07-07).** Record-level embeddings
  are *not* built in Phase 3: the primary retrieval target is **PDF-extracted chunks**
  (a separate Lance table fed by the OCR/ingest pipeline), which needs its own design
  session. Mechanism pre-decisions recorded for that session:
  - **Compute = deferred server-side, RQ + litellm.** Embedding runs as an RQ job (never
    in the write request path) via a configurable `EXTRALIT_EMBEDDING_MODEL` (any litellm
    provider — the pattern `chat.py` already uses). Model unset → vector search cleanly
    disabled (422); FTS/scalar search unaffected, so keyless HF-Spaces deployments
    degrade gracefully.
  - **Vector column is lazy.** Tables are created without a vector column; the first
    embedding job learns the dimension from the litellm response and adds the column via
    Lance schema evolution. No dim setting; changing models requires a rebuild.
  - The compose `worker` service will need the `extralitdata` volume mount once workers
    write Lance files (not needed in Phase 3).
- **Lance storage = local URI with override (DECIDED 2026-07-07).** New setting
  `EXTRALIT_LANCEDB_URI`, defaulting to `${EXTRALIT_HOME_PATH}/lance`. Works out of the
  box on the compose named volume and HF-Spaces persistent `/data`; ops can point it at
  `s3://` later through the same `lancedb.connect` API (documented as
  unsupported-for-now — MinIO commit-concurrency and per-query latency unvalidated).
  Multi-process writes on the shared local volume rely on Lance's optimistic commit
  protocol.
- **ES coexistence: Phase 3 is additive only (DECIDED 2026-07-07).** v1 keeps running on
  `search_engine/` (ES/OpenSearch) untouched until Phase 6 retirement; v2 contexts never
  import it. This supersedes the Phase-2 plan's downstream note that put "delete
  `search_engine/`" in Phase 3.
- **Sync architecture mirrors v1; failure semantics per §6 (DECIDED 2026-07-07).** Keep
  v1's *shape* — create/evolve index on schema publish, `upsert_records` inline after
  record commit, delete on delete, engine injected as a FastAPI dependency, rebuild via
  a reindex CLI (`extralit_server index reindex`, v2 twin of
  `cli/search_engine/reindex.py`) — but as a new v2-shaped `LanceIndexEngine` taking
  `Schema`/`V2Record` (spec §4's "not behind the old ABC" stands). Failure semantics
  differ from v1 deliberately: a failed Lance sync **logs a warning (schema + record
  ids) and never fails the API request** (v1 propagates and 500s); no staleness
  bookkeeping, no per-failure retry — `rebuild` is the recovery path.
- **Search hydrates from Postgres.** `POST /schemas/{id}/records:search` consults Lance
  only for matching/ranking (`record_id`s + scores) and builds response payloads from
  Postgres rows — results always reflect the source of truth even when the index is
  stale, and `RecordRead` serialization is reused. Request shape (Phase 3):
  `{query: {text}, filters, offset, limit}`; the vector query variant lands with the
  chunk-retrieval design.
- **Lance row layout.** One table per schema (`schema_{id.hex}`): identity/system
  columns (`record_id`, `reference`, `schema_version_id`, `status`, `external_id`,
  timestamps) + one typed column per schema column (Arrow types derived from
  `columns_cache` dtypes; superset across versions via Lance `add_columns` evolution) +
  a derived `text` column (concatenated string-dtype cells) carrying the BM25 FTS index.
  `metadata` is stored as a JSON string column, not filterable in Phase 3.

### Future work ledger (after the extraction-records model stabilizes)

- **Documents import → `reference` mapping (needs its own spec + PRD).** How PDF(s) /
  imported documents map to the `reference` join key, beyond what the current documents
  import provides.
- **`reference` normalization.** A canonicalization rule for the join key (trim, DOI
  case-folding) applied on the write path — needed before the Queue (Phase 5) walks
  references, since `10.1000/ABC` vs `10.1000/abc` are currently distinct documents.
- **Question↔column binding validation.** Publish-time validation of `question.columns`
  against the new version's `columns_cache`; bindings dangle on column rename/drop.
- **Validation throughput.** Per-request S3 body fetch is fine for now; later options:
  Pandera lazy/batched validation or ibis + DuckDB backend with incremental loading
  (an immutable-version body cache is the cheap intermediate step).
- **`GET /schemas/{id}/versions/{version}`.** Specced, unimplemented; the Phase-4
  annotation UI will need it to render records pinned to old versions.
- **PDF-chunk retrieval (needs its own design session).** Embeddings + vector search
  over PDF-extracted chunks in a dedicated Lance table (feeds the RAG/chat rewrite,
  §9/§11). Mechanism pre-decisions already made in §15: RQ + litellm compute, lazy
  vector column via schema evolution, worker volume mount.
- **Record-level `similarity_search`.** Deferred with the above; the engine interface
  gains it when a use case (and an embedding target) exists.
- **`metadata` filtering in `:search`.** Stored as a JSON string column in Lance for
  now; promote to typed/filterable columns if a filtering use case appears.

## 16. Resolved during Phase 3 implementation (2026-07-07)

Phase 3 built the LanceDB index engine per §15 with no design reversals. As-built
outcomes and the deviations added during implementation/review (roborev jobs 80–98):

- **As-built package layout.** `index/` = `mapping.py` (pure Arrow/row helpers, no
  LanceDB/DB import), `base.py` (`IndexEngine` ABC + `IndexFilter`/`IndexSearchHit`/
  `IndexSearchResult`, deliberately *not* the v1 `SearchEngine` ABC), `lancedb_engine.py`
  (`LanceIndexEngine` on the async LanceDB API), `__init__.py` (`get_index_engine` DI
  provider mirroring `get_search_engine`). Sync glue lives in
  `contexts/v2/index_sync.py`; reindex CLI in `cli/index/`. v1 `search_engine/` untouched
  (verified: branch diff is empty over that path).
- **Best-effort semantics as-built.** `sync_schema_table` (publish), `sync_upserted_records`
  (bulk-upsert), `sync_deleted_records` (delete) each `try/except Exception` → log WARNING
  with schema + record ids → swallow; the API request still 200s/204s (tested by forcing
  the real engine to raise and asserting 200). Only `:rebuild-index`, `rebuild_schema_index`,
  and the reindex CLI surface errors.
- **Search hydration as-built.** `POST /schemas/{id}/records:search` takes
  `{text, filters, offset, limit}`, consults Lance for `record_id`s + scores, then fetches
  `V2Record` rows from Postgres by `id IN (...)` scoped to the schema and **re-orders to
  Lance's hit order**, skipping ids missing from PG (stale-index tolerance). `total` is the
  engine's match total (FTS totals materialize the match set, saturating at a 10k ceiling,
  since `count_rows` cannot evaluate an FTS predicate).
- **SQL-safety hardening (beyond the plan draft).** Filter column identifiers are validated
  against an allow-list built from the live Lance schema ∪ system fields (Datafusion has no
  parameterized identifiers); values go through a typed literal builder with `'`→`''`
  escaping. `eq` + `None` → `IS NULL`; `op="in"` with a scalar is rejected twice —
  a `RecordFilter` pydantic validator → **422** at the API boundary, and a `TypeError`
  guard in the engine for direct (CLI/SDK) callers.
- **Column-union determinism.** `table_columns` orders versions `version ASC` so
  `union_columns` first-wins keeps the earliest version's dtype; rebuild pagination adds a
  unique `id ASC` tiebreaker (equal `inserted_at` rows would otherwise skip/dup across
  OFFSET pages). `arrow_schema_for` raises `ValueError` if a user column name collides with
  a reserved system field.
- **Rebuild efficiency.** `LanceIndexEngine.upsert` gained a keyword-only `optimize=True`;
  the ABC adds a concrete no-op `optimize_table(schema_id)`. Write-time sync upserts
  eagerly optimize (search freshness); `rebuild_schema_index` upserts every batch with
  `optimize=False` and calls `optimize_table` once at the end — O(1) FTS rebuilds instead
  of O(batches). `_list_tables` paginates the LanceDB `list_tables()` response to
  exhaustion via `page_token`.
- **LanceDB API notes (installed `lancedb>=0.34.0`).** Async API throughout
  (`connect_async`, `merge_insert(...).when_matched_update_all().when_not_matched_insert_all()`,
  `create_index("text", config=FTS())`, `add_columns`, `optimize`, `count_rows`). The
  deprecated `Connection.table_names()` was replaced with `list_tables()`. FTS relevance is
  the `_score` column.
- **Review outcome.** Per-task spec+quality reviews and a whole-branch review passed;
  roborev branch review (job 98) returned **no issues**. Deferred as follow-ups (non-blocking):
  no test asserts the deferred-optimize call count; `ge`/`le` filters with a `None` value
  produce an always-false `>= NULL` (no 422 guard on ordered ops); `lancedb_uri: str | None`
  is always `str` at runtime and treats `""` as unset.

## 17. Resolved during Phase 4 design (2026-07-08) — annotation v2

Phase 4 builds the annotation layer: the human-in-the-loop review surface over LLM
extractions. This section **supersedes §5's annotation rows and §3's Question framing**
where they conflict; the decisions below are the authority for Phase 4.

### 17.0 Mental model: field ⊋ question ⊋ reviewable cell (DECIDED)

The v1 trinity (Question/Suggestion/Response) is kept, but its meaning is corrected for
the schema-centric model. The prior draft conflated *field*, *column*, and *question*;
they are nested, not equal:

- **`record.fields`** is the **superset** — context-relevant extractions the annotator
  needs to do their job. Most fields are read-only context.
- A **question** binds the **reviewable subset** of columns. A field may *reference* a
  question, in which case its authoritative value is **not stored** in `record.fields` —
  it lives in the suggestion→response for that question. So a stored field and a
  question are (mostly) mutually exclusive sources for a column's value.
- The **projection view** (§17.4) is over **questions** — the reviewable cells. Plain
  non-question fields ride along as read-only context.
- A field neither implies a question nor a response.

The **field↔question unification** (a field whose value is *defined by* a question, so a
schema becomes a chain of extraction/annotation steps whose later steps consume earlier
steps' annotated values) is a real generalization of this model but is **out of scope for
Phase 4** — it gets its own design session (§17.6). Phase 4's job is to not preclude it.

### 17.1 Three entities, reached leanly (DECIDED)

Keep `question` + `suggestion` + `response`, but implement them by **reusing v1's
validation logic** (§9's "fold v1 annotation into thin v2"), not by porting handlers
wholesale. The alternatives considered and rejected:

- **Collapse to responses-only** (questions→`columns_cache`/`review_widgets`,
  suggestions→`record.fields`). Rejected: (a) `v2_questions` is useful as the entity that
  **defines per-cell validators** (its settings drive response/suggestion validation, and
  it is the natural anchor for the future field↔question pydantic/Pandera binding); (b) a
  **suggestion is a distinct lifecycle layer**, not a synonym for the stored field — it is
  the LLM-**pre-populated** proposed value, and **submitting a response converts the
  suggestion into a response**. Folding it into `record.fields` loses that loop and its
  `score`/`agent` provenance.
- **Wholesale v1 port** (three tables + duplicated handlers/validators). Rejected to avoid
  maintaining two parallel annotation code stacks; the validators and settings pydantic
  are imported from v1, not re-authored.

### 17.2 Tables (additive Alembic; v2_-prefixed, same footnote as `V2Record`)

v1 owns `questions`/`suggestions`/`responses`, and a second declarative class of the same
name breaks v1's string-based `relationship()` registry lookups (§14). So the ORM classes
are `V2Question`/`V2Suggestion`/`V2Response` on `v2_questions`/`v2_suggestions`/
`v2_responses`; PG enums are `v2_*`-named. Canonical names return at Phase 6 retirement.

| Table / ORM | Key columns |
|---|---|
| `v2_questions` / `V2Question` | `id`, `schema_id`→schemas CASCADE, `name`, `title`, `description?`, `type` (PG enum `v2_question_type_enum`: `text`\|`label`\|`multi_label`\|`rating`\|`ranking`\|`span`\|`table`), `columns` JSONB (bound column names), `settings` JSONB (v1 `QuestionSettings` shape), `required` bool, timestamps; uniq(`schema_id`,`name`) |
| `v2_suggestions` / `V2Suggestion` | `id`, `record_id`→v2_records CASCADE, `question_id`→v2_questions CASCADE, `value` JSONB, `score` JSONB (float\|float[]\|null), `agent?`, `type?` (PG enum `v2_suggestion_type_enum`, v1 `SuggestionType` values), timestamps; uniq(`record_id`,`question_id`) |
| `v2_responses` / `V2Response` | `id`, `record_id`→v2_records CASCADE, `user_id`→users CASCADE, `values` JSONB (`{question_name: {value}}`, Decision §17.3), `status` (PG enum `v2_response_status_enum`: `draft`\|`submitted`\|`discarded`), timestamps; uniq(`record_id`,`user_id`) |

### 17.3 Decided items

- **`response.values` = keyed-by-question map, one row per `(record, user)` (DECIDED).**
  `values` is `{question_name: {value}}`; the question resolves to column(s). Rationale:
  Phase 5 queue-progress counts **responses per (reference→record, user)** — response-row
  granularity, unaffected by the values shape — and the `(record_id, user_id)` unique
  constraint is the overlap unit distribution needs. Per-question rows would only serve
  per-question analytics on *responses*, which in the schema-centric model is the record
  cells (Lance) + suggestions, not the review overlay. Submit is a single-row upsert,
  matching the UX (the annotator submits the whole form). A `table` question's
  multi-column answer stays one JSONB value under its key.

- **`span` question type deferred out of Phase 4 (DECIDED).** The enum value is reserved,
  but question-create **rejects `type=span` with a documented 422**. v2 cells are short
  structured values; the compelling span target is document/PDF text, which is the
  chunk-retrieval design's domain (§15 ledger). Defining a v1-style char-offset anchor
  into `str(record.fields[column])` now would likely be throwaway against the real
  document/chunk anchor. The other six types fully cover the cell-review layer.
  Migration of any v1 `span` questions is decided in the migrator phase (§8) — parked or
  skipped, not annotatable until the chunk-retrieval design lands.

- **No `record.status` transitions on response submit in Phase 4 (DECIDED).** Submitting a
  response writes only the `v2_responses` row. `v2_records.status` is set solely by record
  writes (bulk-upsert). The v1 flip (`responses_submitted >= min_submitted` →
  `completed`) *is* distribution logic (§9 folds `contexts/distribution.py` into the
  queue); **Phase 5 owns it** with the queue. Consequence: nothing moves a record to
  `completed` in Phase 4 — correct, completion is a distribution concept.

- **`question.columns` binding validated at create/update against the current
  `columns_cache` (DECIDED).** Every bound name must exist in
  `schema.current_version_id`'s `columns_cache`; **non-table binds exactly 1 column,
  `table` binds ≥1**. Questions can only be created against a **published** schema
  (`current_version_id` non-null) → 422 otherwise. **Publish-time revalidation** (a later
  version renaming/dropping a bound column dangles the binding) and **dtype-compatibility**
  checks stay in the §15 ledger. Old-version rendering tolerance: when a record pins an
  older version whose `columns_cache` lacks a bound column, the UI renders it as
  not-applicable — a display concern, not a validation error.

- **Value validation is settings-level only (DECIDED).** Reuse v1's per-type validators
  (`validators/response_values.py`): text is str, label/rating in options, ranking
  ranks/values valid+unique, multi_label unique+available; `table` value is a dict whose
  keys ⊆ `question.columns` (structure only — **no Pandera re-run** on the cells). This
  keeps annotation **Postgres-only**: responses/suggestions never fetch the S3 Pandera
  body. `SuggestionCreateValidator`'s score-cardinality checks (value/score length +
  list/scalar match) are ported as-is. Record-cell correctness remains the record-write
  path's responsibility.

### 17.4 The projection view (the "single view" — the product surface)

The first-class read surface. Not a stored table in Phase 4 — a **read-model** over the
three tables.

- **Grain:** record × question → one resolved cell, grouped by `reference` (composes with
  §6 reference grouping).
- **Resolution precedence:** submitted **response** (requesting user) → **suggestion**.
  (No `?? field` term: a reviewable column's value lives in the suggestion→response; plain
  non-question fields are separate context, not resolved cells.) The payload also returns
  the underlying suggestion + response so the UI shows provenance and lets the annotator
  override.
- **Suggestion→response conversion:** on submit, the annotator confirms or edits the
  suggestion value; the response stores the human value; the suggestion row remains
  (provenance) and is superseded by the response in the view.
- **Backing:** **query-time Postgres** for a single reference/record (a point query, not
  OLAP). The endpoint contract is **stable and shipped in Phase 4**; a **materialized OLAP
  method** (DuckDB/ibis/Lance across references) is a future iteration that swaps the
  backing without changing the contract. The **frontend consumes this endpoint in the
  later frontend phase** (§11) — Phase 4 delivers the server contract only.

### 17.5 API surface (`/api/v2`) and authorization

- **Questions:** `POST|GET|PUT|DELETE /schemas/{id}/questions`, `GET /questions/{id}`.
- **Suggestions:** `PUT /records/{id}/suggestions` (upsert on `(record, question)`),
  `GET /records/{id}/suggestions`.
- **Responses:** `PUT /records/{id}/responses` (upsert the **current user's own**
  response), `GET /records/{id}/responses`.
- **Projection view:** `GET /references/{reference:path}/view?workspace_id=` (or an
  extension of the existing `GET /references/{reference}`), returning per-record resolved
  cells + provenance grouped by reference.
- **Version read (pulled into Phase 4):** `GET /schemas/{id}/versions/{version}` — the
  §15 ledger item, needed so the annotation UI can render records pinned to old versions.
- **No Lance sync for annotation.** Questions/suggestions/responses live **only in
  Postgres**; annotation contexts never import the index engine. Lance indexes record
  cells for search; the review overlay is queried from Postgres.
- **Policies** (alongside `SchemaPolicy` in `api/policies/v1/`, which already targets
  `models.v2`): `QuestionPolicy` and `SuggestionPolicy` mirror `SchemaPolicy`
  (list/get: workspace member; create/update/delete: owner or admin+member), scoped via
  the question's / record's `schema.workspace_id`. **`V2ResponsePolicy` ports v1's
  own-response authz**: `owner OR actor.id == response.user_id OR (admin AND
  member(workspace))`, workspace resolved via `record.schema.workspace_id` — annotators
  write and read their own response, not others'.

### 17.6 Out of scope (each with a pointer)

- **Field↔question unification / schema-as-chain-of-steps** — a field whose authoritative
  value is *defined by* a question (value not stored), enabling multi-step schemas whose
  later steps consume earlier annotated values across `reference`. Phase 4 is compatible
  (a question binds a column without requiring a stored field) but does not implement the
  cross-schema resolution. **Its own design session.**
- **Chain-of-steps resolution in the view** — following a field's question reference
  through suggestion→response across schemas needs the OLAP join above; deferred with the
  field↔question spec.
- **Consensus / multi-annotator reconciliation** — the view resolves to the requesting
  user's response; cross-annotator agreement (overlap → reconciled cell) is a later spec.
  Phase 5 distribution produces the overlap; reconciliation consumes it.
- **OLAP materialization method** for the projection view — query-time per-reference for
  now (§17.4).
- **Per-cell suggestion `score`/`agent` surfaced beyond the suggestion row** — if a
  review-UI need appears, a `{column: {score, agent}}` map in `record.metadata` is the
  cheap step.

### 17.7 Testing strategy (Phase 4 additions to §10)

- **Unit:** binding validation (existence + arity, published-schema requirement, span
  422); ported per-type value validators + score cardinality; own-response authz;
  projection resolution precedence (response→suggestion, conversion on submit).
- **Contexts (async pytest):** question CRUD; suggestion upsert on `(record, question)`;
  response upsert on `(record, user)` with **no `record.status` side-effect** and **no
  index-engine call** (assert the engine is untouched); projection assembly for a
  reference.
- **API:** `/api/v2` annotation routers happy-path + 422 (span, unbound column, unpublished
  schema, bad value shape) + authz (own-response, cross-user 403); single-version read;
  projection-view endpoint.
- **Migration (§8):** v1 questions→`v2_questions` column bindings, suggestions, responses
  parity; v1 span questions handled per the migrator decision.
