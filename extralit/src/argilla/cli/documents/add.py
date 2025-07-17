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

"""Add a document or import documents to a workspace."""

from pathlib import Path
from typing import Dict, List, Optional

import typer
import bibtexparser
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def add_document(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    file_path: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Path to the document file", exists=True, readable=True
    ),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL of the document"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Reference of the document"),
    pmid: Optional[str] = typer.Option(None, "--pmid", "-p", help="PubMed ID of the document"),
    doi: Optional[str] = typer.Option(None, "--doi", "-d", help="DOI of the document"),
    debug: bool = typer.Option(False, "--debug", help="Show minimal stack trace for debugging"),
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
                reference=reference,
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
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


def import_bibtex(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    bibtex_file: Path = typer.Option(..., "--bibtex", "-b", help="Path to the BibTeX file", exists=True, readable=True),
    pdf_folder: Path = typer.Argument(
        ..., help="Path to folder containing PDF files", exists=True, readable=True, file_okay=False
    ),
    collection: Optional[str] = typer.Option(
        None, "--collection", "-c", help="Collection tag to add to all imported documents"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Only analyze the import without executing it"),
    debug: bool = typer.Option(False, "--debug", help="Show detailed debug information"),
) -> None:
    """
    Import documents from a BibTeX file and associated PDFs into a workspace.

    This command parses a BibTeX file, matches PDF files from the specified folder,
    and analyzes which documents should be added, updated, or skipped based on
    existing documents in the workspace.
    """
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

        # Parse BibTeX file
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing BibTeX file...", total=None)

            with open(bibtex_file, "r", encoding="utf-8") as bibtex_fp:
                try:
                    bib_database = bibtexparser.load(bibtex_fp)
                    entries = bib_database.entries
                    progress.update(task, completed=True, description=f"Parsed {len(entries)} BibTeX entries")
                except Exception as e:
                    progress.update(task, completed=True, description="Failed to parse BibTeX file")
                    raise ValueError(f"Error parsing BibTeX file: {str(e)}")

        # Match PDF files to BibTeX entries
        pdf_files = {}
        all_pdf_files = list(pdf_folder.rglob("*.pdf"))
        pdf_files_by_name = {pdf.name: pdf for pdf in all_pdf_files}

        matched_via_file_tag = 0
        matched_via_fallback = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Matching PDF files to BibTeX entries...", total=None)

            for entry in entries:
                reference_key = entry.get("ID")
                if not reference_key:
                    continue

                file_tag = entry.get("file")
                matched_pdfs = []
                if file_tag:
                    # Split by semicolon, get only the file name before the first colon
                    file_entries = [f.strip() for f in file_tag.split(";") if f.strip()]
                    for file_entry in file_entries:
                        # Format: <desc>:<relative_path>:<mime_type> or just <relative_path>
                        parts = file_entry.split(":")
                        if len(parts) >= 2:
                            file_name = Path(parts[1]).name
                        else:
                            file_name = Path(parts[0]).name
                        pdf = pdf_files_by_name.get(file_name)
                        if pdf:
                            matched_pdfs.append(pdf)
                    if matched_pdfs:
                        pdf_files[reference_key] = matched_pdfs
                        matched_via_file_tag += len(matched_pdfs)
                        continue  # skip fallback if matched

                # Fallback: match by reference key in file name
                fallback_matches = [pdf for pdf in all_pdf_files if reference_key in pdf.stem]
                if fallback_matches:
                    pdf_files[reference_key] = fallback_matches
                    matched_via_fallback += len(fallback_matches)

            progress.update(
                task,
                completed=True,
                description=f"Matched {matched_via_file_tag} PDFs via file tag, {matched_via_fallback} via fallback, total {sum(len(files) for files in pdf_files.values())} PDF files to {len(pdf_files)} BibTeX entries",
            )

        # Prepare import analysis request
        documents = {}
        for entry in entries:
            reference_key = entry.get("ID")
            if not reference_key:
                continue

            # Extract metadata from BibTeX entry
            title = entry.get("title", "").strip("{}")
            authors = _parse_authors(entry.get("author", ""))
            year = _parse_year(entry.get("year", ""))
            venue = entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""
            doi = entry.get("doi", "")
            pmid = entry.get("pmid", "")

            # Create document metadata
            document_create = {
                "workspace_id": str(workspace_obj.id),
                "reference": reference_key,
                "doi": doi,
                "pmid": pmid,
            }

            # Add collection tag if provided
            metadata = {}
            if collection:
                metadata["collections"] = [collection]
                metadata["source"] = "bib_import"

            if metadata:
                document_create["metadata"] = metadata

            # Add associated files
            associated_files = []
            if reference_key in pdf_files:
                for pdf_file in pdf_files[reference_key]:
                    associated_files.append({"filename": pdf_file.name, "size": pdf_file.stat().st_size})

            # Add document to request
            documents[reference_key] = {
                "document_create": document_create,
                "title": title,
                "authors": authors,
                "year": year,
                "venue": venue,
                "associated_files": associated_files,
            }

        # Send import analysis request
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing import status...", total=None)

            # Send request to server using the public API client
            analysis_response = client.api.http_client.post(
                f"{client.api_url}/api/v1/imports/analyze",
                json={"workspace_id": str(workspace_obj.id), "documents": documents},
            )

            if analysis_response.status_code != 200:
                progress.update(task, completed=True, description="Import analysis failed")
                error_detail = analysis_response.json().get("detail", str(analysis_response.text))
                raise ValueError(f"Error analyzing import: {error_detail}")

            analysis_result = analysis_response.json()
            progress.update(task, completed=True, description="Import analysis completed")

        # Display analysis results
        _display_import_analysis_results(console, analysis_result)

        # If dry_run flag is set, stop here
        if dry_run:
            panel = get_argilla_themed_panel(
                "Import analysis completed. Use --dry-run=false to execute the import.",
                title="Import Analysis Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # TODO: Implement actual import execution in a future task
        panel = get_argilla_themed_panel(
            "Import execution is not yet implemented. This will be added in a future update.",
            title="Import Execution Not Available",
            title_align="left",
            success=False,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error importing documents: {str(e)}",
            title="Error",
            title_align="left",
            exception=e,
            debug=debug,
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)


def _parse_authors(author_string: str) -> List[str]:
    """Parse author string from BibTeX entry into a list of author names."""
    if not author_string:
        return []

    # Remove braces and split by 'and'
    cleaned = author_string.replace("{", "").replace("}", "")
    authors = [author.strip() for author in cleaned.split(" and ")]
    return authors


def _parse_year(year_string: str) -> Optional[int]:
    """Parse year string from BibTeX entry into an integer."""
    if not year_string:
        return None

    try:
        return int(year_string)
    except ValueError:
        return None


def _display_import_analysis_results(console: Console, analysis_result: Dict) -> None:
    """Display import analysis results in a formatted table."""
    documents = analysis_result.get("documents", {})
    summary = analysis_result.get("summary", {})

    # Create summary table
    summary_table = Table(title="Import Analysis Summary")
    summary_table.add_column("Total", style="cyan")
    summary_table.add_column("Add", style="green")
    summary_table.add_column("Update", style="yellow")
    summary_table.add_column("Skip", style="blue")
    summary_table.add_column("Failed", style="red")

    summary_table.add_row(
        str(summary.get("total_documents", 0)),
        str(summary.get("add_count", 0)),
        str(summary.get("update_count", 0)),
        str(summary.get("skip_count", 0)),
        str(summary.get("failed_count", 0)),
    )

    console.print(summary_table)

    # Create documents table
    docs_table = Table(title="Document Import Status")
    docs_table.add_column("Reference Key", style="cyan")
    docs_table.add_column("Title", style="cyan")
    docs_table.add_column("Authors", style="cyan")
    docs_table.add_column("Status", style="cyan")
    docs_table.add_column("Files", style="cyan")

    for ref_key, doc_info in documents.items():
        status = doc_info.get("status", "")
        status_style = {"add": "green", "update": "yellow", "skip": "blue", "failed": "red"}.get(status, "white")

        title = doc_info.get("title", "")
        if len(title) > 50:
            title = title[:47] + "..."

        authors = ", ".join(doc_info.get("authors", []))
        if len(authors) > 50:
            authors = authors[:47] + "..."

        files = ", ".join(doc_info.get("associated_files", []))
        if len(files) > 30:
            files = files[:27] + "..."

        docs_table.add_row(ref_key, title, authors, f"[{status_style}]{status}[/{status_style}]", files)

    console.print(docs_table)
