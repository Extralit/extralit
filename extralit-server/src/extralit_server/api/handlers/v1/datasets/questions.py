from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from extralit_server.api.policies.v1 import DatasetPolicy, authorize
from extralit_server.api.schemas.v1.questions import Question, QuestionCreate, Questions
from extralit_server.contexts import questions
from extralit_server.database import get_async_db
from extralit_server.models import Dataset, User
from extralit_server.security import auth

router = APIRouter()


@router.get("/datasets/{dataset_id}/questions", response_model=Questions)
async def list_dataset_questions(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id, options=[selectinload(Dataset.questions)])

    await authorize(current_user, DatasetPolicy.get(dataset))

    return Questions(items=dataset.questions)


@router.post("/datasets/{dataset_id}/questions", status_code=status.HTTP_201_CREATED, response_model=Question)
async def create_dataset_question(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    question_create: QuestionCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    # TODO: Review this flow since we're putting logic here that will be used internally by the context
    #  Fields and questions are required to apply validations.
    dataset = await Dataset.get_or_raise(
        db,
        dataset_id,
        options=[
            selectinload(Dataset.fields),
            selectinload(Dataset.questions),
        ],
    )

    await authorize(current_user, DatasetPolicy.create_question(dataset))

    return await questions.create_question(db, dataset, question_create)
