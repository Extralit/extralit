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

"""
Import History CLI commands for managing and exporting import records.

This module provides commands to:
- List import history records for a workspace
- Export import data and metadata to CSV files
- View detailed information about specific imports

The import history provides an audit trail of all BibTeX imports,
storing both the tabular dataframe data and metadata about import
status and associated files for each reference.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit


def list_import_histories(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    history_id: Optional[str] = typer.Argument(None, help="Import history ID to show or export"),
    export: bool = typer.Option(False, "--export", "-e", help="Export the import history to CSV files"),
    output_dir: Path = typer.Option(
        Path("."), "--output-dir", "-o", help="Output directory for CSV files (only used with --export)"
    ),
    debug: bool = typer.Option(False, "--debug", help="Show detailed debug information"),
) -> None:
    """
    Manage import history records for a workspace.

    Commands:
    - history list: List all import histories
    - history {history_id}: Show detailed information about a specific import
    - history {history_id} --export: Export import data to CSV files
    """
    console = Console()

    try:
        # Initialize client and get workspace
        client = Extralit.from_credentials()
        workspace_obj = client.workspaces(name=workspace)
        if not workspace_obj:
            panel = get_themed_panel(
                f"Workspace '{workspace}' not found.",
                title="Workspace not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # If history_id is provided and not "list", show or export specific history
        if history_id and history_id != "list":
            if export:
                _export_import_history_internal(client, workspace_obj, history_id, output_dir, console, debug)
            else:
                _show_import_history_internal(client, workspace_obj, history_id, console, debug)
            return

        # Otherwise, list all histories (either no history_id or history_id is "list")
        _list_import_histories_internal(client, workspace_obj, workspace, console, debug)

    except Exception as e:
        panel = get_themed_panel(
            f"Error managing import histories: {e!s}",
            title="Error",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


def _list_import_histories_internal(
    client: Extralit, workspace_obj, workspace: str, console: Console, debug: bool
) -> None:
    """Internal function to list import histories."""
    # Fetch import histories
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching import histories...", total=None)

        response = client.api.http_client.get(
            f"{client.api_url}/api/v1/imports/history", params={"workspace_id": str(workspace_obj.id)}
        )

        if response.status_code != 200:
            progress.update(task, completed=True, description="Failed to fetch import histories")
            error_detail = response.json().get("detail", str(response.text))
            raise ValueError(f"Error fetching import histories: {error_detail}")

        histories = response.json()
        progress.update(task, completed=True, description=f"Found {len(histories)} import histories")

    # Display results
    if not histories:
        panel = get_themed_panel(
            f"No import histories found for workspace '{workspace}'.",
            title="No Import Histories",
            title_align="left",
            success=True,
        )
        console.print(panel)
        return

    # Create table
    table = Table(title=f"Import Histories for Workspace '{workspace}'")
    table.add_column("ID", style="cyan")
    table.add_column("Filename", style="green")
    table.add_column("User ID", style="blue")
    table.add_column("Created At", style="yellow")
    table.add_column("References", style="magenta")

    for history in histories:
        created_at = datetime.fromisoformat(history["created_at"].replace("Z", "+00:00"))

        # Count references from metadata if available
        metadata = history.get("metadata", {})
        ref_count = len(metadata) if metadata else "N/A"

        table.add_row(
            str(history["id"]),
            history["filename"],
            str(history["user_id"])[:8] + "...",  # Truncate user ID for display
            created_at.strftime("%Y-%m-%d %H:%M:%S"),
            str(ref_count),
        )

    console.print(table)

    panel = get_themed_panel(
        f"Found {len(histories)} import history records. Use 'history <history_id> --export' to download data.",
        title="Import Histories Listed",
        title_align="left",
        success=True,
    )
    console.print(panel)


def _export_import_history_internal(
    client: Extralit, workspace_obj, history_id: str, output_dir: Path, console: Console, debug: bool
) -> None:
    """Internal function to export import history."""
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch detailed import history
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching import history details...", total=None)

        response = client.api.http_client.get(f"{client.api_url}/api/v1/imports/history/{history_id}")

        if response.status_code == 404:
            progress.update(task, completed=True, description="Import history not found")
            panel = get_themed_panel(
                f"Import history with ID '{history_id}' not found.",
                title="Import History Not Found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)
        elif response.status_code != 200:
            progress.update(task, completed=True, description="Failed to fetch import history")
            error_detail = response.json().get("detail", str(response.text))
            raise ValueError(f"Error fetching import history: {error_detail}")

        history = response.json()
        progress.update(task, completed=True, description="Import history retrieved")

    # Extract filename for output files
    base_filename = Path(history["filename"]).stem

    # Export data CSV
    data_csv_path = output_dir / f"{base_filename}_data.csv"
    _export_data_to_csv(history["data"], data_csv_path, console)

    # Export metadata CSV
    metadata_csv_path = output_dir / f"{base_filename}_metadata.csv"
    _export_metadata_to_csv(history["metadata"], metadata_csv_path, console)

    panel = get_themed_panel(
        f"Export completed:\n• Data: {data_csv_path}\n• Metadata: {metadata_csv_path}",
        title="Export Successful",
        title_align="left",
        success=True,
    )
    console.print(panel)


def _show_import_history_internal(
    client: Extralit, workspace_obj, history_id: str, console: Console, debug: bool
) -> None:
    """Internal function to show import history details."""
    # Fetch detailed import history
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching import history details...", total=None)

        response = client.api.http_client.get(f"{client.api_url}/api/v1/imports/history/{history_id}")

        if response.status_code == 404:
            progress.update(task, completed=True, description="Import history not found")
            panel = get_themed_panel(
                f"Import history with ID '{history_id}' not found.",
                title="Import History Not Found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)
        elif response.status_code != 200:
            progress.update(task, completed=True, description="Failed to fetch import history")
            error_detail = response.json().get("detail", str(response.text))
            raise ValueError(f"Error fetching import history: {error_detail}")

        history = response.json()
        progress.update(task, completed=True, description="Import history retrieved")

    # Display summary information
    _display_import_history_summary(history, console)


def _export_data_to_csv(data: dict, output_path: Path, console: Console) -> None:
    """Export tabular dataframe data to CSV file."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting data to CSV...", total=None)

        if not data or "data" not in data:
            progress.update(task, completed=True, description="No data to export")
            console.print("[yellow]Warning: No data found in import history[/yellow]")
            return

        data_rows = data["data"]
        if not data_rows:
            progress.update(task, completed=True, description="No data rows to export")
            console.print("[yellow]Warning: No data rows found[/yellow]")
            return

        # Get field names from schema or first row
        fieldnames = []
        if "schema" in data and "fields" in data["schema"]:
            fieldnames = [field["name"] for field in data["schema"]["fields"]]
        elif data_rows:
            fieldnames = list(data_rows[0].keys())

        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_rows)

        progress.update(task, completed=True, description=f"Exported {len(data_rows)} rows to {output_path.name}")


def _export_metadata_to_csv(metadata: dict, output_path: Path, console: Console) -> None:
    """Export import metadata to CSV file."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting metadata to CSV...", total=None)

        if not metadata:
            progress.update(task, completed=True, description="No metadata to export")
            console.print("[yellow]Warning: No metadata found in import history[/yellow]")
            return

        # Convert metadata to rows
        rows = []
        for reference, meta_info in metadata.items():
            status = meta_info.get("status", "unknown")
            associated_files = meta_info.get("associated_files", [])

            # Create one row per reference with files as comma-separated string
            rows.append(
                {
                    "reference": reference,
                    "status": status,
                    "associated_files": ", ".join(associated_files) if associated_files else "",
                    "files_count": len(associated_files),
                }
            )

        # Write CSV
        fieldnames = ["reference", "status", "associated_files", "files_count"]
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        progress.update(task, completed=True, description=f"Exported {len(rows)} references to {output_path.name}")


def _display_import_history_summary(history: dict, console: Console) -> None:
    """Display summary information about an import history record."""

    # Basic info table
    info_table = Table(title="Import History Information")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")

    created_at = datetime.fromisoformat(history["created_at"].replace("Z", "+00:00"))
    info_table.add_row("ID", str(history["id"]))
    info_table.add_row("Filename", history["filename"])
    info_table.add_row("Workspace ID", str(history["workspace_id"]))
    info_table.add_row("User ID", str(history["user_id"]))
    info_table.add_row("Created At", created_at.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(info_table)

    # Data summary
    data = history.get("data", {})
    schema = data.get("schema", {})
    fields = schema.get("fields", [])[:10]  # Limit to first 5 fields for display
    data_table = Table(title="Data")
    for field in fields:
        data_table.add_column(field.get("name", ""), style="blue", max_width=20, no_wrap=True, overflow="ellipsis")

    for row in data.get("data", []):
        row_values = [str(row.get(field.get("name", ""), "")) for field in fields]
        data_table.add_row(*row_values)

    console.print(data_table)

    # Metadata summary
    metadata = history.get("metadata", {})
    if metadata:
        status_counts = {}
        total_files = 0

        for ref_meta in metadata.values():
            status = ref_meta.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            total_files += len(ref_meta.get("associated_files", []))

        metadata_table = Table(title="Metadata Summary")
        metadata_table.add_column("Property", style="cyan")
        metadata_table.add_column("Value", style="magenta")

        metadata_table.add_row("Total References", str(len(metadata)))
        metadata_table.add_row("Total Files", str(total_files))

        for status, count in status_counts.items():
            metadata_table.add_row(f"Status: {status}", str(count))

        console.print(metadata_table)
