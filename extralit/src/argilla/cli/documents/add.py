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

import json
from pathlib import Path
from typing import Dict, List, Optional

from argilla.workspaces._resource import Workspace
import typer
import bibtexparser
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel
from argilla.documents import Document


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
            elif url:
                document = Document(
                    url=url,
                    reference=reference,
                    workspace_id=workspace_obj.id,
                    pmid=pmid,
                    doi=doi,
                    client=client,
                )
            elif pmid:
                document = Document.from_pmid(
                    pmid=pmid,
                    reference=reference,
                    workspace_id=workspace_obj.id,
                    client=client,
                )
            elif doi:
                document = Document.from_doi(
                    doi=doi,
                    reference=reference,
                    workspace_id=workspace_obj.id,
                    client=client,
                )
            else:
                raise ValueError("At least one of file_path, url, pmid, or doi must be provided")

            # Create the document on the server
            document.create()
            document_id = document.id

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


def _parse_bibtex_file(bibtex_file: Path, console: Console) -> list:
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
                return entries
            except Exception as e:
                progress.update(task, completed=True, description="Failed to parse BibTeX file")
                raise ValueError(f"Error parsing BibTeX file: {str(e)}")


def _match_pdfs_to_entries(entries: List[Dict], pdf_folder: Path, console: Console):
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
                file_entries = [f.strip() for f in file_tag.split(";") if f.strip()]
                for file_entry in file_entries:
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
                    continue
            fallback_matches = [pdf for pdf in all_pdf_files if reference_key in pdf.stem]
            if fallback_matches:
                pdf_files[reference_key] = fallback_matches
                matched_via_fallback += len(fallback_matches)
        progress.update(
            task,
            completed=True,
            description=f"Matched {matched_via_file_tag} PDFs via file tag, {matched_via_fallback} via fallback, total {sum(len(files) for files in pdf_files.values())} PDF files to {len(pdf_files)} BibTeX entries",
        )
    return pdf_files


def _build_documents_payload(entries: List[Dict], pdf_files, workspace_obj: Workspace, collection):
    documents = {}
    for entry in entries:
        reference_key = entry.get("ID")
        if not reference_key:
            continue
        title = entry.get("title", "").strip("{}")
        authors = _parse_authors(entry.get("author", ""))
        year = _parse_year(entry.get("year", ""))
        venue = entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""
        doi = entry.get("doi", "")
        pmid = entry.get("pmid", "")
        document_create = {
            "workspace_id": str(workspace_obj.id),
            "reference": reference_key,
            "doi": doi,
            "pmid": pmid,
        }
        metadata = {}
        if collection:
            metadata["collections"] = [collection]
            metadata["source"] = "bib_import"
        if metadata:
            document_create["metadata"] = metadata
        associated_files = []
        if reference_key in pdf_files:
            for pdf_file in pdf_files[reference_key]:
                associated_files.append({"filename": pdf_file.name, "size": pdf_file.stat().st_size})
        documents[reference_key] = {
            "document_create": document_create,
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "associated_files": associated_files,
        }
    return documents


def _send_import_analysis_request(client: Argilla, workspace_obj: Workspace, documents, console: Console):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing import status...", total=None)
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
    return analysis_result


def _execute_document_bulk_import(client: Argilla, analysis_result: Dict, pdf_folder: Path, console: Console) -> None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing import...", total=None)
        documents_to_import: Dict[str, Dict] = {}
        for ref_key, doc_info in analysis_result.get("documents", {}).items():
            status = doc_info.get("status", "")
            if status in ["add", "update"]:
                documents_to_import[ref_key] = doc_info
        if not documents_to_import:
            progress.update(task, completed=True, description="No documents to import")
            panel = get_argilla_themed_panel(
                "No documents to add or update.",
                title="Import Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return
        bulk_documents: List[Dict] = []
        files_to_upload: List = []
        pdf_file_map = {pdf_path.name: pdf_path for pdf_path in pdf_folder.rglob("*.pdf")}
        for ref_key, doc_info in documents_to_import.items():
            document_create = doc_info.get("document_create", {})
            associated_files = doc_info.get("associated_files", [])
            for file_name in associated_files:
                file_path = pdf_file_map.get(file_name)
                if file_path:
                    bulk_documents.append(
                        {
                            "reference_key": ref_key,
                            "document_create": document_create,
                            "associated_file": file_path.name,
                        }
                    )
                    files_to_upload.append(("files", (file_path.name, open(file_path, "rb"), "application/pdf")))
        if bulk_documents:
            files_to_upload.insert(0, ("documents_metadata", (None, json.dumps({"documents": bulk_documents}))))
            try:
                upload_response = client.api.http_client.post(
                    f"{client.api_url}/api/v1/documents/bulk", files=files_to_upload
                )
                # Always close file objects
                for _, (_, file_obj, _) in files_to_upload[1:]:
                    if hasattr(file_obj, "close"):
                        file_obj.close()
                # Accept any 2xx status code as success
                if not (200 <= upload_response.status_code < 300):
                    progress.update(task, completed=True, description="Import execution failed")
                    error_detail = upload_response.json().get("detail", str(upload_response.text))
                    raise ValueError(f"Error executing import: {error_detail}")
                upload_result = upload_response.json()
                job_ids = upload_result.get("job_ids", {})
                failed_validations = upload_result.get("failed_validations", [])
                progress.update(
                    task,
                    completed=True,
                    description=f"Import submitted: {len(job_ids)} documents queued, {len(failed_validations)} failed validation",
                )
                if job_ids:
                    jobs_table = Table(title="Import Jobs")
                    jobs_table.add_column("Reference Key", style="cyan")
                    jobs_table.add_column("Job ID", style="green")
                    for ref_key, job_id in job_ids.items():
                        jobs_table.add_row(ref_key, job_id)
                    console.print(jobs_table)
                if failed_validations:
                    failed_table = Table(title="Failed Validations", style="red")
                    failed_table.add_column("Error", style="red")
                    for error in failed_validations:
                        failed_table.add_row(error)
                    console.print(failed_table)
                panel = get_argilla_themed_panel(
                    f"Import submitted successfully. {len(job_ids)} documents queued for processing.",
                    title="Import Execution Complete",
                    title_align="left",
                    success=True,
                )
                console.print(panel)
            except Exception as e:
                progress.update(task, completed=True, description="Import execution failed")
                for _, (_, file_obj, _) in files_to_upload[1:]:
                    if hasattr(file_obj, "close"):
                        file_obj.close()
                _handle_cli_exception(console, e)
        else:
            progress.update(task, completed=True, description="No files to upload")
            panel = get_argilla_themed_panel(
                "No files found to upload.",
                title="Import Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)


def _handle_cli_exception(console: Console, e: Exception, debug: bool = False) -> None:
    panel = get_argilla_themed_panel(
        f"Error: {str(e)}",
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
    console = Console()
    try:
        client = Argilla.from_credentials()
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
        if not pdf_folder.exists() or not pdf_folder.is_dir():
            panel = get_argilla_themed_panel(
                f"PDF folder '{pdf_folder}' does not exist or is not a directory.",
                title="Invalid PDF Folder",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)
        entries = _parse_bibtex_file(bibtex_file, console)
        pdf_files = _match_pdfs_to_entries(entries, pdf_folder, console)
        documents = _build_documents_payload(entries, pdf_files, workspace_obj, collection)
        analysis_result = _send_import_analysis_request(client, workspace_obj, documents, console)
        _display_import_analysis_results(console, analysis_result)
        if dry_run:
            panel = get_argilla_themed_panel(
                "Import analysis completed. Use --dry-run=false to execute the import.",
                title="Import Analysis Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        proceed = typer.confirm("Do you want to proceed with the bulk upload?", default=True)
        if not proceed:
            panel = get_argilla_themed_panel(
                "Bulk upload cancelled by user.",
                title="Cancelled",
                title_align="left",
                success=False,
            )
            console.print(panel)
            return

        _execute_document_bulk_import(client, analysis_result, pdf_folder, console)

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
    docs_table.add_column("Errors", style="red")

    for ref_key, doc_info in documents.items():
        status = doc_info.get("status", "")
        status_style = {"add": "green", "update": "yellow", "skip": "blue", "failed": "red"}.get(status, "white")

        title = doc_info.get("title", "")
        if len(title) > 50:
            title = title[:47] + "..."

        authors = ", ".join(doc_info.get("authors", []))
        if len(authors) > 10:
            authors = authors[:12] + "..."

        files = ", ".join(doc_info.get("associated_files", []))
        if len(files) > 10:
            files = files[:10] + "..."

        errors = ", ".join(doc_info.get("validation_errors", []))

        docs_table.add_row(ref_key, title, authors, f"[{status_style}]{status}[/{status_style}]", files, errors)

    console.print(docs_table)
