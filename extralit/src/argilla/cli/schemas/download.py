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

"""Download schemas from a workspace."""

from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from argilla.cli.rich import get_argilla_themed_panel, print_rich_table


def download_schemas(
    ctx: typer.Context,
    output_dir: Path = typer.Argument(
        ...,
        help="Directory to save the downloaded schemas",
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
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
    console = Console()

    try:
        # Get client and workspace from context
        client = ctx.obj.get("client")
        workspace = ctx.obj.get("workspace")

        if not client or not workspace:
            panel = get_argilla_themed_panel(
                "Client or workspace not found in context. Make sure to specify the workspace with --workspace.",
                title="Missing Context",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get schemas from the workspace
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Fetching schemas from workspace '{workspace.name}'...", total=None)

            # Get schemas
            schema_structure = workspace.list_schemas()

            progress.update(task, completed=True, description=f"Fetched schemas from workspace '{workspace.name}'")

        if not schema_structure.schemas:
            panel = get_argilla_themed_panel(
                f"No schemas found in workspace '{workspace.name}'.",
                title="No schemas found",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Filter schemas by name if provided
        if name:
            schemas = [schema for schema in schema_structure.schemas if name.lower() in schema.name.lower()]
        else:
            schemas = schema_structure.schemas

        # Filter out excluded schemas
        if exclude:
            schemas = [schema for schema in schemas if schema.name not in exclude]

        if not schemas:
            panel = get_argilla_themed_panel(
                f"No schemas found in workspace '{workspace.name}' after applying filters.",
                title="No schemas found",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        downloaded_schemas = []
        skipped_schemas = []
        error_schemas = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            download_task = progress.add_task("Downloading schemas...", total=len(schemas))

            for schema in schemas:
                output_file = output_dir / f"{schema.name}.json"
                progress.update(download_task, description=f"Downloading schema {schema.name}")

                # Check if file exists and skip if not overwriting
                if output_file.exists() and not overwrite:
                    skipped_schemas.append((schema.name, "File already exists"))
                    progress.update(download_task, advance=1)
                    continue

                try:
                    # Save the schema to file
                    with open(output_file, "w") as f:
                        f.write(schema.to_json())

                    downloaded_schemas.append(schema)
                except Exception as e:
                    error_schemas.append((schema.name, str(e)))

                progress.update(download_task, advance=1)

        # Display results
        if skipped_schemas:
            console.print("\n[yellow]Skipped schemas:[/yellow]")
            for name, reason in skipped_schemas:
                console.print(f"  - [yellow]{name}[/yellow]: {reason}")

        if error_schemas:
            console.print("\n[red]Failed schemas:[/red]")
            for name, reason in error_schemas:
                console.print(f"  - [red]{name}[/red]: {reason}")

        if not downloaded_schemas:
            panel = get_argilla_themed_panel(
                f"No schemas were downloaded from workspace '{workspace.name}'.",
                title="No schemas downloaded",
                title_align="left",
                success=False,
            )
            console.print(panel)
            return

        # Show success message
        panel = get_argilla_themed_panel(
            f"Successfully downloaded {len(downloaded_schemas)} schema(s) from workspace '{workspace.name}' to '{output_dir}'.",
            title="Schemas downloaded",
            title_align="left",
            success=True,
        )
        console.print(panel)

        # Display downloaded schemas using print_rich_table
        print_rich_table(
            downloaded_schemas, title=f"Downloaded Schemas from workspace '{workspace.name}'", return_table=False
        )

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error downloading schemas: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
