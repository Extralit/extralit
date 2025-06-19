"""Delete a document from a workspace."""

import sys
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def delete_document(
    document_id: UUID = typer.Argument(..., help="ID of the document to delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
) -> None:
    """Delete a document from a workspace."""
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

        # Check if the document exists
        documents = workspace_obj.get_documents()
        document = next((doc for doc in documents if doc.id == document_id), None)
        if not document:
            panel = get_argilla_themed_panel(
                f"Document with ID '{document_id}' not found in workspace '{workspace}'.",
                title="Document not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Confirm deletion if not forced
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete document '{document_id}' from workspace '{workspace}'?")
            if not confirm:
                panel = get_argilla_themed_panel(
                    "Document deletion cancelled.",
                    title="Cancelled",
                    title_align="left",
                    success=True,
                )
                console.print(panel)
                return

        # Delete the document
        # Note: This is a placeholder as the API doesn't have a delete_document method yet
        # We'll need to implement this in the API first
        # workspace_obj.delete_document(document_id)
        
        # For now, just show a message
        panel = get_argilla_themed_panel(
            f"Document deletion is not yet implemented in the API. Document '{document_id}' was not deleted.",
            title="Not implemented",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error deleting document: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
