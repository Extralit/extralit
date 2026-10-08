import asyncio

import typer

from extralit_server.contexts import accounts
from extralit_server.database import AsyncSessionLocal
from extralit_server.models import UserRole


async def _update(username: str, role: UserRole):
    async with AsyncSessionLocal() as session:
        user = await accounts.get_user_by_username(session, username)

        if not user:
            typer.echo(f"User with username {username!r} does not exists in database. Skipping...")
            return

        if user.role == role:
            typer.echo(f"User {username!r} already has role {role.value!r}. Skipping...")
            return

        old_role = user.role

        user = await user.update(session, role=role)

        typer.echo(f"User {username!r} successfully updated:")
        typer.echo(f"• role: {old_role.value!r} -> {user.role.value!r}")


def update(
    username: str = typer.Argument(
        default=None,
        help="Username as a lowercase string without spaces allowing letters, numbers, dashes and underscores.",
    ),
    role: UserRole = typer.Option(
        prompt=True,
        default=None,
        show_default=False,
        help="New role for the user.",
    ),
):
    asyncio.run(_update(username, role))


if __name__ == "__main__":
    typer.run(update)
