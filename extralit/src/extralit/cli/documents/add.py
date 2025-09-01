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

"""
Document import CLI with multi-file support per reference.

This module implements the CLI interface for the papers library importer feature,
supporting the new multi-file schema where:

- Each reference may have multiple associated files (DocumentImportAnalysis.associated_files)
- Jobs are created per reference (not per file) to process multiple files together
- BulkDocumentInfo supports one file per entry, but multiple entries per reference
- DocumentsBulkResponse returns job_ids indexed by reference key
- Import analysis tracks files at both reference and individual file levels

The CLI mirrors the frontend UI workflow:
1. Parse BibTeX and match PDF files (frontend processing)
2. Send analysis request with file metadata (ImportAnalysisRequest)
3. Display preview with multi-file information (ImportAnalysisResponse)
4. Execute bulk upload with job tracking (DocumentsBulkResponse)
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit
from extralit.documents import Document


def add_document(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    file_path: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Path to the document file", exists=True, readable=True
    ),
    reference: str = typer.Option(..., "--reference", "-r", help="Reference of the document"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL of the document"),
    pmid: Optional[str] = typer.Option(None, "--pmid", "-p", help="PubMed ID of the document"),
    doi: Optional[str] = typer.Option(None, "--doi", "-d", help="DOI of the document"),
    debug: bool = typer.Option(False, "--debug", help="Show minimal stack trace for debugging"),
) -> None:
    """Add a document to a workspace."""
    console = Console()

    # Check that at least one of file_path, url, pmid, or doi is provided
    if not any([file_path, url, pmid, doi]):
        panel = get_themed_panel(
            "At least one of --file, --url, --pmid, or --doi must be provided.",
            title="Missing document information",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)

    try:
        # Get the client
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

        # Add the document with a progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Adding document to workspace '{workspace}'...", total=None)

            # Create the document using the new resource API
            if file_path:
                document = Document.from_file(
                    file_path_or_url=file_path,
                    reference=reference,
                    workspace_id=workspace_obj.id,
                    pmid=pmid,
                    doi=doi,
                    client=client,
                )
            else:
                document = Document(
                    url=url,
                    reference=reference,
                    workspace_id=workspace_obj.id,
                    pmid=pmid,
                    doi=doi,
                    client=client,
                )

            # Create the document on the server
            document.create()
            document_id = document.id

            progress.update(task, completed=True, description=f"Document added to workspace '{workspace}'")

        # Print a success message
        panel = get_themed_panel(
            f"Document added to workspace '{workspace}' with ID '{document_id}'.",
            title="Document added successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_themed_panel(
            f"Error adding document: {e!s}",
            title="Error",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
