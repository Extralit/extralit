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
    """
    Match PDF files to BibTeX entries with support for multiple files per reference.

    Matching strategies:
    1. File tag parsing: Extract filenames from BibTeX 'file' field (Zotero/Mendeley format)
    2. Fallback matching: Match PDFs containing the reference key in filename
    3. Multiple files per reference are supported and tracked separately

    Returns:
        Dict mapping reference keys to lists of matched PDF file paths
    """
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
        task = progress.add_task("Matching PDF files to BibTeX entries (multi-file support)...", total=None)

        for entry in entries:
            reference = entry.get("ID")
            if not reference:
                continue

            matched_pdfs = []

            # Strategy 1: Parse 'file' field from BibTeX entry (supports multiple files)
            file_tag = entry.get("file")
            if file_tag:
                file_entries = [f.strip() for f in file_tag.split(";") if f.strip()]
                for file_entry in file_entries:
                    # Handle different file field formats:
                    # "Description:path/to/file.pdf:application/pdf"
                    # "path/to/file.pdf"
                    parts = file_entry.split(":")
                    if len(parts) >= 2:
                        file_name = Path(parts[1]).name
                    else:
                        file_name = Path(parts[0]).name

                    pdf = pdf_files_by_name.get(file_name)
                    if pdf:
                        matched_pdfs.append(pdf)

                if matched_pdfs:
                    pdf_files[reference] = matched_pdfs
                    matched_via_file_tag += len(matched_pdfs)
                    continue

            # Strategy 2: Fallback - find PDFs containing reference key in filename
            fallback_matches = [pdf for pdf in all_pdf_files if reference in pdf.stem]
            if fallback_matches:
                pdf_files[reference] = fallback_matches
                matched_via_fallback += len(fallback_matches)

        total_files = sum(len(files) for files in pdf_files.values())
        total_refs_with_files = len(pdf_files)

        progress.update(
            task,
            completed=True,
            description=f"Matched {matched_via_file_tag} files via file tag, {matched_via_fallback} via fallback. Total: {total_files} files across {total_refs_with_files} references",
        )

    return pdf_files


def _build_documents_payload(entries: List[Dict], pdf_files, workspace_obj: Workspace, collection):
    """Build documents payload for import analysis request with multi-file support."""
    documents = {}
    for entry in entries:
        reference = entry.get("ID")
        if not reference:
            continue
        title = entry.get("title", "").strip("{}")
        authors = _parse_authors(entry.get("author", ""))
        year = _parse_year(entry.get("year", ""))
        venue = entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""
        doi = entry.get("doi", "")
        pmid = entry.get("pmid", "")

        # Build document_create payload
        document_create = {
            "workspace_id": str(workspace_obj.id),
            "reference": reference,
            "doi": doi,
            "pmid": pmid,
        }

        # Add metadata if collection is specified
        metadata = {}
        if collection:
            metadata["collections"] = [collection]
            metadata["source"] = "bib_import"
        if metadata:
            document_create["metadata"] = metadata

        # Build associated_files list with FileInfo structure
        associated_files = []
        if reference in pdf_files:
            for pdf_file in pdf_files[reference]:
                associated_files.append({"filename": pdf_file.name, "size": pdf_file.stat().st_size})

        # Build DocumentMetadata structure for analysis request
        documents[reference] = {
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


def _execute_document_bulk_import(
    client: Argilla, analysis_result: Dict, pdf_folder: Path, bibtex_file: Path, console: Console
) -> None:
    """Execute bulk document import with multi-file support per reference."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing import...", total=None)

        # Filter documents to import (add/update status only)
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

        # Build bulk upload payload - one entry per file (not per reference)
        bulk_documents: List[Dict] = []
        files_to_upload: List = []
        pdf_file_map = {pdf_path.name: pdf_path for pdf_path in pdf_folder.rglob("*.pdf")}

        for ref_key, doc_info in documents_to_import.items():
            document_create = doc_info.get("document_create", {})
            associated_files = doc_info.get("associated_files", [])

            # Create one BulkDocumentInfo entry per file
            for file_name in associated_files:
                file_path = pdf_file_map.get(file_name)
                if file_path:
                    # Each file gets its own document entry with the same reference
                    bulk_documents.append(
                        {
                            "reference": ref_key,
                            "document_create": document_create,
                            "associated_file": file_path.name,
                        }
                    )
                    files_to_upload.append(("files", (file_path.name, open(file_path, "rb"), "application/pdf")))

        if bulk_documents:
            # Add metadata as first form field
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
                    description=f"Import submitted: {len(job_ids)} references queued, {len(failed_validations)} failed validation",
                )

                # Display job tracking table (one job per reference)
                if job_ids:
                    jobs_table = Table(title="Import Jobs (One Job Per Reference)")
                    jobs_table.add_column("Reference Key", style="cyan")
                    jobs_table.add_column("Job ID", style="green")
                    jobs_table.add_column("Files Count", style="yellow")

                    for ref_key, job_id in job_ids.items():
                        # Count files for this reference
                        file_count = len([doc for doc in bulk_documents if doc["reference"] == ref_key])
                        jobs_table.add_row(ref_key, job_id, str(file_count))

                    console.print(jobs_table)

                # Display validation failures
                if failed_validations:
                    failed_table = Table(title="Failed Validations", style="red")
                    failed_table.add_column("Error", style="red")
                    for error in failed_validations:
                        failed_table.add_row(error)
                    console.print(failed_table)

                # Store import history after successful bulk upload (non-blocking)
                try:
                    _store_import_history(client, analysis_result, bibtex_file, console)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not store import history: {str(e)}[/yellow]")

                panel = get_argilla_themed_panel(
                    f"Import submitted successfully. {len(job_ids)} references queued for processing with {len(bulk_documents)} total files.",
                    title="Import Execution Complete",
                    title_align="left",
                    success=True,
                )
                console.print(panel)

            except Exception as e:
                progress.update(task, completed=True, description="Import execution failed")
                # Ensure all file objects are closed on error
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


def _store_import_history(client: Argilla, analysis_result: Dict, bibtex_file: Path, console: Console) -> None:
    """
    Store import history record with dataframe data and metadata.

    This function calls the POST /imports/history endpoint to store:
    - data: Tabular dataframe representation of the BibTeX import
    - metadata: Import status and associated files for each reference

    This provides an audit trail of all imports for analysis and querying.
    """
    try:
        # Check if a live display is already active on the console
        live_display_active = getattr(console, "_live", None) is not None

        def do_store(progress=None, task=None):
            # Extract workspace_id from analysis result
            documents = analysis_result.get("documents", {})
            if not documents:
                if progress and task is not None:
                    progress.update(task, completed=True, description="No documents to store in history")
                else:
                    console.print("[yellow]No documents to store in history[/yellow]")
                return

            # Get workspace_id from first document
            first_doc = next(iter(documents.values()))
            workspace_id = first_doc.get("document_create", {}).get("workspace_id")
            if not workspace_id:
                if progress and task is not None:
                    progress.update(task, completed=True, description="Could not determine workspace ID")
                else:
                    console.print("[yellow]Could not determine workspace ID[/yellow]")
                return

            # Build dataframe data from analysis result
            dataframe_data = analysis_result.get("data", {})

            # Validate dataframe data structure
            if not dataframe_data or not isinstance(dataframe_data, dict):
                if progress and task is not None:
                    progress.update(task, completed=True, description="Invalid dataframe data structure")
                console.print("[yellow]Warning: Could not store import history - invalid dataframe data[/yellow]")
                return

            # Build metadata with import status and associated files for each reference
            metadata = {}
            for ref_key, doc_info in documents.items():
                metadata[ref_key] = {
                    "status": doc_info.get("status", "unknown"),
                    "associated_files": doc_info.get("associated_files", []),
                }

            # Create import history payload
            import_history_payload = {
                "workspace_id": workspace_id,
                "filename": bibtex_file.name,
                "data": dataframe_data,
                "metadata": metadata,
            }

            # Send request to store import history
            history_response = client.api.http_client.post(
                f"{client.api_url}/api/v1/imports/history", json=import_history_payload
            )

            if history_response.status_code == 201:
                history_result = history_response.json()
                msg = f"Import history stored (ID: {history_result.get('id', 'unknown')})"
                if progress and task is not None:
                    progress.update(task, completed=True, description=msg)
                else:
                    console.print(f"[green]{msg}[/green]")
            else:
                msg = f"Failed to store import history: {history_response.text}"
                if progress and task is not None:
                    progress.update(task, completed=True, description="Failed to store import history")
                console.print(f"[yellow]Warning: {msg}[/yellow]")

        if live_display_active:
            # Just print status updates, don't use Progress
            console.print("[cyan]Storing import history...[/cyan]")
            do_store()
        else:
            from rich.progress import Progress, SpinnerColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Storing import history...", total=None)
                do_store(progress, task)

    except Exception as e:
        console.print(f"[yellow]Warning: Error storing import history: {str(e)}[/yellow]")
        raise e


def _handle_cli_exception(console: Console, e: Exception, debug: bool = False) -> None:
    """Handle CLI exceptions with consistent error formatting."""
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


def _validate_workspace_and_folder(client: Argilla, workspace: str, pdf_folder: Path, console: Console) -> Workspace:
    """Validate workspace exists and PDF folder is accessible."""
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

    return workspace_obj


def _get_user_confirmation_for_import(console: Console, analysis_result: Dict) -> bool:
    """Get user confirmation before proceeding with bulk import."""
    summary = analysis_result.get("summary", {})
    total_files = sum(len(doc.get("associated_files", [])) for doc in analysis_result.get("documents", {}).values())

    console.print("\n[bold]Import Summary:[/bold]")
    console.print(f"  • {summary.get('add_count', 0)} references to add")
    console.print(f"  • {summary.get('update_count', 0)} references to update")
    console.print(f"  • {summary.get('skip_count', 0)} references to skip")
    console.print(f"  • {total_files} total files to process")

    if summary.get("failed_count", 0) > 0:
        console.print(f"  • [red]{summary.get('failed_count', 0)} references failed validation[/red]")

    return typer.confirm("\nDo you want to proceed with the bulk upload?", default=True)


def import_bib(
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
    Import documents from a BibTeX file and match them with PDFs in a folder.

    This command follows the same workflow as the frontend UI:
    1. Parse BibTeX file and match PDF files to references
    2. Send analysis request to determine add/update/skip status
    3. Display preview of import actions
    4. Execute bulk import with job tracking (one job per reference)
    5. Store import history for audit trail and analysis

    Each reference may have multiple associated PDF files, which are processed
    together in a single job to maintain consistency. The import history stores
    both the tabular dataframe data and metadata about import status and files.
    """
    console = Console()
    try:
        # Initialize client and validate inputs
        client = Argilla.from_credentials()
        workspace_obj = _validate_workspace_and_folder(client, workspace, pdf_folder, console)

        # Phase 1: Parse BibTeX and match files (mirrors frontend processing)
        entries = _parse_bibtex_file(bibtex_file, console)
        pdf_files = _match_pdfs_to_entries(entries, pdf_folder, console)

        # Phase 2: Build analysis request payload (mirrors frontend analysis request)
        documents = _build_documents_payload(entries, pdf_files, workspace_obj, collection)

        # Phase 3: Send analysis request to backend (mirrors frontend API call)
        analysis_result = _send_import_analysis_request(client, workspace_obj, documents, console)

        # Phase 4: Display preview results (mirrors frontend preview component)
        _display_import_analysis_results(console, analysis_result)

        # Phase 5: Handle dry-run mode
        if dry_run:
            panel = get_argilla_themed_panel(
                "Import analysis completed. Use --dry-run=false to execute the import.",
                title="Import Analysis Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Phase 6: Get user confirmation (mirrors frontend confirmation dialog)
        proceed = _get_user_confirmation_for_import(console, analysis_result)
        if not proceed:
            panel = get_argilla_themed_panel(
                "Bulk upload cancelled by user.",
                title="Cancelled",
                title_align="left",
                success=False,
            )
            console.print(panel)
            return

        # Phase 7: Execute bulk import (mirrors frontend bulk upload execution)
        _execute_document_bulk_import(client, analysis_result, pdf_folder, bibtex_file, console)

    except Exception as e:
        _handle_cli_exception(console, e, debug)


def _display_import_analysis_results(console: Console, analysis_result: Dict) -> None:
    """Display import analysis results in a formatted table with multi-file support."""
    documents = analysis_result.get("documents", {})
    summary = analysis_result.get("summary", {})

    # Create summary table
    summary_table = Table(title="Import Analysis Summary")
    summary_table.add_column("Total References", style="cyan")
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

    # Create documents table with multi-file information
    docs_table = Table(title="Document Import Status (Multi-File Support)")
    docs_table.add_column("Reference Key", style="cyan")
    docs_table.add_column("Title", style="cyan")
    docs_table.add_column("Authors", style="cyan")
    docs_table.add_column("Status", style="cyan")
    docs_table.add_column("Files Count", style="magenta")
    docs_table.add_column("Files", style="cyan")
    docs_table.add_column("Errors", style="red")

    # Calculate total files across all references
    total_files = 0
    for ref_key, doc_info in documents.items():
        status = doc_info.get("status", "")
        status_style = {"add": "green", "update": "yellow", "skip": "blue", "failed": "red"}.get(status, "white")

        title = doc_info.get("title", "")
        if len(title) > 50:
            title = title[:47] + "..."

        authors = ", ".join(doc_info.get("authors", []))
        if len(authors) > 30:
            authors = authors[:27] + "..."

        associated_files = doc_info.get("associated_files", [])
        files_count = len(associated_files)
        total_files += files_count

        # Display file names, truncate if too long
        files_display = ", ".join(associated_files)
        if len(files_display) > 40:
            files_display = files_display[:37] + "..."

        errors = ", ".join(doc_info.get("validation_errors", []))

        docs_table.add_row(
            ref_key,
            title,
            authors,
            f"[{status_style}]{status}[/{status_style}]",
            str(files_count),
            files_display,
            errors,
        )

    console.print(docs_table)

    # Display total files summary
    files_summary_table = Table(title="Files Summary")
    files_summary_table.add_column("Total Files", style="cyan")
    files_summary_table.add_column("References with Files", style="green")
    files_summary_table.add_column("References without Files", style="red")

    refs_with_files = len([doc for doc in documents.values() if doc.get("associated_files")])
    refs_without_files = len(documents) - refs_with_files

    files_summary_table.add_row(str(total_files), str(refs_with_files), str(refs_without_files))

    console.print(files_summary_table)
