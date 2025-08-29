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

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import SuggestionPolicy, authorize
from extralit_server.api.schemas.v1.suggestions import Suggestion as SuggestionSchema
from extralit_server.contexts import datasets
from extralit_server.database import get_async_db
from extralit_server.models import Record, Suggestion, User
from extralit_server.search_engine import SearchEngine, get_search_engine
from extralit_server.security import auth

router = APIRouter(tags=["suggestions"])


@router.delete("/suggestions/{suggestion_id}", response_model=SuggestionSchema)
async def delete_suggestion(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    suggestion_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    suggestion = await Suggestion.get_or_raise(
        db,
        suggestion_id,
        options=[
            selectinload(Suggestion.record).selectinload(Record.dataset),
            selectinload(Suggestion.question),
        ],
    )

    await authorize(current_user, SuggestionPolicy.delete(suggestion))

    return await datasets.delete_suggestion(db, search_engine, suggestion)
