# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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

    # Prepare metadata with pandera_schema if provided
    metadata = {}
    if question_create.pandera_schema is not None:
        metadata["pandera_schema"] = question_create.pandera_schema

    return await Question.create(
        db,
        name=question_create.name,
        title=question_create.title,
        description=question_create.description,
        required=question_create.required,
        settings=question_create.settings.model_dump(),
        metadata_=metadata if metadata else None,
        dataset_id=dataset.id,
    )


async def update_question(db: AsyncSession, question: Question, question_update: QuestionUpdate) -> Question:
    QuestionUpdateValidator.validate(question_update, question)

    params = question_update.model_dump(exclude_unset=True)
    
    # Handle pandera_schema separately - it goes into metadata
    if "pandera_schema" in params:
        pandera_schema = params.pop("pandera_schema")
        
        # Get existing metadata or create new
        metadata = question.metadata_ or {}
        
        if pandera_schema is not None:
            metadata["pandera_schema"] = pandera_schema
        else:
            # Remove pandera_schema if set to None
            metadata.pop("pandera_schema", None)
        
        params["metadata_"] = metadata if metadata else None

    return await question.update(db, **params)


async def delete_question(db: AsyncSession, question: Question) -> Question:
    QuestionDeleteValidator.validate(question.dataset)

    return await question.delete(db)
