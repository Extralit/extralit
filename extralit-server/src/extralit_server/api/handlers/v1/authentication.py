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

from fastapi import APIRouter, Depends, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.oauth2 import Token
from extralit_server.contexts import accounts
from extralit_server.database import get_async_db
from extralit_server.errors import UnauthorizedError

router = APIRouter(tags=["Authentication"])


@router.post("/token", status_code=status.HTTP_201_CREATED, response_model=Token)
async def create_token(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    user = await accounts.authenticate_user(db, username, password)
    if not user:
        raise UnauthorizedError()

    return Token(access_token=accounts.generate_user_token(user))
