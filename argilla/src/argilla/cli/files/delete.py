"""Delete a file from a workspace."""

import os
import sys
from typing import Optional

import typer
from rich.console import Console

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def delete_file(
    remote_path: str = typer.Argument(..., help="Remote path of the file to delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    version_id: Optional[str] = typer.Option(None, "--version-id", "-v", help="Version ID of the file to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
) -> None:
    """Delete a file from a workspace."""
    console = Console()

    try:
        # Get the client
        client = Argilla.from_credentials()

        # Get the workspace
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

        # Confirm deletion if not forced
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete file '{remote_path}' from workspace '{workspace}'?")
            if not confirm:
                panel = get_argilla_themed_panel(
                    "File deletion cancelled.",
                    title="Cancelled",
                    title_align="left",
                    success=True,
                )
                console.print(panel)
                return

        # Delete the file
        workspace_obj.delete_file(remote_path, version_id=version_id)

        # Print a success message
        panel = get_argilla_themed_panel(
            f"File '{remote_path}' deleted from workspace '{workspace}'.",
            title="File deleted successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error deleting file: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
