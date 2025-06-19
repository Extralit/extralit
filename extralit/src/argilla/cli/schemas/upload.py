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

from pathlib import Path
import os
import glob
from typing import Optional, List
import typer


def upload_schemas(
    ctx: typer.Context,
    path: Path = typer.Argument(
        ...,
        help="The directory containing the JSON schema files to be updated to the Workspace files.",
    ),
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
    from argilla.cli.rich import get_argilla_themed_panel, print_rich_table
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

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

        # Find all JSON files in the directory
        schema_files = glob.glob(os.path.join(path, "*.json"))

        if not schema_files:
            panel = get_argilla_themed_panel(
                f"No schema files found in directory '{path}'.",
                title="No schemas found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Filter out excluded schemas
        if exclude:
            schema_files = [f for f in schema_files if os.path.splitext(os.path.basename(f))[0] not in exclude]

        if not schema_files:
            panel = get_argilla_themed_panel(
                f"All schema files in directory '{path}' were excluded.",
                title="No schemas to upload",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Load schemas from files
        loaded_schemas = []
        skipped_schemas = []
        error_schemas = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            load_task = progress.add_task("Loading schema files...", total=len(schema_files))

            for schema_file in schema_files:
                file_name = os.path.basename(schema_file)
                progress.update(load_task, description=f"Loading schema from {file_name}")

                try:
                    import pandera as pa

                    schema = pa.DataFrameSchema.from_json(schema_file)
                    loaded_schemas.append(schema)
                except Exception as e:
                    error_schemas.append((file_name, str(e)))
                    progress.update(load_task, advance=1)
                    continue

                progress.update(load_task, advance=1)

        # Upload schemas
        uploaded_schemas = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            upload_task = progress.add_task("Uploading schemas...", total=len(loaded_schemas))

            for schema in loaded_schemas:
                progress.update(upload_task, description=f"Uploading schema {schema.name}")

                try:
                    # Add schema to workspace
                    workspace.add_schema(schema)
                    uploaded_schemas.append(schema)
                except ValueError as e:
                    if "already exists" in str(e) and not overwrite:
                        skipped_schemas.append((schema.name, str(e)))
                    else:
                        error_schemas.append((schema.name, str(e)))
                except Exception as e:
                    error_schemas.append((schema.name, str(e)))

                progress.update(upload_task, advance=1)

        # Display results
        if skipped_schemas:
            console.print("\n[yellow]Skipped schemas:[/yellow]")
            for name, reason in skipped_schemas:
                console.print(f"  - [yellow]{name}[/yellow]: {reason}")

        if error_schemas:
            console.print("\n[red]Failed schemas:[/red]")
            for name, reason in error_schemas:
                console.print(f"  - [red]{name}[/red]: {reason}")

        if not uploaded_schemas:
            panel = get_argilla_themed_panel(
                f"No schemas were uploaded to workspace '{workspace.name}'.",
                title="No schemas uploaded",
                title_align="left",
                success=False,
            )
            console.print(panel)
            return

        # Show success message
        panel = get_argilla_themed_panel(
            f"Successfully uploaded {len(uploaded_schemas)} schema(s) to workspace '{workspace.name}'.",
            title="Schemas uploaded",
            title_align="left",
        )
        console.print(panel)

        # Display uploaded schemas using print_rich_table
        print_rich_table(
            uploaded_schemas, title=f"Uploaded Schemas in workspace '{workspace.name}'", return_table=False
        )

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Unable to update schemas in workspace: {str(e)}",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1) from e
