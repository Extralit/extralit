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
from typing import Dict

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def list_import_histories(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    debug: bool = typer.Option(False, "--debug", help="Show detailed debug information"),
) -> None:
    """
    List import history records for a workspace.

    Shows a table of all import history records including filename,
    creation date, and basic statistics about the import.
    """
    console = Console()

    try:
        # Initialize client and get workspace
        client = Argilla.from_credentials()
        workspace_obj = client.workspaces(name=workspace)
        if not workspace_obj:
            panel = get_argilla_themed_panel(
                f"Workspace '{workspace}' not found.",
                title="Workspace not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

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
            panel = get_argilla_themed_panel(
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
                str(history["id"])[:8] + "...",  # Truncate ID for display
                history["filename"],
                str(history["user_id"])[:8] + "...",  # Truncate user ID for display
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                str(ref_count),
            )

        console.print(table)

        panel = get_argilla_themed_panel(
            f"Found {len(histories)} import history records. Use 'export-import-history' to download data.",
            title="Import Histories Listed",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error listing import histories: {str(e)}",
            title="Error",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


def export_import_history(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    history_id: str = typer.Option(..., "--history-id", "-h", help="Import history ID to export"),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="Output directory for CSV files"),
    debug: bool = typer.Option(False, "--debug", help="Show detailed debug information"),
) -> None:
    """
    Export import history data and metadata to CSV files.

    Creates two CSV files:
    - {filename}_data.csv: Tabular dataframe data from the BibTeX import
    - {filename}_metadata.csv: Import status and associated files for each reference
    """
    console = Console()

    try:
        # Initialize client and get workspace
        client = Argilla.from_credentials()
        workspace_obj = client.workspaces(name=workspace)
        if not workspace_obj:
            panel = get_argilla_themed_panel(
                f"Workspace '{workspace}' not found.",
                title="Workspace not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

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
                panel = get_argilla_themed_panel(
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

        panel = get_argilla_themed_panel(
            f"Export completed:\n• Data: {data_csv_path}\n• Metadata: {metadata_csv_path}",
            title="Export Successful",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error exporting import history: {str(e)}",
            title="Error",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


def _export_data_to_csv(data: Dict, output_path: Path, console: Console) -> None:
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


def _export_metadata_to_csv(metadata: Dict, output_path: Path, console: Console) -> None:
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


def show_import_history(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    history_id: str = typer.Option(..., "--history-id", "-h", help="Import history ID to show"),
    debug: bool = typer.Option(False, "--debug", help="Show detailed debug information"),
) -> None:
    """
    Show detailed information about a specific import history record.

    Displays summary statistics, data schema, and metadata overview
    without exporting to files.
    """
    console = Console()

    try:
        # Initialize client and get workspace
        client = Argilla.from_credentials()
        workspace_obj = client.workspaces(name=workspace)
        if not workspace_obj:
            panel = get_argilla_themed_panel(
                f"Workspace '{workspace}' not found.",
                title="Workspace not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

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
                panel = get_argilla_themed_panel(
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

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error showing import history: {str(e)}",
            title="Error",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


def _display_import_history_summary(history: Dict, console: Console) -> None:
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
    data_rows = data.get("data", [])
    schema = data.get("schema", {})
    fields = schema.get("fields", [])

    data_table = Table(title="Data Summary")
    data_table.add_column("Property", style="cyan")
    data_table.add_column("Value", style="yellow")

    data_table.add_row("Total Records", str(len(data_rows)))
    data_table.add_row("Fields Count", str(len(fields)))
    data_table.add_row("Primary Key", ", ".join(schema.get("primaryKey", [])))

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

    # Fields schema if available
    if fields:
        fields_table = Table(title="Data Schema Fields")
        fields_table.add_column("Field Name", style="cyan")
        fields_table.add_column("Type", style="green")

        for field in fields:
            fields_table.add_row(field.get("name", ""), field.get("type", ""))

        console.print(fields_table)
