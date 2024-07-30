import os
from pathlib import Path
from typing import Dict, Optional, List
import typer

from argilla.client.workspaces import Workspace
from extralit.extraction.models import SchemaStructure, DEFAULT_SCHEMA_S3_PATH

def delete_schema(
    ctx: typer.Context,
    schema_name: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help="The schema name contained in the Workspace.",
        show_default=True,
    ),
    version_id: Optional[str] = typer.Option(
        None,
        "--version-id",
        "-v",
        help="The version ID of the schema to delete.",
    ),
) -> None:
    from argilla.cli.rich import echo_in_panel, get_argilla_themed_table
    from rich.console import Console

    try:
        workspace: Workspace = ctx.obj["workspace"]
        path = os.path.join(DEFAULT_SCHEMA_S3_PATH, schema_name)
        workspace.delete_file(path, version_id=version_id)

        echo_in_panel(
            f"Schema (name='{schema_name}') in workspace '{workspace.name}' have been deleted successfully.",
            title="File deleted",
            title_align="left",
        )

    except Exception as e:
        echo_in_panel(
            f"Unable to list schemas in workspace:\n{e}", 
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1) from e
