
from typing import Optional
from argilla.cli.callback import init_callback

import typer

_COMMANDS_REQUIRING_WORKSPACE = ["export"]

def callback(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, help="Name of the workspace to which apply the command."),
) -> None:
    from argilla.client.singleton import active_client
    init_callback()

    if ctx.invoked_subcommand not in _COMMANDS_REQUIRING_WORKSPACE:
        return

    if name is None:
        raise typer.BadParameter("The command requires a workspace name provided using '--name' option")

    from argilla.cli.rich import echo_in_panel
    from argilla.client.workspaces import Workspace

    try:
        workspace = Workspace.from_name(name)
    except ValueError as e:
        echo_in_panel(
            f"Workspace with name={name} does not exist.",
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

    ctx.obj = workspace


app = typer.Typer(help="Commands for extraction data management", no_args_is_help=True, callback=callback)

# app.command(name="list", help="List datasets linked to user's workspaces")(list_datasets)
# app.command(name="delete", help="Deletes a dataset")(delete_dataset)


if __name__ == "__main__":
    app()
