
from typing import Optional
from argilla.cli.callback import init_callback

import typer

from argilla.cli.schemas.upload import upload_schemas
from argilla.cli.schemas.list import list_schemas
from argilla.cli.schemas.delete import delete_schema

_COMMANDS_REQUIRING_WORKSPACE = ["upload", "list", "delete"]

def callback(
    ctx: typer.Context,
    workspace: str = typer.Option(
        None, 
        "--workspace", 
        "-n", 
        help="Name of the workspace to which apply the command."
    ),
) -> None:
    from argilla.client.singleton import active_client
    init_callback()

    if ctx.invoked_subcommand not in _COMMANDS_REQUIRING_WORKSPACE:
        return

    if workspace is None:
        raise typer.BadParameter(f"The command requires a workspace name provided using '--workspace' option before the {typer.style(ctx.invoked_subcommand, bold=True)} keyword")

    from argilla.cli.rich import echo_in_panel
    from argilla.client.workspaces import Workspace

    try:
        workspace = Workspace.from_name(workspace)
    except ValueError as e:
        echo_in_panel(
            f"Workspace with name={workspace} does not exist.",
            title="Workspace not found",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1) from e
    except RuntimeError as e:
        echo_in_panel(
            "An unexpected error occurred when trying to get the workspace from the Argilla server",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1) from e
    
    ctx.obj = {
        "workspace": workspace,
    }


app = typer.Typer(help="Commands for schemas file management", no_args_is_help=True, callback=callback)

app.command(name="upload", help="Upload or update schemas from files in a specified directory.")(upload_schemas)
app.command(name="list", help="List schemas.")(list_schemas)
app.command(name="delete", help="Delete a schema.")(delete_schema)


if __name__ == "__main__":
    app()
