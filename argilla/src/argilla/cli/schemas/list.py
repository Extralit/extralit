from pathlib import Path
from typing import Dict, Optional, List
import typer

from argilla.client.workspaces import Workspace
from extralit.extraction.models import SchemaStructure, DEFAULT_SCHEMA_S3_PATH


def list_schemas(
    ctx: typer.Context,
    include_version: bool = typer.Option(
        False,
        "--versions",
        "-v",
        help="Whether to list multiple schema versions.",
        show_default=True,
        is_flag=True,
    ),
    path: Path = typer.Option(
        DEFAULT_SCHEMA_S3_PATH,
        "--path",
        "-p",
        help="The directory prefix containing the schema files in the Workspace's S3 bucket.",
        show_default=True,
    ),
) -> None:
    from argilla.cli.rich import echo_in_panel, get_argilla_themed_table
    from rich.console import Console

    console = Console()

    try:
        workspace: Workspace = ctx.obj["workspace"]
        workspace_schemas = workspace.list_files(path, include_version=include_version)

        table = get_argilla_themed_table(title=f"Workspace (name='{workspace.name}') Schemas", show_lines=True)
        for column in ("Schema Name", "Version ID", "Version Tag", "Last Update Date", "Metadata"):
            table.add_column(column, justify="left")

        schema_names = set()
        for file_object in workspace_schemas.objects:            
            if not file_object.etag:
                # Skip alias files
                continue

            schema_name = file_object.object_name.split("/", 1)[-1]

            if not include_version:
                if schema_name in schema_names:
                    continue
                schema_names.add(schema_name)

            table.add_row(
                schema_name,
                file_object.version_id,
                file_object.version_tag,
                file_object.last_modified.isoformat(sep=" "),
                str(file_object.metadata),
            )

        console.print(table)

    except Exception as e:
        echo_in_panel(
            f"Unable to list schemas in workspace:\n{e}", 
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1) from e
