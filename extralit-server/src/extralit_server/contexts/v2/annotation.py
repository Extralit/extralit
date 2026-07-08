"""Business logic for v2 annotation: questions, suggestions, responses (spec §17).

Postgres-only — this module MUST NOT import the LanceDB index engine."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from extralit_server.api.schemas.v2.annotation import ResponseUpsert, SuggestionUpsert
from extralit_server.api.schemas.v2.questions import QuestionCreate, QuestionUpdate
from extralit_server.enums import ResponseStatus
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.v2 import Schema, SchemaVersion, V2Question, V2Record, V2Response, V2Suggestion
from extralit_server.validators.v2.questions import QuestionBindingValidator
from extralit_server.validators.v2.values import V2ResponseValueValidator, V2SuggestionValidator


async def _current_columns_cache(db: AsyncSession, schema: Schema) -> list[dict]:
    if schema.current_version_id is None:
        raise UnprocessableEntityError(
            f"schema `{schema.id}` has no published version; publish a version before adding questions"
        )
    version = await SchemaVersion.get(db, schema.current_version_id)
    return list(version.columns_cache or [])


async def create_question(db: AsyncSession, schema: Schema, *, create: QuestionCreate) -> V2Question:
    columns_cache = await _current_columns_cache(db, schema)
    QuestionBindingValidator.validate(type=create.type, columns=create.columns, columns_cache=columns_cache)
    question = V2Question(
        schema_id=schema.id,
        name=create.name,
        title=create.title,
        description=create.description,
        type=create.type,
        columns=list(create.columns),
        settings=dict(create.settings),
        required=create.required,
    )
    db.add(question)
    await db.commit()
    return question


async def list_questions(db: AsyncSession, schema: Schema) -> list[V2Question]:
    stmt = select(V2Question).where(V2Question.schema_id == schema.id).order_by(V2Question.inserted_at.asc())
    return (await db.execute(stmt)).scalars().all()


async def get_question(
    db: AsyncSession, question_id: UUID, options: list[ExecutableOption] | None = None
) -> V2Question | None:
    return await V2Question.get(db, question_id, options=options)


async def update_question(db: AsyncSession, question: V2Question, *, update: QuestionUpdate) -> V2Question:
    if update.columns is not None:
        schema = await Schema.get_or_raise(db, question.schema_id)
        columns_cache = await _current_columns_cache(db, schema)
        QuestionBindingValidator.validate(type=question.type, columns=update.columns, columns_cache=columns_cache)
        question.columns = list(update.columns)
    for attr in ("title", "description", "settings", "required"):
        value = getattr(update, attr)
        if value is not None:
            setattr(question, attr, value)
    await db.commit()
    return question


async def delete_question(db: AsyncSession, question: V2Question) -> V2Question:
    return await question.delete(db)


async def upsert_suggestion(
    db: AsyncSession, record: V2Record, question: V2Question, *, upsert: SuggestionUpsert
) -> V2Suggestion:
    V2SuggestionValidator.validate(
        upsert.value, upsert.score, type=question.type, settings=question.settings, columns=question.columns
    )
    stmt = select(V2Suggestion).where(V2Suggestion.record_id == record.id, V2Suggestion.question_id == question.id)
    suggestion = (await db.execute(stmt)).scalar_one_or_none()
    if suggestion is None:
        suggestion = V2Suggestion(record_id=record.id, question_id=question.id)
        db.add(suggestion)
    suggestion.value = upsert.value
    suggestion.score = upsert.score
    suggestion.agent = upsert.agent
    suggestion.type = upsert.type
    await db.commit()
    return suggestion


async def list_suggestions(db: AsyncSession, record: V2Record) -> list[V2Suggestion]:
    stmt = select(V2Suggestion).where(V2Suggestion.record_id == record.id).order_by(V2Suggestion.inserted_at.asc())
    return (await db.execute(stmt)).scalars().all()


async def _schema_questions(db: AsyncSession, schema_id) -> list[V2Question]:
    stmt = select(V2Question).where(V2Question.schema_id == schema_id)
    return (await db.execute(stmt)).scalars().all()


def _validate_response_values(upsert: ResponseUpsert, questions: list[V2Question]) -> None:
    values = upsert.values or {}
    submitted = upsert.status == ResponseStatus.submitted
    if submitted and not values:
        raise UnprocessableEntityError("missing response values for submitted response")

    by_name = {q.name: q for q in questions}
    for name in values:
        if name not in by_name:
            raise UnprocessableEntityError(f"response value for non-configured question {name!r}")
    for question in questions:
        if submitted and question.required and question.name not in values:
            raise UnprocessableEntityError(f"missing response value for required question {question.name!r}")
    for name, wrapped in values.items():
        question = by_name[name]
        V2ResponseValueValidator.validate(
            wrapped.get("value"), type=question.type, settings=question.settings, columns=question.columns
        )


async def upsert_response(db: AsyncSession, record: V2Record, user, *, upsert: ResponseUpsert) -> V2Response:
    # NOTE (spec §17.3, §17.5): must never mutate `record.status` and must never touch the
    # LanceDB index engine — this module is Postgres-only (see the module docstring).
    questions = await _schema_questions(db, record.schema_id)
    _validate_response_values(upsert, questions)

    stmt = select(V2Response).where(V2Response.record_id == record.id, V2Response.user_id == user.id)
    response = (await db.execute(stmt)).scalar_one_or_none()
    if response is None:
        response = V2Response(record_id=record.id, user_id=user.id)
        db.add(response)
    response.values = upsert.values
    response.status = upsert.status
    await db.commit()
    return response


async def get_response(db: AsyncSession, record: V2Record, user) -> V2Response | None:
    stmt = select(V2Response).where(V2Response.record_id == record.id, V2Response.user_id == user.id)
    return (await db.execute(stmt)).scalar_one_or_none()
