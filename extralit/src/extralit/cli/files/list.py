import typer

from extralit.cli.rich import get_themed_panel, print_rich_table
from extralit.client import Extralit


def list_files(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    path: str = typer.Option("", "--path", "-p", help="Path prefix to filter files"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="List files recursively"),
) -> None:
    from rich.console import Console

    console = Console()

    try:
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

        files = workspace_obj.list_files(path, recursive=recursive)

        if not files.objects:
            panel = get_themed_panel(
                f"No files found in workspace '{workspace}' at path '{path}'.",
                title="No files found",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        print_rich_table(files.objects)

        panel = get_themed_panel(
            f"Found {len(files.objects)} files in workspace '{workspace}'.",
            title="Files listed successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_themed_panel(
            f"Error listing files: {e!s}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
