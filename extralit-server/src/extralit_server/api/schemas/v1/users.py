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

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.enums import UserRole

USER_PASSWORD_MIN_LENGTH = 8
USER_PASSWORD_MAX_LENGTH = 100

UserFirstName = Annotated[
    constr(min_length=1, strip_whitespace=True), Field(..., description="The first name for the user")
]
UserLastName = Annotated[
    constr(min_length=1, strip_whitespace=True), Field(..., description="The last name for the user")
]
UserUsername = Annotated[str, Field(..., min_length=1, description="The username for the user")]

UserPassword = Annotated[
    str,
    Field(
        ...,
        min_length=USER_PASSWORD_MIN_LENGTH,
        max_length=USER_PASSWORD_MAX_LENGTH,
        description="The password for the user",
    ),
]


class User(BaseModel):
    id: UUID
    first_name: str
    last_name: str | None = None
    username: str
    role: UserRole
    # TODO: We need to move `api_key` outside of this schema and think about a more
    # secure way to expose it, along with ways to expire it and create new API keys.
    api_key: str
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    id: UUID | None = None
    first_name: UserFirstName
    last_name: UserLastName | None = None
    username: UserUsername
    role: UserRole | None = None
    password: UserPassword


class UserUpdate(UpdateSchema):
    __non_nullable_fields__ = {"first_name", "username", "role", "password"}

    first_name: UserFirstName | None = None
    last_name: UserLastName | None = None
    username: UserUsername | None = None
    role: UserRole | None = None
    password: UserPassword | None = None


class Users(BaseModel):
    items: list[User]
