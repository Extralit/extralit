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

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit


def delete_document(
    reference: Optional[str] = typer.Option(None, help="Reference of the document to delete"),
    document_id: Optional[UUID] = typer.Option(None, "--id", help="ID of the document to delete"),
    pmid: Optional[str] = typer.Option(None, help="PMID of the document to delete"),
    doi: Optional[str] = typer.Option(None, help="DOI of the document to delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    all: bool = typer.Option(False, "--all", "-a", help="Delete all documents in the workspace"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
) -> None:
    """Delete a document or all documents from a workspace.

    You can specify a document to delete by any of:
    - --reference (string)
    - --document-id (UUID)
    - --pmid (PubMed ID)
    - --doi (DOI)
    """
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

        documents_collection = workspace_obj.documents

        if all:
            # Get all documents in the workspace (using efficient call without metadata)
            all_documents = documents_collection()
            if not all_documents:
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
                    f"Are you sure you want to delete ALL ({len(all_documents)}) documents from workspace '{workspace}'?"
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
            for doc in all_documents:
                try:
                    doc.delete()
                    deleted.append(doc.file_name or str(doc.id))
                except Exception as e:
                    failed.append((doc.file_name or str(doc.id), str(e)))

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

        # Single document deletion - check that at least one identifier is provided
        if not any([reference, document_id, pmid, doi]):
            panel = get_themed_panel(
                "You must specify a document to delete using one of: reference, --document-id, --pmid, or --doi",
                title="Missing document identifier",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Use the new Documents API to get documents by any of the provided criteria
        # Only pass the non-None values to avoid API errors
        kwargs = {}
        if document_id is not None:
            kwargs["id"] = document_id
        if reference is not None:
            kwargs["reference"] = reference
        if pmid is not None:
            kwargs["pmid"] = pmid
        if doi is not None:
            kwargs["doi"] = doi

        # Get matching documents (returns a list)
        matching_documents = documents_collection(**kwargs)

        if not matching_documents:
            # Build a descriptive error message based on what was provided
            criteria = []
            if reference:
                criteria.append(f"reference '{reference}'")
            if document_id:
                criteria.append(f"ID '{document_id}'")
            if pmid:
                criteria.append(f"PMID '{pmid}'")
            if doi:
                criteria.append(f"DOI '{doi}'")

            criteria_text = " or ".join(criteria)
            panel = get_themed_panel(
                f"No documents found with {criteria_text} in workspace '{workspace}'.",
                title="Documents not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Handle multiple documents found
        if len(matching_documents) == 1:
            document = matching_documents[0]
            # Get a display name for the document
            document_name = document.file_name or document.reference or str(document.id)

            if not force:
                confirm = typer.confirm(
                    f"Are you sure you want to delete document '{document_name}' from workspace '{workspace}'?"
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
                f"Document '{document_name}' deleted successfully from workspace '{workspace}'.",
                title="Document deleted",
                title_align="left",
                success=True,
            )
            console.print(panel)
        else:
            # Multiple documents found - ask user to confirm bulk deletion
            if not force:
                confirm = typer.confirm(
                    f"Found {len(matching_documents)} documents matching the criteria. "
                    f"Are you sure you want to delete ALL of them from workspace '{workspace}'?"
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

            # Delete all matching documents
            deleted = []
            failed = []
            for doc in matching_documents:
                try:
                    doc.delete()
                    deleted.append(doc.file_name or doc.reference or str(doc.id))
                except Exception as e:
                    failed.append((doc.file_name or doc.reference or str(doc.id), str(e)))

            msg = f"Deleted {len(deleted)} document(s) from workspace '{workspace}'."
            if deleted:
                msg += "\n" + "\n".join(f"  - {name}" for name in deleted)
            if failed:
                msg += f"\nFailed to delete {len(failed)} document(s):"
                msg += "\n" + "\n".join(f"  - {name}: {err}" for name, err in failed)

            panel = get_themed_panel(
                msg,
                title="Documents deleted",
                title_align="left",
                success=(len(failed) == 0),
            )
            console.print(panel)
            if failed:
                raise typer.Exit(code=1)

    except Exception as e:
        panel = get_themed_panel(
            f"Error deleting document: {e!s}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
