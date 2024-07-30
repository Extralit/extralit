from pathlib import Path
from typing import Dict, Optional, List
import typer

from argilla.client.workspaces import Workspace
from extralit.extraction.models import SchemaStructure

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
    from argilla.cli.rich import echo_in_panel, get_argilla_themed_table

    from rich.console import Console

    console = Console()

    try:
        workspace: Workspace = ctx.obj["workspace"]

        update_schemas = SchemaStructure.from_dir(path, exclude=exclude)

        if not update_schemas.schemas:
            raise FileNotFoundError(f"No schemas found in directory '{path}'.")
        
        uploaded_files = workspace.update_schemas(update_schemas, check_existing=not overwrite)

        if uploaded_files.objects:
            echo_in_panel(
                f"Schemas in workspace '{workspace.name}' have been updated successfully.",
                title="Schemas updated",
                title_align="left",
            )

        table = get_argilla_themed_table(title=f"Updated Workspace (name='{workspace.name}') Schemas", show_lines=True)
        for column in ("Schema Name", "Version ID", "Version Tag", "Last Update Date"):
            table.add_column(column, justify="left")

        for uploaded_file in uploaded_files.objects:
            updated_schema = workspace.list_files(uploaded_file.object_name, include_version=True)
            if updated_schema.objects:
                file_object = updated_schema.objects[0]
                table.add_row(
                    file_object.object_name.split("/", 1)[-1],
                    file_object.version_id,
                    file_object.version_tag,
                    file_object.last_modified.isoformat(sep=" "),
                )

        console.print(table, new_line_start=True)

    except Exception as e:
        echo_in_panel(
            f"Unable to update schemas in workspace:\n{e}", 
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1) from e
