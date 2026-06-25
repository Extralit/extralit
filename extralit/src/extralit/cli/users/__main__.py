from typing import Optional

import typer

from extralit._models._user import Role
from extralit.cli.callback import init_callback
from extralit.cli.rich import print_rich_table


def callback() -> None:
    """Callback for users commands."""
    init_callback()


app = typer.Typer(help="Commands for user management", no_args_is_help=True, callback=callback)


@app.command(name="create", help="Creates a new user")
def create_user(
    username: str = typer.Option(..., prompt=True, help="The username of the user to be created"),
    password: str = typer.Option(
        ..., prompt=True, confirmation_prompt=True, hide_input=True, help="The password of the user to be created"
    ),
    first_name: Optional[str] = typer.Option(None, help="The first name of the user to be created"),
    last_name: Optional[str] = typer.Option(None, help="The last name of the user to be created"),
    role: Role = typer.Option(Role.annotator, help="The role of the user to be created"),
    workspaces: Optional[list[str]] = typer.Option(
        None,
        "--workspace",
        help="A workspace name to which the user will be linked to. This option can be provided several times.",
    ),
) -> None:
    """Creates a new user in the system."""
    from rich.console import Console

    from extralit.cli.rich import get_themed_panel
    from extralit.users._resource import User

    try:
        client = init_callback()

        user = User(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            client=client,
        )

        user.create()

        linked_workspaces: list[str] = []
        unknown_workspaces: list[str] = []
        for workspace_name in workspaces or []:
            workspace = client.workspaces(name=workspace_name)
            if workspace is None:
                unknown_workspaces.append(workspace_name)
                continue
            user.add_to_workspace(workspace)
            linked_workspaces.append(workspace_name)

        title = "User created"
        if linked_workspaces:
            title += f" (linked to workspaces: {', '.join(linked_workspaces)})"

        print_rich_table(
            [user],
            title=title,
        )

        if unknown_workspaces:
            panel = get_themed_panel(
                "User was created, but the following workspaces were not found and "
                f"could not be linked: {', '.join(unknown_workspaces)}.",
                title="Some workspaces not linked",
                title_align="left",
                success=False,
            )
            Console().print(panel)
    except KeyError:
        panel = get_themed_panel(
            f"User with name={username} already exists.",
            title="User already exists",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except ValueError as e:
        panel = get_themed_panel(
            f"Provided parameters are not valid:\n\n{e}", title="Invalid parameters", title_align="left", success=False
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError:
        panel = get_themed_panel(
            "An unexpected error occurred when trying to create the user.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="list", help="List users")
def list_users(
    workspace: Optional[str] = typer.Option(None, help="Filter users by workspace"),
    role: Optional[str] = typer.Option(
        None, help="Filter users by role", autocompletion=lambda: [role.value for role in Role]
    ),
) -> None:
    """List all users in the system with optional filtering."""
    from rich.console import Console

    from extralit.cli.rich import get_themed_panel

    try:
        client = init_callback()

        users = []
        if workspace:
            workspace_obj = client.workspaces(name=workspace)

            if workspace_obj is None:
                panel = get_themed_panel(
                    f"Workspace with name={workspace} doesn't exist.",
                    title="Workspace not found",
                    title_align="left",
                    success=False,
                )
                Console().print(panel)
                raise typer.Exit(code=1)

            users = workspace_obj.users
        elif client.me.role == Role.admin:
            users = client.users.list()
        else:
            raise typer.BadParameter(
                "You are not authorized to list all users, please specify a workspace with --workspace"
            )

        if role:
            users = [user for user in users if user.role == role]

        print_rich_table(
            users,
            title="Users",
        )
    except RuntimeError:
        panel = get_themed_panel(
            "An unexpected error occurred when trying to list users.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="delete", help="Deletes a user")
def delete_user(
    username: str = typer.Option(..., help="Username of the user to be deleted"),
) -> None:
    """Delete a user from the system."""
    from rich.console import Console

    from extralit.cli.rich import get_themed_panel

    try:
        # Initialize the client
        client = init_callback()

        user = client.users(username=username)
        user.delete()
        panel = get_themed_panel(
            f"User with username={username} has been removed.", title="User removed", title_align="left"
        )
        Console().print(panel)
    except ValueError:
        panel = get_themed_panel(
            f"User with username={username} doesn't exist.", title="User not found", title_align="left", success=False
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except RuntimeError:
        panel = get_themed_panel(
            "An unexpected error occurred when trying to remove the user.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
