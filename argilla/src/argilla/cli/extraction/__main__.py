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
from argilla.cli.rich import get_argilla_themed_panel
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live


# Commands that require specific parameters
_COMMANDS_REQUIRING_WORKSPACE = ["export"]
_COMMANDS_REQUIRING_ENVFILE = ["export"]


def callback(
    ctx: typer.Context,
    workspace: str = typer.Option(None, help="Name of the workspace to which apply the command."),
    env_file: str = typer.Option(None, help="Path to .env file with environment variables containing S3 credentials."),
) -> None:
    if ctx.resilient_parsing or "--help" in sys.argv or "-h" in sys.argv:
        return

    if (
        ctx.invoked_subcommand not in _COMMANDS_REQUIRING_WORKSPACE
        and ctx.invoked_subcommand not in _COMMANDS_REQUIRING_ENVFILE
    ):
        return

    # Check required parameters based on command
    if ctx.invoked_subcommand in _COMMANDS_REQUIRING_WORKSPACE and workspace is None:
        raise typer.BadParameter(
            f"The command requires a workspace name provided using '--workspace' option before the {typer.style(ctx.invoked_subcommand, bold=True)} keyword"
        )

    if ctx.invoked_subcommand in _COMMANDS_REQUIRING_ENVFILE and env_file is None:
        raise typer.BadParameter("The command requires a .env file path provided using '--env-file' option")

    try:
        # Initialize the client
        client = init_callback()

        # Validate the workspace if provided
        workspace_data = None
        if workspace:
            try:
                workspace_data = client.workspaces(workspace)
            except ValueError:
                panel = get_argilla_themed_panel(
                    f"Workspace with name={workspace} does not exist.",
                    title="Workspace not found",
                    title_align="left",
                    success=False,
                )
                Console().print(panel)
                raise typer.Exit(code=1)

        # Load environment variables from .env file if provided
        if env_file:
            try:
                # Load environment variables from .env file
                from dotenv import load_dotenv

                load_dotenv(env_file)

                panel = get_argilla_themed_panel(
                    f"Loaded environment variables from {env_file}",
                    title="Environment Loaded",
                    title_align="left",
                )
                Console().print(panel)
            except Exception as e:
                panel = get_argilla_themed_panel(
                    f"Failed to load environment variables from {env_file}: {str(e)}",
                    title="Environment Load Failed",
                    title_align="left",
                    success=False,
                )
                Console().print(panel)
                raise typer.Exit(code=1)

        # Store the client and workspace in the context
        ctx.obj = {
            "client": client,
            "workspace": workspace_data or {"name": workspace} if workspace else None,
        }

    except ValueError:
        panel = get_argilla_themed_panel(
            f"Workspace with name={workspace} does not exist.",
            title="Workspace not found",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)

    except Exception:
        panel = get_argilla_themed_panel(
            "An unexpected error occurred when trying to initialize extraction.",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


app = typer.Typer(
    name="extraction",
    help="Commands for data extraction operations.",
    callback=callback,
)


@app.command(name="export", help="Export extraction data to S3 storage")
def export(
    ctx: typer.Context,
    output_path: str = typer.Option(
        "exported-data",
        "--output",
        help="The path where the exported data will be stored.",
    ),
) -> None:
    """Export extraction data to S3 storage."""
    try:
        # Get client and workspace from context
        client = ctx.obj["client"]
        workspace = ctx.obj["workspace"]

        # Display export information
        panel = get_argilla_themed_panel(
            f"Starting export of extraction data for workspace '{workspace['name']}'",
            title="Export Started",
            title_align="left",
        )
        Console().print(panel)

        # Start the export process
        spinner = Spinner(
            name="dots",
            text="Exporting data...",
        )

        with Live(spinner, refresh_per_second=20):
            # Perform the actual export
            client.export_extraction_data(workspace=workspace["name"], output_path=output_path)

        # Show completion message
        panel = get_argilla_themed_panel(
            f"Extraction data successfully exported to {output_path}\n" f"• Workspace: {workspace['name']}\n",
            title="Export Complete",
            title_align="left",
        )
        Console().print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"An unexpected error occurred during data export: {str(e)}",
            title="Export Failed",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


@app.command(name="status", help="Check extraction status")
def check_status(
    ctx: typer.Context,
    dataset: Optional[str] = typer.Option(None, help="The name of the dataset to check status for."),
) -> None:
    """Check status of the extraction process."""
    try:
        # Get client from context
        client = ctx.obj["client"]
        workspace = ctx.obj["workspace"]["name"] if ctx.obj.get("workspace") else None

        # Get extraction status from the API
        status_records = client.get_extraction_status(dataset_name=dataset, workspace=workspace)

        # Create a status table
        from rich.table import Table

        table = Table(title="Extraction Status")
        table.add_column("Dataset", justify="left")
        table.add_column("Type", justify="left")
        table.add_column("Status", justify="center")
        table.add_column("Records", justify="right")
        table.add_column("Last Updated", justify="center")

        # Add data rows from the API response
        if status_records:
            for record in status_records:
                # Format the status with an emoji
                status_text = record["status"]
                if status_text.lower() == "complete":
                    status_display = "✅ Complete"
                elif "progress" in status_text.lower():
                    status_display = "🔄 " + status_text
                elif "fail" in status_text.lower():
                    status_display = "❌ " + status_text
                else:
                    status_display = status_text

                # Format the record count with commas
                record_count = f"{record['records']:,}" if record["records"] else "0"

                # Format the last updated date
                last_updated = record["last_updated"].strftime("%Y-%m-%d %H:%M:%S") if record["last_updated"] else ""

                table.add_row(record["dataset"], record["type"], status_display, record_count, last_updated)
        else:
            # No records found
            table.add_row("No extraction data found", "", "", "", "")

        Console().print(table)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"An unexpected error occurred when checking extraction status: {str(e)}",
            title="Status Check Failed",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
