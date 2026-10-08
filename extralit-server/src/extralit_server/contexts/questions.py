from sqlalchemy.ext.asyncio import AsyncSession

import extralit_server.errors.future as errors
from extralit_server.api.schemas.v1.questions import (
    QuestionCreate,
    QuestionUpdate,
)
from extralit_server.models import Dataset, Question
from extralit_server.validators.questions import (
    QuestionCreateValidator,
    QuestionDeleteValidator,
    QuestionUpdateValidator,
)


async def create_question(db: AsyncSession, dataset: Dataset, question_create: QuestionCreate) -> Question:
    if await Question.get_by(db, name=question_create.name, dataset_id=dataset.id):
        raise errors.NotUniqueError(
            f"Question with name `{question_create.name}` already exists for dataset with id `{dataset.id}`"
        )

    QuestionCreateValidator.validate(question_create, dataset)

    return await Question.create(
        db,
        name=question_create.name,
        title=question_create.title,
        description=question_create.description,
        required=question_create.required,
        settings=question_create.settings.model_dump(),
        dataset_id=dataset.id,
    )


async def update_question(db: AsyncSession, question: Question, question_update: QuestionUpdate) -> Question:
    QuestionUpdateValidator.validate(question_update, question)

    params = question_update.model_dump(exclude_unset=True)

    return await question.update(db, **params)


async def delete_question(db: AsyncSession, question: Question) -> Question:
    QuestionDeleteValidator.validate(question.dataset)

    return await question.delete(db)
