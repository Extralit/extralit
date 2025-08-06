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

"""Delete a document or all documents from a workspace."""

from typing import Optional
from uuid import UUID

import typer
from rich.console import Console

from extralit.client import Extralit
from extralit.cli.rich import get_themed_panel


def delete_document(
    reference: Optional[str] = typer.Argument(None, help="Reference of the document to delete"),
    document_id: Optional[UUID] = typer.Option(None, help="ID of the document to delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    all: bool = typer.Option(False, "--all", "-a", help="Delete all documents in the workspace"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
) -> None:
    """Delete a document or all documents from a workspace."""
    console = Console()

    try:
        client = Extralit.from_credentials()

        # Get the workspace
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

        documents = workspace_obj.documents

        if all:
            if not documents:
                panel = get_themed_panel(
                    f"No documents found in workspace '{workspace}'.",
                    title="No documents",
                    title_align="left",
                    success=False,
                )
                console.print(panel)
                return

            if not force:
                confirm = typer.confirm(
                    f"Are you sure you want to delete ALL ({len(documents)}) documents from workspace '{workspace}'?"
                )
                if not confirm:
                    panel = get_themed_panel(
                        "Bulk document deletion cancelled.",
                        title="Cancelled",
                        title_align="left",
                        success=True,
                    )
                    console.print(panel)
                    return

            deleted = []
            failed = []
            for doc in documents:
                try:
                    doc.delete()
                    deleted.append(doc.file_name)
                except Exception as e:
                    failed.append((doc.file_name, str(e)))

            msg = f"Deleted {len(deleted)} document(s) from workspace '{workspace}'."
            if deleted:
                msg += "\n" + "\n".join(f"  - {name}" for name in deleted)
            if failed:
                msg += f"\nFailed to delete {len(failed)} document(s):"
                msg += "\n" + "\n".join(f"  - {name}: {err}" for name, err in failed)

            panel = get_themed_panel(
                msg,
                title="Bulk document deletion",
                title_align="left",
                success=(len(failed) == 0),
            )
            console.print(panel)
            if failed:
                raise typer.Exit(code=1)
            return

        # Single document deletion
        document = None
        if reference:
            document = next((doc for doc in documents if doc.reference == reference), None)
        elif document_id:
            document = next((doc for doc in documents if doc.id == document_id), None)

        if not document:
            panel = get_themed_panel(
                f"Document with {'reference ' + reference if reference else 'ID ' + str(document_id)} not found in workspace '{workspace}'.",
                title="Document not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        if not force:
            confirm = typer.confirm(
                f"Are you sure you want to delete document '{document.file_name}' from workspace '{workspace}'?"
            )
            if not confirm:
                panel = get_themed_panel(
                    "Document deletion cancelled.",
                    title="Cancelled",
                    title_align="left",
                    success=True,
                )
                console.print(panel)
                return

        document.delete()

        panel = get_themed_panel(
            f"Document '{document.file_name}' deleted successfully from workspace '{workspace}'.",
            title="Document deleted",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_themed_panel(
            f"Error deleting document: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
