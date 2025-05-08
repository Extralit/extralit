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

"""List documents in a workspace."""

import typer
from rich.console import Console

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel, print_rich_table


def list_documents(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
) -> None:
    """List documents in a workspace."""
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

        # List documents
        documents = workspace_obj.get_documents()

        if not documents:
            panel = get_argilla_themed_panel(
                f"No documents found in workspace '{workspace}'.",
                title="No documents found",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Use print_rich_table to display the documents
        print_rich_table(documents, title=f"Documents in workspace '{workspace}'")

        # Print a success message
        panel = get_argilla_themed_panel(
            f"Found {len(documents)} documents in workspace '{workspace}'.",
            title="Documents listed successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error listing documents: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
