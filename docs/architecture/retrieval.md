# Retrieval Architecture

How an uploaded PDF becomes searchable chunks: analysis → layout → chunk → embed → hybrid search.
Code lives in `extralit-server/src/extralit_server/contexts/retrieval/` and
`jobs/retrieval_jobs.py`.

## Storage layout

```
documents/{id}/source.pdf      upload
documents/{id}/ocr.pdf         analysis job; every parser reads this
documents/{id}/docling.json    layout job; the source of truth
documents/{id}/thumbnail.png
layout/items.lance             one row per (item, provenance), workspace-wide
layout/chunks.lance            one row per chunk, one nullable vector__{slug} column per model
```

Only `docling.json` is authoritative: `items` and `chunks` are derived from it and rebuilt from it.

## Sync chain

`create_document_workflow` (upload, import and workflow start all call it) enqueues the whole chain
in one go, linked by RQ job dependencies in one RQ `Group`:

```
analysis_and_preprocess_job (default)         writes ocr.pdf
        │ depends_on, allow_failure
        ▼
async_document_layout_job (ocr)               writes docling.json, then items
        │ depends_on, allow_failure
        ▼
async_document_chunk_job (ocr)                writes chunks
        │ .delay() from inside the job, only if EXTRALIT_RETRIEVAL_EMBEDDING_MODEL is set
        ▼
async_embed_chunks_job (embed)                fills NULL vector__{slug} rows

POST /api/v1/workspaces/{name}/search
  query ─▶ DuckDB `lance`: lance_fts leg + lance_vector_search leg ─▶ SQL RRF ─▶ hits
```

| Failure | Result |
|---|---|
| Analysis fails | RQ retries it (3 times). Layout still runs and fails on the missing `ocr.pdf` with a message naming the analysis job |
| Layout fails | RQ retries it (2 times). The chunk job then runs anyway: it fails on a missing `docling.json`, or re-chunks the unchanged old one. Items and chunks never end up half-new |
| Layout succeeds but its worker dies between the `docling.json` and `items` writes | The chunk job sees items whose hash differs from `docling.json` and rewrites items and chunks together |
| Chunk job fails, or its embed enqueue raises | The job fails and RQ retries it (2 times); replacing chunks is idempotent. `retrieval backfill` finds what is still stale afterwards |
| Embed job fails | RQ retries it; rows stay `NULL` and search skips them. `retrieval backfill` re-enqueues |

The `pymupdf_to_markdown_job` text-extraction job is in the same workflow but nothing in the chain
depends on it.

## Drift detection

`source_hash` is the sha256 of the exact `docling.json` bytes. The layout job stamps it on every
`items` row; the chunk job stamps the same value on every `chunks` row, from the file it just read.
The layout API and search never check it. `python -m extralit_server retrieval backfill` reads each
document's `docling.json`, compares its hash and `chunker_fingerprint` with the chunks, and
enqueues a chunk job for each mismatch. A second run enqueues nothing. Datasets written before the
column existed read as all-stale; there is no deployment to migrate.

- One chunk per body `DocItem`. A caption linked through `FloatingItem.captions` joins its owner. No
  chunk is split; the embedder truncates (`EmbeddingSettings(truncate=True)`).
- `chunk_id = xxh64(document_id, text, n)`, so re-chunking keeps the ids, and the vectors, of
  unchanged chunks. `item_refs` are positional (`#/texts/41`); a re-parse updates them in place
  through `merge_insert`, so they always resolve against the current `docling.json`.
- Chunks live in the workspace layout root next to `items`, under the same Redis lock.
- Deleting a document removes `documents/{id}/`, its items and its chunks (and their vectors).
- `chunks.type` is `text`, `table` or `figure`. It is a plain string; search filters and the API use
  `type`/`types`. Unquoted `type` works in Lance filters and in the DuckDB `filter :=` strings.

## Settings

Read from `EXTRALIT_RETRIEVAL_*` (`RetrievalSettings`).

| Variable | Default | Meaning |
|---|---|---|
| `EMBEDDING_MODEL` | `""` | pydantic-ai model string, e.g. `openai:text-embedding-3-small`. Empty: full-text search only, no embed job, no vector leg |
| `EMBEDDING_DIMENSIONS` | unset | Passed as `EmbeddingSettings(dimensions=…)` |
| `EMBEDDING_SETTINGS` | `{}` | JSON, merged into the provider's `EmbeddingSettings`, e.g. `{"bedrock_max_concurrency": 2}` |
| `EMBEDDING_BATCH_SIZE` | `64` | Texts per provider call; also the unit of one index commit |
| `RRF_K` | `60` | Reciprocal rank fusion constant |
| `CANDIDATE_K` | `50` | `k` of each leg before fusion |

Worker count: `EXTRALIT_EMBED_WORKERS` (default 1) in the compose files.

## Index policy

- `chunks.text`: `INVERTED` index, created on the first write.
- `vector__{slug}`: one nullable `fixed_size_list<f32, D>` column per embedding model, tagged with
  `{embedding_model, dimensions}` in field metadata. Added without rewriting data the first time a
  model embeds. Each gets its own `IVF_HNSW_FLAT` index (`num_partitions=1`).
  `optimize_indices()` runs after every write.
- Not `IVF_RQ` yet: extension 1.5.5 read pylance RQ indexes wrongly. Extension 2.0.0 returns the same
  neighbours as pylance (see `scripts/probe_lance_types.py`), so switching is now an option.
- Switching models adds a new column. Existing chunks are embedded for it only when an operator runs
  `python -m extralit_server retrieval backfill`. Search reads only the configured model's column;
  rows still `NULL` are skipped. Drop a retired column with `ChunkStore.drop_vector_column`.
- A model whose dimensions differ from its existing column is rejected.

## Search

`hybrid_search` runs in DuckDB with the `lance` extension. Each store root is attached as a Lance
namespace (`ATTACH root AS ns (TYPE LANCE, READ_ONLY false)`; `s3://` roots first get a scoped
`CREATE SECRET (TYPE LANCE, …)` from `lance_storage_options()`).

- Both legs take `filter := '…', prefilter := true`, so document, reference, page and type filters
  apply before top-k. A `WHERE` on the table function output would run after top-k and can return
  nothing. The filter string is built from allow-listed columns and quoted literals.
- RRF is plain SQL over the two legs: `1/(rrf_k + rank)` summed per chunk. `lance_hybrid_search` is
  not used: it takes one dataset, fuses by `alpha` and has no filter.
- The vector leg is skipped without an embedder or when no store has a column for the model. The
  response then carries `scores.vector = null` on every hit.
- Scores: `bm25` (higher is better), `vector` (distance, lower is closer), `rrf` (fused).
- The `type` column is a plain string. With a dictionary-encoded column, extension 2.0.0 still
  segfaults in `lance_fts`/`lance_vector_search` and returns `''` under a filter.
- JSON and VARIANT columns are not used for filter fields. Lance stores `arrow.json` as JSONB,
  which DuckDB reads as BLOB. DuckDB reads VARIANT, but Lance filters have no `variant_get`.

## Queues and workers

| Queue | Jobs | Served by |
|---|---|---|
| `high`, `default`, `ocr` | layout, chunk and the rest | `worker` (default `--queues`) |
| `embed` | `async_embed_chunks_job` | `embed-worker`: `--queues embed --num-workers ${EXTRALIT_EMBED_WORKERS:-1}` |

`embed` is deliberately not in the default `--queues`. Provider caps such as
`bedrock_max_concurrency` are in-process, so the cross-job limit is
embed workers × that cap. The embed job calls the provider outside the layout lock and takes the lock
only for each batch's `merge_insert`; the lock waits at most 300 s.

## DuckDB extension and pylance versions

The `lance` extension comes from the `duckdb-extension-lance` wheel, which pins an exact `duckdb`.
It is loaded from the wheel's own path, because `LOAD lance` only searches `~/.duckdb/extensions`.
The extension reads files written by pylance. The current lock has duckdb 2.0.0, extension 2.0.0
(build `86118537da`) and pylance 14.0.3; duckdb 2.0 needs Python 3.11 or newer.
Compared with 1.5.5 on 100k chunks, vector and hybrid queries are about 4x faster and full-text
queries about 2.5x slower.

A pylance or extension bump can break how the extension reads an index type, as it once did for
`IVF_RQ`. The integration test that queries a stored chunk's own vector and expects that chunk
first is the guard. Run it, and `scripts/probe_lance_types.py`, on every pylance or
`duckdb-extension-lance` bump.

HNSW is approximate: at `k=1` the self-match is not always found, so the vector leg asks for
`candidate_k` neighbours.
