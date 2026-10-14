"""List documents in a workspace."""

from typing import Optional

import typer
from rich.console import Console

from extralit.cli.rich import get_themed_panel, print_rich_table
from extralit.client import Extralit


def list_documents(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Reference filter"),
) -> None:
    """List documents in a workspace."""
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

        # Get all documents in the workspace (using efficient call without metadata)
        documents = workspace_obj.documents(reference=reference)

        if not documents:
            panel = get_themed_panel(
                f"No documents found in workspace '{workspace}'.",
                title="No documents found",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Use type: ignore since Document is a Resource but type system doesn't recognize the inheritance
        print_rich_table(documents, title=f"Documents in workspace '{workspace}'")  # type: ignore

        panel = get_themed_panel(
            f"Found {len(documents)} documents in workspace '{workspace}'.",
            title="Documents listed successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_themed_panel(
            f"Error listing documents: {e!s}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
