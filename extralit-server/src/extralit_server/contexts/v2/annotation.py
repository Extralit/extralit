"""Business logic for v2 annotation: questions, suggestions, responses (spec §17).

Postgres-only — this module MUST NOT import the LanceDB index engine."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from extralit_server.api.schemas.v2.questions import QuestionCreate, QuestionUpdate
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.v2 import Schema, SchemaVersion, V2Question
from extralit_server.validators.v2.questions import QuestionBindingValidator


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
