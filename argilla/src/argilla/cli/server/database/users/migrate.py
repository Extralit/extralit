#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import traceback
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import typer
import yaml
from pydantic import BaseModel, constr

from argilla.cli import typer_ext
from argilla.cli.server.database.users.utils import get_or_new_workspace
from argilla.server.database import AsyncSessionLocal
from argilla.server.models import User, UserRole
from argilla.server.security.auth_provider.local.settings import settings
from argilla.server.security.model import USER_USERNAME_REGEX, WORKSPACE_NAME_REGEX

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceCreate(BaseModel):
    name: constr(regex=WORKSPACE_NAME_REGEX, min_length=1)


class UserCreate(BaseModel):
    first_name: constr(strip_whitespace=True)
    last_name: Optional[constr(strip_whitespace=True)]
    username: constr(regex=USER_USERNAME_REGEX, min_length=1)
    role: UserRole
    api_key: constr(min_length=1)
    password_hash: constr(min_length=1)
    workspaces: Optional[List[WorkspaceCreate]]


class UsersMigrator:
    def __init__(self, users_filename: str):
        self._users_filename = users_filename

        if not os.path.exists(users_filename):
            raise ValueError(f"Users file {users_filename!r} does not exist, must set the environment variable ARGILLA_LOCAL_AUTH_USERS_DB_FILE")

        with open(users_filename) as users_file:
            self._users = yaml.safe_load(users_file.read())

    async def migrate(self):
        typer.echo(f"Starting users migration process using file {self._users_filename!r}")

        async with AsyncSessionLocal() as session:
            try:
                for user in self._users:
                    await self._migrate_user(session, user)
                await session.commit()
            except Exception as e:
                await session.rollback()
                traceback.print_exc()  # Print the traceback

                typer.echo("Users migration process failed...")
                raise typer.Exit(code=1)

            typer.echo("Users migration process successfully finished")

    async def _migrate_user(self, session: "AsyncSession", user: dict):
        typer.echo(f"Migrating User with username {user['username']!r}")

        user_create = self._build_user_create(user)

        existing_user = await session.execute(
            select(User).where(User.username == user_create.username).options(selectinload(User.workspaces))
        )
        existing_user = existing_user.scalars().first()

        if existing_user:
            await self._update_user(session, user_create, existing_user)
        else:
            typer.echo(f"Creating User with username {user['username']!r}")
            await User.create(
                session,
                first_name=user_create.first_name,
                username=user_create.username,
                role=user_create.role,
                api_key=user_create.api_key,
                password_hash=user_create.password_hash,
                workspaces=[await get_or_new_workspace(session, workspace.name) for workspace in user_create.workspaces],
                autocommit=False,
            )

    async def _update_user(self, session, user_create, existing_user):
        typer.echo(f"Updating existing User")
        existing_user.api_key = user_create.api_key
        existing_user.password_hash = user_create.password_hash
        existing_user.first_name = user_create.first_name
        existing_user.last_name = user_create.last_name
        if user_create.role:
            existing_user.role = user_create.role
        workspaces = []
        for workspace in user_create.workspaces:
            workspaces.append(await get_or_new_workspace(session, workspace.name))
        existing_user.workspaces = workspaces

        await session.commit()

    def _build_user_create(self, user: dict) -> UserCreate:
        first_name, _, last_name = user.get("full_name", "").partition(" ")
        
        return UserCreate(
            first_name=first_name,
            last_name=last_name,
            username=user["username"],
            role=self._user_role(user),
            api_key=user["api_key"],
            password_hash=user["hashed_password"],
            workspaces=[WorkspaceCreate(name=workspace_name) for workspace_name in self._user_workspace_names(user)],
        )

    def _user_role(self, user: dict) -> UserRole:
        if user.get("role") == 'owner':
            return UserRole.owner

        elif user.get("role") == 'admin':
            return UserRole.admin
        
        elif user.get("role") == 'annotator':
            return UserRole.annotator

        return UserRole.annotator

    def _user_workspace_names(self, user: dict) -> List[str]:
        workspace_names = [workspace_name for workspace_name in user.get("workspaces", [])]

        if user["username"] in workspace_names:
            return workspace_names

        return [user["username"]] + workspace_names


async def migrate():
    """Migrate users defined in YAML file to database."""
    await UsersMigrator(settings.users_db_file).migrate()


if __name__ == "__main__":
    typer_ext.run(migrate)
