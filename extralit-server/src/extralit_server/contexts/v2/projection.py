"""Projection views (spec §17.4): resolve each reviewable cell as
submitted-response -> suggestion. `build_reference_view` is the per-reference review form
(Postgres-only, requesting user's responses). `build_workspace_view` is the workspace-wide
denormalized grid: Postgres serves batched raw slices, an in-memory DuckDB does the
denormalization. Both are query-time; a future OLAP materialization can replace them
without changing the API."""

import json
from uuid import UUID

import duckdb
from anyio import to_thread
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v2.projection import (
    ProjectionCell,
    ProjectionRecord,
    ProjectionView,
    WorkspaceProjection,
    WorkspaceProjectionCell,
    WorkspaceProjectionColumn,
    WorkspaceProjectionRow,
)
from extralit_server.contexts.v2 import records as records_ctx
from extralit_server.enums import QuestionType, ResponseStatus
from extralit_server.models.v2 import Schema, V2Question, V2Record, V2Response, V2Suggestion


async def build_reference_view(db: AsyncSession, *, workspace_id: UUID, reference: str, user) -> ProjectionView:
    records = await records_ctx.list_records_by_reference(db, workspace_id=workspace_id, reference=reference)
    if not records:
        return ProjectionView(reference=reference, records=[], total_records=0)

    schema_ids = {r.schema_id for r in records}
    record_ids = [r.id for r in records]

    questions_by_schema: dict[UUID, list[V2Question]] = {}
    q_rows = (await db.execute(select(V2Question).where(V2Question.schema_id.in_(schema_ids)))).scalars().all()
    for q in q_rows:
        questions_by_schema.setdefault(q.schema_id, []).append(q)

    # (record_id, question_id) -> suggestion row
    sugg_rows = (await db.execute(select(V2Suggestion).where(V2Suggestion.record_id.in_(record_ids)))).scalars().all()
    suggestions = {(s.record_id, s.question_id): s for s in sugg_rows}

    # requesting user's submitted responses only: record_id -> {question_name: value}
    resp_rows = (
        (
            await db.execute(
                select(V2Response).where(
                    V2Response.record_id.in_(record_ids),
                    V2Response.user_id == user.id,
                    V2Response.status == ResponseStatus.submitted,
                )
            )
        )
        .scalars()
        .all()
    )
    responses = {r.record_id: (r.values or {}) for r in resp_rows}

    projection_records: list[ProjectionRecord] = []
    for record in records:
        cells: list[ProjectionCell] = []
        for question in questions_by_schema.get(record.schema_id, []):
            wrapped = responses.get(record.id, {}).get(question.name)
            if wrapped is not None:
                cells.append(
                    ProjectionCell(
                        question_name=question.name,
                        value=wrapped.get("value"),
                        source="response",
                        record_id=record.id,
                    )
                )
            elif (record.id, question.id) in suggestions:
                suggestion = suggestions[(record.id, question.id)]
                cells.append(
                    ProjectionCell(
                        question_name=question.name,
                        value=suggestion.value,
                        source="suggestion",
                        record_id=record.id,
                        agent=suggestion.agent,
                        score=suggestion.score,
                    )
                )
            else:
                cells.append(ProjectionCell(question_name=question.name, value=None, source=None))
        projection_records.append(
            ProjectionRecord(record_id=record.id, schema_id=record.schema_id, reference=record.reference, cells=cells)
        )

    return ProjectionView(reference=reference, records=projection_records, total_records=len(records))


def _build_columns(
    schemas: list[Schema],
    questions_by_schema: dict[UUID, list[V2Question]],
) -> list[WorkspaceProjectionColumn]:
    """Flat grid column manifest (spec §3.1): one column per scalar question, one per
    table-question sub-column binding, in schema-name then question-definition order."""
    columns: list[WorkspaceProjectionColumn] = []
    for schema in schemas:
        for question in questions_by_schema.get(schema.id, []):
            if question.type == QuestionType.table:
                # sub-columns are the question's `columns` binding (spec §3.4)
                for sub in question.columns or []:
                    columns.append(
                        WorkspaceProjectionColumn(
                            name=f"{schema.name}.{question.name}.{sub}",
                            schema_id=schema.id,
                            schema_name=schema.name,
                            question_name=question.name,
                            sub_column=sub,
                            dtype=question.type.value,
                        )
                    )
            else:
                columns.append(
                    WorkspaceProjectionColumn(
                        name=f"{schema.name}.{question.name}",
                        schema_id=schema.id,
                        schema_name=schema.name,
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
CREATE TABLE question_columns (question_id VARCHAR, sub_column VARCHAR);
CREATE TABLE records (record_id VARCHAR, schema_id VARCHAR, reference VARCHAR, inserted_at TIMESTAMP);
CREATE TABLE suggestions (record_id VARCHAR, question_id VARCHAR, value_json JSON, agent VARCHAR, score_json JSON);
CREATE TABLE responses (record_id VARCHAR, values_json JSON, updated_at TIMESTAMP);
"""

_INSERTS = {
    "questions": "INSERT INTO questions VALUES (?, ?, ?, ?, ?)",
    "question_columns": "INSERT INTO question_columns VALUES (?, ?)",
    "records": "INSERT INTO records VALUES (?, ?, ?, ?)",
    "suggestions": "INSERT INTO suggestions VALUES (?, ?, ?, ?, ?)",
    "responses": "INSERT INTO responses VALUES (?, ?, ?)",
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
    -- latest submitted response per record, by ANY user (submitted-only filtering happens in Postgres)
    SELECT record_id, values_json
    FROM responses
    WHERE values_json IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY record_id ORDER BY updated_at DESC) = 1
),
response_keys AS (
    SELECT record_id, values_json, unnest(json_keys(values_json)) AS question_name
    FROM latest_responses
),
response_cells AS (
    -- unwrap the {question_name: {"value": ...}} envelope
    SELECT record_id, question_name,
           json_extract(values_json, '$."' || question_name || '".value') AS value
    FROM response_keys
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
table_cells AS (
    -- quoting the sub-column into the JSON path handles arbitrary key names
    SELECT tr.reference, tr.record_id, tr.row_idx,
           tr.schema_name || '.' || tr.question_name || '.' || qc.sub_column AS column_name,
           json_extract(tr.row_json, '$."' || qc.sub_column || '"') AS value,
           tr.source, tr.agent, tr.score
    FROM table_object_rows tr
    JOIN question_columns qc ON qc.question_id = tr.question_id
    WHERE json_type(json_extract(tr.row_json, '$."' || qc.sub_column || '"')) <> 'NULL'
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
    """
    schemas = (
        (await db.execute(select(Schema).where(Schema.workspace_id == workspace_id).order_by(Schema.name)))
        .scalars()
        .all()
    )
    if not schemas:
        return WorkspaceProjection(columns=[], rows=[], total_references=0)

    schema_ids = [s.id for s in schemas]
    schema_names = {s.id: s.name for s in schemas}
    questions = (
        (
            await db.execute(
                select(V2Question)
                .where(V2Question.schema_id.in_(schema_ids))
                .order_by(V2Question.inserted_at, V2Question.name)
            )
        )
        .scalars()
        .all()
    )
    questions_by_schema: dict[UUID, list[V2Question]] = {}
    for question in questions:
        questions_by_schema.setdefault(question.schema_id, []).append(question)
    columns = _build_columns(list(schemas), questions_by_schema)

    total_references = (
        await db.execute(select(func.count(distinct(V2Record.reference))).where(V2Record.schema_id.in_(schema_ids)))
    ).scalar_one()
    references = (
        (
            await db.execute(
                select(V2Record.reference)
                .where(V2Record.schema_id.in_(schema_ids))
                .group_by(V2Record.reference)
                .order_by(V2Record.reference)
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
                select(V2Record).where(V2Record.schema_id.in_(schema_ids), V2Record.reference.in_(list(references)))
            )
        )
        .scalars()
        .all()
    )
    record_ids = [r.id for r in records]
    suggestions = (await db.execute(select(V2Suggestion).where(V2Suggestion.record_id.in_(record_ids)))).scalars().all()
    responses = (
        (
            await db.execute(
                select(V2Response).where(
                    V2Response.record_id.in_(record_ids), V2Response.status == ResponseStatus.submitted
                )
            )
        )
        .scalars()
        .all()
    )

    inputs: dict[str, list[tuple]] = {
        "questions": [
            (str(q.id), str(q.schema_id), schema_names[q.schema_id], q.name, q.type.value) for q in questions
        ],
        "question_columns": [
            (str(q.id), sub) for q in questions if q.type == QuestionType.table for sub in (q.columns or [])
        ],
        "records": [(str(r.id), str(r.schema_id), r.reference, r.inserted_at) for r in records],
        "suggestions": [
            (str(s.record_id), str(s.question_id), json.dumps(s.value), s.agent, json.dumps(s.score))
            for s in suggestions
        ],
        "responses": [(str(r.record_id), json.dumps(r.values or {}), r.updated_at) for r in responses],
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
