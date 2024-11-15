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

import sys
from typing import Optional

import typer

from argilla.cli.callback import init_callback
from argilla.cli.rich import get_argilla_themed_panel, print_rich_table
from argilla._models._user import Role

from rich.console import Console


_COMMANDS_REQUIRING_WORKSPACE = ["add-user", "delete-user"]


def callback(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, help="Name of the workspace to which apply the command."),
) -> None:
    if ctx.resilient_parsing or "--help" in sys.argv or "-h" in sys.argv:
        return

    client = init_callback()

    if ctx.invoked_subcommand not in _COMMANDS_REQUIRING_WORKSPACE:
        return

    if name is None:
        raise typer.BadParameter(
            f"The command requires a workspace name provided using '--name' option before the {typer.style(ctx.invoked_subcommand, bold=True)} keyword"
        )

    try:
        workspace = client.workspaces(name)
        ctx.obj = workspace
    except ValueError:
        panel = get_argilla_themed_panel(
            f"Workspace with name={name} does not exist.",
            title="Workspace not found",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to get the workspace from the Extralit server",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


app = typer.Typer(help="Commands for workspace management", no_args_is_help=True, callback=callback)


@app.command(name="create", help="Create a workspace")
def create_workspace(
    name: str = typer.Argument(
        ...,
        help="The name of the workspace to be created",
    ),
) -> None:
    """Creates a workspace for the logged user in Extralit."""
    try:
        # Initialize the client
        client = init_callback()

        # Create a workspace object with the provided name
        from argilla.workspaces import Workspace

        workspace = Workspace(name=name)

        # Add the workspace using the proper API
        client.workspaces.add(workspace)

        # Display success message
        panel = get_argilla_themed_panel(
            f"Workspace with the name={name} successfully created.", title="Workspace created", title_align="left"
        )
        Console().print(panel)
    except ValueError:
        panel = get_argilla_themed_panel(
            f"Workspace with name={name} already exists.",
            title="Workspace already exists",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to create the workspace.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="list", help="Lists workspaces of the logged user")
def list_workspaces() -> None:
    """List the workspaces in Extralit and prints them on the console."""
    try:
        client = init_callback()
        workspaces = client.workspaces.list()

        print_rich_table(workspaces)
    except RuntimeError:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to list workspaces.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="add-user", help="Adds a user to a workspace")
def add_user(
    ctx: typer.Context,
    username: str = typer.Argument(..., help="The username of the user to be added to the workspace"),
    role: str = typer.Option("annotator", help="The role of the user in the workspace (annotator, owner)"),
) -> None:
    """Adds a user to a workspace."""
    workspace = ctx.obj

    try:
        client = init_callback()

        user = client.users(username)

        if user.role == Role.owner:
            panel = get_argilla_themed_panel(
                f"User with name={username} is an owner. Users with owner role don't need specific permissions per"
                " workspace, as those are super-users with privileges over everything under Extralit.",
                title="User is owner",
                title_align="left",
                success=False,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

        workspace_obj = client.workspaces(name=workspace["name"])
        if not workspace_obj:
            raise ValueError(f"Workspace with name={workspace['name']} not found.")

        user_obj = client.users(username=username)
        if not user_obj:
            raise ValueError(f"User with username={username} not found.")

        from argilla._api._workspaces import WorkspaceUserRole

        workspace_obj.add_user(user=user_obj, role=WorkspaceUserRole(role))

        # Display success message
        panel = get_argilla_themed_panel(
            f"User with username={username} has been added to workspace={workspace['name']}",
            title="User added",
            title_align="left",
        )
        Console().print(panel)
    except ValueError:
        panel = get_argilla_themed_panel(
            f"User with username={username} doesn't exist.",
            title="User not found",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to add user to the workspace.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="delete-user", help="Deletes a user from a workspace")
def delete_user(
    ctx: typer.Context,
    username: str = typer.Argument(..., help="The username of the user to be removed from the workspace"),
) -> None:
    """Removes a user from a workspace."""
    workspace = ctx.obj

    try:
        client = init_callback()

        user = client.users(username)

        if user.role == Role.owner:
            panel = get_argilla_themed_panel(
                f"User with name={username} is an owner. Users with owner role don't need specific permissions per"
                " workspace, as those are super-users with privileges over everything under Extralit.",
                title="User is owner",
                title_align="left",
                success=False,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

        workspace_obj = client.workspaces(name=workspace["name"])
        if not workspace_obj:
            raise ValueError(f"Workspace with name={workspace['name']} not found.")

        user_obj = client.users(username=username)
        if not user_obj:
            raise ValueError(f"User with username={username} not found.")

        workspace_obj.remove_user(user=user_obj)

        panel = get_argilla_themed_panel(
            f"User with username={username} has been removed from workspace={workspace['name']}",
            title="User removed",
            title_align="left",
        )
        Console().print(panel)
    except ValueError:
        panel = get_argilla_themed_panel(
            f"User with username={username} doesn't exist.",
            title="User not found",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to remove user from the workspace.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
