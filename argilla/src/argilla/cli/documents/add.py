"""Add a document to a workspace."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def add_document(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    file_path: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to the document file", exists=True, readable=True),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL of the document"),
    pmid: Optional[str] = typer.Option(None, "--pmid", "-p", help="PubMed ID of the document"),
    doi: Optional[str] = typer.Option(None, "--doi", "-d", help="DOI of the document"),
) -> None:
    """Add a document to a workspace."""
    console = Console()

    # Check that at least one of file_path, url, pmid, or doi is provided
    if not any([file_path, url, pmid, doi]):
        panel = get_argilla_themed_panel(
            "At least one of --file, --url, --pmid, or --doi must be provided.",
            title="Missing document information",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)

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

        # Add the document with a progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Adding document to workspace '{workspace}'...", total=None)
            
            # Add the document
            document_id = workspace_obj.add_document(
                file_path=str(file_path) if file_path else None,
                url=url,
                pmid=pmid,
                doi=doi,
            )
            
            progress.update(task, completed=True, description=f"Document added to workspace '{workspace}'")

        # Print a success message
        panel = get_argilla_themed_panel(
            f"Document added to workspace '{workspace}' with ID '{document_id}'.",
            title="Document added successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error adding document: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
