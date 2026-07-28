from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import QuestionPolicy, authorize
from extralit_server.api.schemas.v1.questions import Question as QuestionSchema
from extralit_server.api.schemas.v1.questions import QuestionUpdate
from extralit_server.contexts import questions
from extralit_server.database import get_async_db
from extralit_server.models import Dataset, Question, User
from extralit_server.security import auth

router = APIRouter(tags=["questions"])


@router.patch("/questions/{question_id}", response_model=QuestionSchema)
async def update_question(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    question_id: UUID,
    question_update: QuestionUpdate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await Question.get_or_raise(
        db,
        question_id,
        options=[selectinload(Question.dataset).selectinload(Dataset.fields)],
    )

    await authorize(current_user, QuestionPolicy.update(question))

    return await questions.update_question(db, question, question_update)


@router.delete("/questions/{question_id}", response_model=QuestionSchema)
async def delete_question(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    question_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    question = await Question.get_or_raise(db, question_id, options=[selectinload(Question.dataset)])

    await authorize(current_user, QuestionPolicy.delete(question))

    return await questions.delete_question(db, question)
