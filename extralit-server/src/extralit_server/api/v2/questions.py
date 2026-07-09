from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import V2QuestionPolicy, authorize
from extralit_server.api.schemas.v2.questions import (
    QuestionCreate,
    QuestionRead,
    Questions,
    QuestionUpdate,
)
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError
from extralit_server.models import User
from extralit_server.models.v2 import Schema, V2Question
from extralit_server.security import auth

router = APIRouter(tags=["v2: questions"])


async def _get_schema_or_404(db: AsyncSession, schema_id: UUID) -> Schema:
    schema = await schemas_ctx.get_schema(db, schema_id)
    if schema is None:
        raise NotFoundError(f"Schema with id `{schema_id}` not found")
    return schema


async def _get_question_or_404(db: AsyncSession, question_id: UUID) -> V2Question:
    # `schema` is eager-loaded here (rather than lazily accessed) because the write policies
    # read `question.schema.workspace_id` synchronously, which AsyncSession cannot lazy-load
    # outside an active greenlet.
    question = await annotation_ctx.get_question(db, question_id, options=[selectinload(V2Question.schema)])
    if question is None:
        raise NotFoundError(f"Question with id `{question_id}` not found")
    return question


@router.post("/schemas/{schema_id}/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    *,
    schema_id: UUID,
    payload: QuestionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, V2QuestionPolicy.create(schema))
    return await annotation_ctx.create_question(db, schema, create=payload)


@router.get("/schemas/{schema_id}/questions", response_model=Questions)
async def list_questions(
    *,
    schema_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    schema = await _get_schema_or_404(db, schema_id)
    await authorize(current_user, V2QuestionPolicy.list(schema))
    return Questions(items=await annotation_ctx.list_questions(db, schema))


@router.get("/questions/{question_id}", response_model=QuestionRead)
async def get_question(
    *,
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await _get_question_or_404(db, question_id)
    await authorize(current_user, V2QuestionPolicy.get(question.schema))
    return question


@router.put("/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    *,
    question_id: UUID,
    payload: QuestionUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await _get_question_or_404(db, question_id)
    await authorize(current_user, V2QuestionPolicy.update(question))
    return await annotation_ctx.update_question(db, question, update=payload)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    *,
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await _get_question_or_404(db, question_id)
    await authorize(current_user, V2QuestionPolicy.delete(question))
    await annotation_ctx.delete_question(db, question)
