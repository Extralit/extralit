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

from typing import Optional, List, TYPE_CHECKING
from pathlib import Path

import typer

from argilla.cli.callback import init_callback
from argilla.cli.rich import get_argilla_themed_panel
from rich.console import Console

if TYPE_CHECKING:
    pass


def get_workspace_client(workspace_name: str):
    """Helper function to get workspace and client"""
    client = init_callback()

    try:
        workspace_data = client.workspaces(workspace_name)
        return client, workspace_data
    except ValueError:
        panel = get_argilla_themed_panel(
            f"Workspace with name={workspace_name} does not exist.",
            title="Workspace not found",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)
    except Exception:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to get the workspace.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


app = typer.Typer(help="Commands for schemas management", no_args_is_help=True)


@app.command(name="upload", help="Upload or update schemas from files in a specified directory")
def upload_schemas_command(
    ctx: typer.Context,
    directory: Path = typer.Argument(
        ...,
        help="Path to the directory containing schema files to upload",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Name of the workspace to which apply the command."),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        is_flag=True,
        help="Force overwrite of existing schemas in the workspace.",
        show_choices=True,
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        help="List of schema names to exclude from the update.",
    ),
) -> None:
    """Upload or update schemas from files in a specified directory."""
    from argilla.cli.schemas.upload import upload_schemas

    client, workspace_data = get_workspace_client(workspace)
    ctx.obj = {
        "client": client,
        "workspace": workspace_data,
    }

    upload_schemas(ctx, directory, overwrite, exclude)


@app.command(name="list", help="List schemas")
def list_schemas(
    ctx: typer.Context,
    workspace: str = typer.Option(..., "--workspace", "-w", help="Name of the workspace to which apply the command."),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Whether to show debug information.",
        show_default=True,
    ),
    csv_path: Optional[Path] = typer.Option(
        None,
        "--csv",
        help="Path to export the output as a CSV file.",
        show_default=False,
    ),
) -> None:
    """List available schemas with optional filtering."""
    from argilla.cli.rich import get_argilla_themed_panel, print_rich_table, console_table_to_pandas_df
    from rich.console import Console

    client, workspace_data = get_workspace_client(workspace)
    ctx.obj = {
        "client": client,
        "workspace": workspace_data,
    }

    console = Console()

    try:
        workspace_schemas = workspace_data.list_schemas()

        if not workspace_schemas.schemas:
            message = f"No schemas found in workspace '{workspace_data.name}'"

            panel = get_argilla_themed_panel(
                message,
                title="No schemas found",
                title_align="left",
            )
            console.print(panel)
            return

        filtered_schemas = [workspace_schemas[schema] for schema in workspace_schemas.ordering]

        if not filtered_schemas:
            message = f"No schemas found in workspace '{workspace_data.name}'"
            panel = get_argilla_themed_panel(
                message,
                title="No schemas found",
                title_align="left",
            )
            console.print(panel)
            return

        table_title = f"Schemas in workspace '{workspace_data.name}'"

        if csv_path:
            table = print_rich_table(filtered_schemas, title=table_title, return_table=True)

            if table:
                df = console_table_to_pandas_df(table)
                df.to_csv(csv_path, index=False)
                console.print(f"Exported {len(filtered_schemas)} schemas to {csv_path}")
        else:
            print_rich_table(filtered_schemas, title=table_title)

    except Exception as e:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when listing schemas",
            title="List Failed",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


@app.command(name="delete", help="Delete a schema")
def delete_schema(
    ctx: typer.Context,
    workspace: str = typer.Option(..., "--workspace", "-w", help="Name of the workspace to which apply the command."),
    schema_id: str = typer.Argument(..., help="ID of the schema to delete"),
) -> None:
    """Delete a specific schema by ID."""
    client, workspace_data = get_workspace_client(workspace)

    try:
        try:
            schema = client.get_schema(workspace=workspace_data.name, schema_id=schema_id)
        except ValueError:
            panel = get_argilla_themed_panel(
                f"Schema with ID '{schema_id}' not found in workspace '{workspace_data.name}'",
                title="Schema not found",
                title_align="left",
                success=False,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

        if not typer.confirm(f"Are you sure you want to delete schema '{schema.name}' ({schema_id})?"):
            panel = get_argilla_themed_panel(
                "Schema deletion cancelled",
                title="Operation Cancelled",
                title_align="left",
            )
            Console().print(panel)
            return

        client.delete_schema(workspace=workspace_data.name, schema_id=schema_id)

        panel = get_argilla_themed_panel(
            f"Schema '{schema.name}' (ID: {schema_id}) successfully deleted from workspace '{workspace_data.name}'",
            title="Schema Deleted",
            title_align="left",
        )
        Console().print(panel)

    except Exception:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when deleting the schema.",
            title="Delete Failed",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="download", help="Download schemas from a workspace")
def download_schemas_command(
    ctx: typer.Context,
    directory: Path = typer.Argument(
        ...,
        help="Directory to save the downloaded schemas",
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Name of the workspace to which apply the command."),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Filter schemas by name",
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        "-e",
        help="List of schema names to exclude from download",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        "-o",
        help="Overwrite existing schema files",
    ),
) -> None:
    """Download schemas from a workspace."""
    from argilla.cli.schemas.download import download_schemas

    client, workspace_data = get_workspace_client(workspace)
    ctx.obj = {
        "client": client,
        "workspace": workspace_data,
    }

    download_schemas(ctx, directory, name, exclude, overwrite)


if __name__ == "__main__":
    app()
