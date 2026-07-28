"""Projection views (spec §17.4): resolve each reviewable cell as
submitted-response -> suggestion. `build_workspace_view` is the workspace-wide
denormalized grid: Postgres serves batched raw slices, an in-memory DuckDB does the
denormalization. It is query-time; a future OLAP materialization can replace it
without changing the API."""

import json
from uuid import UUID

import duckdb
from anyio import to_thread
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.projection import (
    WorkspaceProjection,
    WorkspaceProjectionCell,
    WorkspaceProjectionColumn,
    WorkspaceProjectionRow,
)
from extralit_server.enums import QuestionType, ResponseStatus
from extralit_server.models.database import Dataset, Question, Record, Response, Suggestion


def _build_columns(
    datasets: list[Dataset],
    questions_by_dataset: dict[UUID, list[Question]],
) -> list[WorkspaceProjectionColumn]:
    """Flat grid column manifest (spec §3.1): one column per scalar question, one per
    table-question sub-column binding, in dataset-name then question-definition order."""
    columns: list[WorkspaceProjectionColumn] = []
    for dataset in datasets:
        for question in questions_by_dataset.get(dataset.id, []):
            if question.type == QuestionType.table:
                # sub-columns are the question's `columns` binding (spec §3.4)
                for sub in question.settings.get("columns") or []:
                    columns.append(
                        WorkspaceProjectionColumn(
                            name=f"{dataset.name}.{question.name}.{sub}",
                            dataset_id=dataset.id,
                            dataset_name=dataset.name,
                            question_name=question.name,
                            sub_column=sub,
                            dtype=question.type.value,
                        )
                    )
            else:
                columns.append(
                    WorkspaceProjectionColumn(
                        name=f"{dataset.name}.{question.name}",
                        dataset_id=dataset.id,
                        dataset_name=dataset.name,
                        question_name=question.name,
                        sub_column=None,
                        dtype=question.type.value,
                    )
                )
    return columns


_INPUT_TABLES_DDL = """
CREATE TABLE questions (
    question_id VARCHAR, schema_id VARCHAR, schema_name VARCHAR, question_name VARCHAR, qtype VARCHAR
);
-- Sub-column bindings are unconstrained user input and are never interpolated into a JSON path:
-- the statement joins them against unnested object keys instead. A quote, a backslash or an
-- empty name in a path aborts the whole statement at execution time (not just that cell), and a
-- name of '*' would silently match every key.
CREATE TABLE question_columns (question_id VARCHAR, sub_column VARCHAR);
CREATE TABLE records (record_id VARCHAR, schema_id VARCHAR, reference VARCHAR, inserted_at TIMESTAMP);
CREATE TABLE suggestions (record_id VARCHAR, question_id VARCHAR, value_json JSON, agent VARCHAR, score_json JSON);
CREATE TABLE responses (response_id VARCHAR, record_id VARCHAR, values_json JSON, updated_at TIMESTAMP);
"""

_INSERTS = {
    "questions": "INSERT INTO questions VALUES (?, ?, ?, ?, ?)",
    "question_columns": "INSERT INTO question_columns VALUES (?, ?)",
    "records": "INSERT INTO records VALUES (?, ?, ?, ?)",
    "suggestions": "INSERT INTO suggestions VALUES (?, ?, ?, ?, ?)",
    "responses": "INSERT INTO responses VALUES (?, ?, ?, ?)",
}

# One statement, one CTE per concern. Emits long-format
# (reference, row_idx, column_name, value_json, source, record_id, agent, score_json)
# ordered so a single linear pass in Python regroups it into rows.
_DENORMALIZE_SQL = """
WITH effective_records AS (
    -- one effective record per (reference, schema): the latest inserted one
    SELECT record_id, schema_id, reference
    FROM records
    QUALIFY row_number() OVER (PARTITION BY reference, schema_id ORDER BY inserted_at DESC, record_id DESC) = 1
),
latest_responses AS (
    -- Record-level selection, intentional per spec §3.2: exactly ONE response *envelope* wins
    -- per record -- the latest submitted one by ANY user (submitted-only filtering happens in
    -- Postgres). A question absent from that envelope therefore falls back to its suggestion
    -- even when an earlier submitted response answered it; envelopes are not merged per cell.
    -- `response_id` is a tiebreaker, not decoration: TimestampMixin defaults `updated_at` to
    -- `datetime.utcnow`, so two users submitting back-to-back can land on the identical
    -- timestamp and the winner would otherwise be whatever order Postgres happened to return.
    -- It buys stability, not latest-ness: a UUID carries no recency, so on a tie the winner is
    -- the greatest `response_id` -- an arbitrary user, picked the same way every run.
    SELECT record_id, values_json
    FROM responses
    WHERE values_json IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY record_id ORDER BY updated_at DESC, response_id DESC) = 1
),
response_entries AS (
    -- zip-unnest the envelope: `json_keys` and the `'$.*'` wildcard walk the object in the same
    -- order, which avoids interpolating a data-derived key into a JSON path (unescapable here).
    SELECT record_id,
           unnest(json_keys(values_json)) AS question_name,
           unnest(json_extract(values_json, '$.*')) AS entry
    FROM latest_responses
),
response_cells AS (
    -- unwrap the {question_name: {"value": ...}} envelope
    SELECT record_id, question_name, json_extract(entry, '$.value') AS value
    FROM response_entries
),
resolved AS (
    -- coalesce = response ?? suggestion; (record, question) pairs with neither drop out
    SELECT er.reference,
           er.record_id,
           q.question_id,
           q.qtype,
           q.schema_name,
           q.question_name,
           COALESCE(rc.value, s.value_json) AS value,
           CASE WHEN rc.value IS NOT NULL THEN 'response' ELSE 'suggestion' END AS source,
           CASE WHEN rc.value IS NOT NULL THEN NULL ELSE s.agent END AS agent,
           CASE WHEN rc.value IS NOT NULL THEN NULL ELSE s.score_json END AS score
    FROM effective_records er
    JOIN questions q ON q.schema_id = er.schema_id
    LEFT JOIN response_cells rc ON rc.record_id = er.record_id AND rc.question_name = q.question_name
    LEFT JOIN suggestions s ON s.record_id = er.record_id AND s.question_id = q.question_id
    WHERE COALESCE(rc.value, s.value_json) IS NOT NULL
),
scalar_cells AS (
    SELECT reference, record_id,
           schema_name || '.' || question_name AS column_name,
           value, source, agent, score
    FROM resolved
    WHERE qtype <> 'table' AND json_type(value) <> 'NULL'
),
table_arrays AS (
    -- §3.4 normalization: a bare dict is a one-row table
    SELECT reference, record_id, question_id, schema_name, question_name, source, agent, score,
           CASE WHEN json_type(value) = 'ARRAY'
                THEN value
                ELSE CAST('[' || CAST(value AS VARCHAR) || ']' AS JSON)
           END AS arr
    FROM resolved
    WHERE qtype = 'table'
),
table_rows AS (
    -- zip-unnest: the index list and the element list are unnested in lockstep
    SELECT reference, record_id, question_id, schema_name, question_name, source, agent, score,
           unnest(range(CAST(json_array_length(arr) AS BIGINT))) AS row_idx,
           unnest(json_extract(arr, '$[*]')) AS row_json
    FROM table_arrays
),
table_object_rows AS (
    SELECT * FROM table_rows WHERE json_type(row_json) = 'OBJECT'
),
table_row_entries AS (
    -- same zip-unnest as the response envelope: no data-derived text ever reaches a JSON path,
    -- so quotes, backslashes, empty names and '*' in a binding are all just ordinary keys
    SELECT reference, record_id, question_id, schema_name, question_name, source, agent, score, row_idx,
           unnest(json_keys(row_json)) AS entry_key,
           unnest(json_extract(row_json, '$.*')) AS entry_value
    FROM table_object_rows
),
table_cells AS (
    -- an unmatched binding is an absent sub-key: no join row, hence no cell. JSON-null omitted too.
    SELECT e.reference, e.record_id, e.row_idx,
           e.schema_name || '.' || e.question_name || '.' || qc.sub_column AS column_name,
           e.entry_value AS value,
           e.source, e.agent, e.score
    FROM table_row_entries e
    JOIN question_columns qc ON qc.question_id = e.question_id AND qc.sub_column = e.entry_key
    WHERE json_type(e.entry_value) <> 'NULL'
),
fanout AS (
    SELECT reference, max(row_idx) AS max_idx FROM table_object_rows GROUP BY reference
),
spine AS (
    -- independent stacking: row count = max fan-out across every table on the reference, min 1
    SELECT r.reference, unnest(range(CAST(COALESCE(f.max_idx, 0) + 1 AS BIGINT))) AS row_idx
    FROM (SELECT DISTINCT reference FROM records) r
    LEFT JOIN fanout f ON f.reference = r.reference
),
all_cells AS (
    -- NULL row_idx = "repeat me onto every spine row"
    SELECT reference, CAST(NULL AS BIGINT) AS row_idx, column_name, value, source, record_id, agent, score
    FROM scalar_cells
    UNION ALL
    SELECT reference, row_idx, column_name, value, source, record_id, agent, score
    FROM table_cells
)
SELECT s.reference,
       s.row_idx,
       c.column_name,
       CAST(c.value AS VARCHAR) AS value_json,
       c.source,
       c.record_id,
       c.agent,
       CAST(c.score AS VARCHAR) AS score_json
FROM spine s
LEFT JOIN all_cells c
  ON c.reference = s.reference AND (c.row_idx IS NULL OR c.row_idx = s.row_idx)
ORDER BY s.reference, s.row_idx, c.column_name NULLS LAST
"""


def _run_denormalization(inputs: dict[str, list[tuple]]) -> list[tuple]:
    """Load the raw Postgres slices into an in-memory DuckDB and run the denormalization.

    Sync and CPU-bound on purpose: callers offload it with `anyio.to_thread.run_sync`.
    """
    con = duckdb.connect()
    try:
        con.execute(_INPUT_TABLES_DDL)
        for table, statement in _INSERTS.items():
            rows = inputs.get(table) or []
            if rows:  # DuckDB's executemany rejects an empty parameter list
                con.executemany(statement, rows)
        return con.execute(_DENORMALIZE_SQL).fetchall()
    finally:
        con.close()


async def build_workspace_view(db: AsyncSession, *, workspace_id: UUID, offset: int, limit: int) -> WorkspaceProjection:
    """Denormalize a whole workspace into flat grid rows (spec §3).

    Postgres serves batched raw slices only (<=7 statements, independent of the page size);
    the in-memory DuckDB statement implements every semantic: effective-record dedup,
    response-over-suggestion coalescing, table fan-out with independent stacking and scalar
    repetition. `offset`/`limit` count references, not fan-out rows.

    Coalescing is record-level, intentionally (spec §3.2): the latest submitted response
    *envelope* per record wins outright, across all users. A question the winning envelope does
    not contain falls back to its suggestion even if an earlier submitted response answered it
    — envelopes are never merged cell-by-cell. "Latest" is by `updated_at`; ties resolve to the
    greatest `response_id`, which is deterministic but arbitrary with respect to authorship.
    """
    datasets = (
        (
            await db.execute(
                select(Dataset)
                .where(
                    Dataset.workspace_id == workspace_id,
                    # Only schema-backed datasets are extraction projects; a plain
                    # annotation dataset in the same workspace has no column manifest
                    # and must not contribute columns or rows to the grid.
                    Dataset.current_schema_version_id.is_not(None),
                )
                .order_by(Dataset.name)
            )
        )
        .scalars()
        .all()
    )
    if not datasets:
        return WorkspaceProjection(columns=[], rows=[], total_references=0)

    dataset_ids = [d.id for d in datasets]
    dataset_names = {d.id: d.name for d in datasets}
    questions = (
        (
            await db.execute(
                select(Question)
                .where(Question.dataset_id.in_(dataset_ids))
                .order_by(Question.inserted_at, Question.name)
            )
        )
        .scalars()
        .all()
    )
    questions_by_dataset: dict[UUID, list[Question]] = {}
    for question in questions:
        questions_by_dataset.setdefault(question.dataset_id, []).append(question)
    columns = _build_columns(list(datasets), questions_by_dataset)

    total_references = (
        await db.execute(select(func.count(distinct(Record.reference))).where(Record.dataset_id.in_(dataset_ids)))
    ).scalar_one()
    references = (
        (
            await db.execute(
                select(Record.reference)
                .where(Record.dataset_id.in_(dataset_ids))
                .group_by(Record.reference)
                .order_by(Record.reference)
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    if not references:
        return WorkspaceProjection(columns=columns, rows=[], total_references=total_references)

    records = (
        (
            await db.execute(
                select(Record).where(Record.dataset_id.in_(dataset_ids), Record.reference.in_(list(references)))
            )
        )
        .scalars()
        .all()
    )
    record_ids = [r.id for r in records]
    suggestions = (await db.execute(select(Suggestion).where(Suggestion.record_id.in_(record_ids)))).scalars().all()
    responses = (
        (
            await db.execute(
                select(Response).where(Response.record_id.in_(record_ids), Response.status == ResponseStatus.submitted)
            )
        )
        .scalars()
        .all()
    )

    inputs: dict[str, list[tuple]] = {
        "questions": [
            (str(q.id), str(q.dataset_id), dataset_names[q.dataset_id], q.name, q.type.value) for q in questions
        ],
        "question_columns": [
            (str(q.id), sub)
            for q in questions
            if q.type == QuestionType.table
            for sub in (q.settings.get("columns") or [])
        ],
        "records": [(str(r.id), str(r.dataset_id), r.reference, r.inserted_at) for r in records],
        # ensure_ascii=False: question names and sub-column bindings are matched by string
        # equality against keys DuckDB parses out of this JSON text (`rc.question_name =
        # q.question_name`, `qc.sub_column = e.entry_key`). Emitting non-ASCII keys as
        # \uXXXX escapes would make that join depend on DuckDB decoding them back; writing
        # the codepoints directly removes the dependency instead of relying on it.
        "suggestions": [
            (
                str(s.record_id),
                str(s.question_id),
                json.dumps(s.value, ensure_ascii=False),
                s.agent,
                json.dumps(s.score, ensure_ascii=False),
            )
            for s in suggestions
        ],
        "responses": [
            (str(r.id), str(r.record_id), json.dumps(r.values or {}, ensure_ascii=False), r.updated_at)
            for r in responses
        ],
    }
    output = await to_thread.run_sync(_run_denormalization, inputs)

    rows: list[WorkspaceProjectionRow] = []
    current: WorkspaceProjectionRow | None = None
    for reference, row_idx, column_name, value_json, source, record_id, agent, score_json in output:
        if current is None or current.reference != reference or current.row_index != row_idx:
            current = WorkspaceProjectionRow(reference=reference, row_index=row_idx, cells={})
            rows.append(current)
        if column_name is None:  # spine-only row: the reference has records but no resolvable cells
            continue
        current.cells[column_name] = WorkspaceProjectionCell(
            value=json.loads(value_json),
            source=source,
            record_id=UUID(record_id),
            agent=agent,
            score=json.loads(score_json) if score_json is not None else None,
        )

    return WorkspaceProjection(columns=columns, rows=rows, total_references=total_references)
