"""
Document import CLI with polars-based BibTeX processing and dataframe support.

This module implements the CLI interface for the papers library importer feature,
using polars for proper BibTeX parsing and dataframe handling:

- Parses BibTeX files into a polars DataFrame with proper field handling
- Matches PDF files to references and stores file paths in 'files' column
- Uses DataFrame for import_history.data storage
- Simplified and refactored code for better reuse and maintainability

The CLI workflow:
1. Parse BibTeX file into a polars DataFrame with proper field parsing
2. Match PDF files to references and add to 'files' column
3. Send analysis request with file metadata
4. Display preview with multi-file information
5. Execute bulk upload with job tracking
6. Store import history with DataFrame data
"""

import json
import mimetypes
from pathlib import Path
from typing import Optional

import lazy_loader as lazy
import polars as pl
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit
from extralit.workspaces._resource import Workspace

bibtexparser = lazy.load("bibtexparser")


def _clean_bibtex_field(value: str) -> str:
    """Clean BibTeX field by removing braces and extra whitespace."""
    if not value:
        return ""
    return value.replace("{", "").replace("}", "").strip()


def _parse_bibtex_to_dataframe(bibtex_file: Path, console: Console) -> pl.DataFrame:
    """Parse BibTeX file into a polars DataFrame with proper field handling."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing BibTeX file to DataFrame...", total=None)

        try:
            library = bibtexparser.parse_file(str(bibtex_file), encoding="utf-8")
            entries = [
                {"ID": e.key, "ENTRYTYPE": e.entry_type, **{k: f.value for k, f in e.fields_dict.items()}}
                for e in library.entries
            ]

            if not entries:
                progress.update(task, completed=True, description="No entries found in BibTeX file")
                return pl.DataFrame()

            # Entries have different fields; a field an entry lacks becomes null.
            df = pl.from_dicts(entries, infer_schema_length=None).select(pl.all().cast(pl.String))
            df = (
                df.rename({"ID": "reference"})
                if "ID" in df.columns
                else df.with_columns(reference=pl.lit(None, pl.String))
            )
            fields = [c for c in df.columns if c != "reference"]
            df = df.with_columns(
                pl.col("reference").fill_null(""),
                *(pl.col(c).str.replace_all("[{}]", "").str.strip_chars().alias(c) for c in fields if c != "files"),
                files=pl.lit(""),
            ).select("reference", *(c for c in fields if c != "files"), "files")
            progress.update(task, completed=True, description=f"Parsed {len(df)} entries to DataFrame")
            return df

        except Exception as e:
            progress.update(task, completed=True, description="Failed to parse BibTeX file")
            raise ValueError(f"Error parsing BibTeX file: {e!s}")


def _match_pdfs_to_dataframe(df: pl.DataFrame, pdf_folder: Path, console: Console) -> pl.DataFrame:
    """
    Match PDF files to BibTeX DataFrame entries and populate 'files' column.

    Matching strategies:
    1. File tag parsing: Extract filenames from BibTeX 'file' field (Zotero/Mendeley format)
    2. Fallback matching: Match PDFs containing the reference key in filename
    3. Store matched file paths in 'files' column as semicolon-separated string

    Returns:
        Updated DataFrame with 'files' column populated
    """
    if df.is_empty():
        return df

    all_pdf_files = list(pdf_folder.rglob("*.pdf"))
    pdf_files_by_name = pl.DataFrame(
        {"file_name": [pdf.name for pdf in all_pdf_files], "pdf": [str(pdf) for pdf in all_pdf_files]},
        schema={"file_name": pl.String, "pdf": pl.String},
    ).unique("file_name", keep="last", maintain_order=True)
    pdf_stems = pl.DataFrame(
        {"stem": [pdf.stem for pdf in all_pdf_files], "pdf": [str(pdf) for pdf in all_pdf_files]},
        schema={"stem": pl.String, "pdf": pl.String},
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Matching PDF files to DataFrame entries...", total=None)

        refs = df.with_row_index("_idx").filter(pl.col("reference") != "")
        file_tag = pl.col("file") if "file" in df.columns else pl.lit("")

        # Strategy 1: the BibTeX 'file' field, "Description:path/to/file.pdf:application/pdf" or "path/to/file.pdf"
        entries = (
            refs.select("_idx", entry=file_tag.fill_null("").str.split(";"))
            .explode("entry")
            .with_columns(pl.col("entry").str.strip_chars())
            .filter(pl.col("entry") != "")
            .with_columns(parts=pl.col("entry").str.split(":"))
            .with_columns(
                path=pl.when(pl.col("parts").list.len() >= 2)
                .then(pl.col("parts").list.get(1))
                .otherwise(pl.col("parts").list.get(0))
            )
            .with_columns(file_name=pl.col("path").str.replace(r"^.*/", ""))
        )
        via_tag = entries.join(pdf_files_by_name, on="file_name", how="inner", maintain_order="left").select(
            "_idx", "pdf"
        )

        # Strategy 2: fallback for references without a file-tag match: PDFs whose stem contains the key
        fallback_refs = refs.join(via_tag.select("_idx").unique(), on="_idx", how="anti")
        via_fallback = (
            fallback_refs.select("_idx", "reference")
            .join(pdf_stems, how="cross")
            .filter(pl.col("stem").str.contains(pl.col("reference"), literal=True))
            .select("_idx", "pdf")
        )

        matched = (
            pl.concat([via_tag, via_fallback])
            .group_by("_idx", maintain_order=True)
            .agg(files=pl.col("pdf").str.join("; "))
        )
        df_matched = (
            df.with_row_index("_idx")
            .join(matched, on="_idx", how="left", suffix="_matched")
            .with_columns(files=pl.col("files_matched").fill_null(""))
            .drop("_idx", "files_matched")
        )

        matched_via_file_tag = via_tag.height
        matched_via_fallback = via_fallback.height
        total_files = matched_via_file_tag + matched_via_fallback
        refs_with_files = df_matched.filter(pl.col("files") != "").height

        progress.update(
            task,
            completed=True,
            description=f"Matched {matched_via_file_tag} files via file tag, {matched_via_fallback} via fallback. Total: {total_files} files across {refs_with_files} references",
        )

    return df_matched


def _dataframe_to_import_history_format(df: pl.DataFrame) -> dict:
    """Convert DataFrame to import history data format."""
    if df.is_empty():
        return {"schema": {"fields": []}, "data": []}

    def field_type(dtype: pl.DataType) -> str:
        if dtype.is_integer():
            return "integer"
        if dtype.is_float():
            return "float"
        if dtype == pl.Boolean:
            return "boolean"
        return "string"

    schema_fields = [{"name": name, "type": field_type(dtype)} for name, dtype in df.schema.items()]
    schema = {"fields": schema_fields, "primaryKey": ["reference"]}

    # Missing values become None for 'year' and "" elsewhere.
    floats = [pl.col(name).fill_nan(None) for name, dtype in df.schema.items() if dtype.is_float()]
    data_rows = [
        {k: ("" if v is None and k != "year" else v) for k, v in row.items()}
        for row in df.with_columns(floats).to_dicts()
    ]
    return {"schema": schema, "data": data_rows}


def _file_paths(df: pl.DataFrame) -> pl.DataFrame:
    """One row per (row index, path) from the semicolon-separated 'files' column."""
    if "files" not in df.columns:
        return pl.DataFrame(schema={"_idx": pl.UInt32, "path": pl.String})
    return (
        df.with_row_index("_idx")
        .select("_idx", path=pl.col("files").fill_null("").str.split(";"))
        .explode("path")
        .with_columns(pl.col("path").str.strip_chars())
        .filter(pl.col("path").is_not_null() & (pl.col("path") != ""))
    )


def _build_documents_payload(df: pl.DataFrame, workspace_obj: Workspace, collection: Optional[str]) -> dict:
    """Build documents payload for import analysis request from DataFrame."""
    metadata = {"collections": [collection], "source": "bib_import"} if collection else {}
    column = {c: pl.col(c) if c in df.columns else pl.lit("") for c in ("doi", "pmid")}
    rows = (
        df.with_row_index("_idx")
        .filter(pl.col("reference").is_not_null() & (pl.col("reference") != ""))
        .select("_idx", "reference", doi=column["doi"], pmid=column["pmid"])
    )

    existing = [p for p in _file_paths(df).iter_rows(named=True) if Path(p["path"]).exists()]
    files = pl.DataFrame(
        {
            "_idx": [p["_idx"] for p in existing],
            "file": [{"filename": Path(p["path"]).name, "size": Path(p["path"]).stat().st_size} for p in existing],
        },
        schema={"_idx": pl.UInt32, "file": pl.Struct({"filename": pl.String, "size": pl.Int64})},
    )
    grouped = files.group_by("_idx", maintain_order=True).agg(associated_files=pl.col("file"))
    rows = rows.join(grouped, on="_idx", how="left", maintain_order="left")

    return {
        row["reference"]: {
            "document_create": {
                "workspace_id": str(workspace_obj.id),
                "reference": row["reference"],
                "doi": row["doi"],
                "pmid": row["pmid"],
                **({"metadata": metadata} if metadata else {}),
            },
            "associated_files": row["associated_files"] or [],
        }
        for row in rows.iter_rows(named=True)
    }


def _send_import_analysis_request(client: Extralit, workspace_obj: Workspace, documents, console: Console):
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
    client: Extralit, analysis_result: dict, df: pl.DataFrame, df_data: dict, bibtex_file: Path, console: Console
) -> None:
    """Execute bulk document import with multi-file support per reference."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing import...", total=None)

        # Filter documents to import (add/update status only)
        documents_to_import: dict[str, dict] = {}
        for ref_key, doc_info in analysis_result.get("documents", {}).items():
            status = doc_info.get("status", "")
            if status in ["add", "update"]:
                documents_to_import[ref_key] = doc_info

        if not documents_to_import:
            progress.update(task, completed=True, description="No documents to import")
            panel = get_themed_panel(
                "No documents to add or update.",
                title="Import Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Build bulk upload payload - one entry per file (not per reference)
        bulk_documents: list[dict] = []
        files_to_upload: list = []

        # Create file mapping from DataFrame
        file_map = {Path(path).name: Path(path) for path in _file_paths(df)["path"].to_list() if Path(path).exists()}

        for ref_key, doc_info in documents_to_import.items():
            document_create = doc_info.get("document_create", {})
            associated_files = doc_info.get("associated_files", [])

            # Collect all valid file names for this reference
            valid_file_names = []
            for file_info in associated_files:
                file_name = file_info if isinstance(file_info, str) else file_info.get("filename")
                file_path = file_map.get(file_name)
                if file_path:
                    valid_file_names.append(file_path.name)
                    # Determine content type based on file extension (default to application/pdf)
                    if file_path.suffix.lower() == ".pdf":
                        content_type = "application/pdf"
                    else:
                        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                    files_to_upload.append(("files", (file_path.name, open(file_path, "rb"), content_type)))

            # Create one BulkDocumentInfo entry per reference with multiple files
            if valid_file_names:
                bulk_documents.append(
                    {
                        "reference": ref_key,
                        "document_create": document_create,
                        "associated_files": valid_file_names,
                    }
                )

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
                        # Count files for this reference from the bulk_documents entry
                        ref_doc = next((doc for doc in bulk_documents if doc["reference"] == ref_key), None)
                        file_count = len(ref_doc.get("associated_files", [])) if ref_doc else 0
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
                    _store_import_history(client, analysis_result, df_data, bibtex_file, console)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not store import history: {e!s}[/yellow]")

                # Calculate total files across all references
                total_files = sum(len(doc.get("associated_files", [])) for doc in bulk_documents)

                panel = get_themed_panel(
                    f"Import submitted successfully. {len(job_ids)} references queued for processing with {total_files} total files.",
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
            panel = get_themed_panel(
                "No files found to upload.",
                title="Import Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)


def _store_import_history(
    client: Extralit, analysis_result: dict, df_data: dict, bibtex_file: Path, console: Console
) -> None:
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

            # Use the provided DataFrame data
            dataframe_data = df_data

            # Validate dataframe data structure
            if not dataframe_data or not isinstance(dataframe_data, dict):
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
        console.print(f"[yellow]Warning: Error storing import history: {e!s}[/yellow]")
        raise e


def _handle_cli_exception(console: Console, e: Exception, debug: bool = False) -> None:
    """Handle CLI exceptions with consistent error formatting."""
    panel = get_themed_panel(
        f"Error: {e!s}",
        title="Error",
        title_align="left",
        exception=e,
        debug=debug,
        success=False,
    )
    console.print(panel)
    raise typer.Exit(code=1)


def _validate_workspace_and_folder(client: Extralit, workspace: str, pdf_folder: Path, console: Console) -> Workspace:
    """Validate workspace exists and PDF folder is accessible."""
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

    if not pdf_folder.exists() or not pdf_folder.is_dir():
        panel = get_themed_panel(
            f"PDF folder '{pdf_folder}' does not exist or is not a directory.",
            title="Invalid PDF Folder",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)

    return workspace_obj


def _get_user_confirmation_for_import(console: Console, analysis_result: dict) -> bool:
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
        client = Extralit.from_credentials()
        workspace_obj = _validate_workspace_and_folder(client, workspace, pdf_folder, console)

        # Phase 1: Parse BibTeX to DataFrame and match PDF files
        df = _parse_bibtex_to_dataframe(bibtex_file, console)
        df_with_files = _match_pdfs_to_dataframe(df, pdf_folder, console)

        # Phase 2: Build analysis request payload from DataFrame
        documents = _build_documents_payload(df_with_files, workspace_obj, collection)

        # Phase 3: Send analysis request to backend (mirrors frontend API call)
        analysis_result = _send_import_analysis_request(client, workspace_obj, documents, console)

        # Phase 4: Display preview results (mirrors frontend preview component)
        _display_import_analysis_results(console, analysis_result)

        # Phase 5: Handle dry-run mode
        if dry_run:
            panel = get_themed_panel(
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
            panel = get_themed_panel(
                "Bulk upload cancelled by user.",
                title="Cancelled",
                title_align="left",
                success=False,
            )
            console.print(panel)
            return

        # Phase 7: Execute bulk import with DataFrame
        df_data = _dataframe_to_import_history_format(df_with_files)
        _execute_document_bulk_import(client, analysis_result, df_with_files, df_data, bibtex_file, console)

    except Exception as e:
        _handle_cli_exception(console, e, debug)


def _display_import_analysis_results(console: Console, analysis_result: dict) -> None:
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
