"""Projection view (spec §17.4): resolve each reviewable cell as
submitted-response(requesting user) -> suggestion, grouped by reference. Query-time,
Postgres-only. A future OLAP materialization can replace this without changing the API."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v2.projection import ProjectionCell, ProjectionRecord, ProjectionView
from extralit_server.contexts.v2 import records as records_ctx
from extralit_server.enums import ResponseStatus
from extralit_server.models.v2 import V2Question, V2Response, V2Suggestion


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

    # (record_id, question_id) -> suggestion value
    sugg_rows = (await db.execute(select(V2Suggestion).where(V2Suggestion.record_id.in_(record_ids)))).scalars().all()
    suggestions = {(s.record_id, s.question_id): s.value for s in sugg_rows}

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
                cells.append(ProjectionCell(question_name=question.name, value=wrapped.get("value"), source="response"))
            elif (record.id, question.id) in suggestions:
                cells.append(
                    ProjectionCell(
                        question_name=question.name,
                        value=suggestions[(record.id, question.id)],
                        source="suggestion",
                    )
                )
            else:
                cells.append(ProjectionCell(question_name=question.name, value=None, source=None))
        projection_records.append(
            ProjectionRecord(record_id=record.id, schema_id=record.schema_id, reference=record.reference, cells=cells)
        )

    return ProjectionView(reference=reference, records=projection_records, total_records=len(records))
