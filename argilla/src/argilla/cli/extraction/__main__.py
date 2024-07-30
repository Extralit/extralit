
from typing import Optional
from argilla.cli.callback import init_callback

import typer

from argilla.cli.extraction.export import export_data

_COMMANDS_REQUIRING_WORKSPACE = ["export"]
_COMMANDS_REQUIRING_ENVFILE = ["export"]

def callback(
    ctx: typer.Context,
    workspace: str = typer.Option(None, help="Name of the workspace to which apply the command."),
    env_file: str = typer.Option(None, help="Path to .env file with environment variables containing S3 credentials."),
) -> None:
    from argilla.client.singleton import active_client
    init_callback()

    if ctx.invoked_subcommand not in _COMMANDS_REQUIRING_ENVFILE:
        return

    if ctx.invoked_subcommand not in _COMMANDS_REQUIRING_WORKSPACE:
        return

    if workspace is None:
        raise typer.BadParameter("The command requires a workspace name provided using '--workspace' option the {typer.style(ctx.invoked_subcommand, bold=True)} keyword")
    elif env_file is None:
        raise typer.BadParameter("The command requires a .env file path provided using '--env-file' option")

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
    
    from dotenv import load_dotenv
    if env_file is not None:
        load_dotenv(env_file)

    from extralit.server.context.files import get_minio_client

    minio_client = get_minio_client()
    ctx.obj = {
        "workspace": workspace,
        "minio_client": minio_client,
    }


app = typer.Typer(help="Commands for extraction data management", no_args_is_help=True, callback=callback)

app.command(name="export", help="List datasets linked to user's workspaces")(export_data)
# app.command(name="delete", help="Deletes a dataset")(delete_dataset)


if __name__ == "__main__":
    app()
