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
Workflow management CLI commands for PDF processing workflows.

This module provides CLI commands to manage PDF processing workflows:
- Start workflows for documents
- Check workflow status
- Restart failed workflows
- List workflows with filtering

The CLI communicates with the server through FastAPI endpoints using the HTTP client,
following the same pattern as the existing import_bib.py command.
"""

import json
import time
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit

# Create typer app with Rich library components for formatted output
app = typer.Typer(help="Manage PDF processing workflows")

# Set up HTTP client communication pattern following import_bib.py example
console = Console()


def _handle_http_error(response, operation: str) -> None:
    """Handle HTTP errors with user-friendly messages."""
    try:
        error_detail = response.json().get("detail", str(response.text))
    except Exception:
        error_detail = str(response.text)

    panel = get_themed_panel(
        f"Error {operation}: {error_detail}",
        title="API Error",
        title_align="left",
        success=False,
    )
    console.print(panel)
    raise typer.Exit(1)


@app.command()
def start(
    document_id: str = typer.Option(..., "--document-id", help="Document UUID to process"),
    workspace_name: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Document reference for tracking"),
    force: bool = typer.Option(False, "--force", "-f", help="Force restart if workflow already exists"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Start PDF processing workflow for a document."""
    try:
        client = Extralit.from_credentials()
    except Exception as e:
        panel = get_themed_panel(
            f"Authentication failed: {e}",
            title="Authentication Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)

    try:
        # Validate document_id is a valid UUID
        try:
            UUID(document_id)
        except ValueError:
            panel = get_themed_panel(
                f"Invalid document ID format: {document_id}",
                title="Invalid Input",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Starting workflow...", total=None)

            # Use client.api.http_client.post() to call /workflows/start endpoint
            response = client.api.http_client.post(
                f"{client.api_url}/api/v1/workflows/start",
                json={
                    "document_id": document_id,
                    "workspace_name": workspace_name,
                    "reference": reference or f"doc_{document_id[:8]}",
                    "force": force,
                },
            )

            progress.update(task, completed=True, description="Workflow start request completed")

        # Add validation and error handling for HTTP responses
        if response.status_code != 200:
            _handle_http_error(response, "starting workflow")

        result = response.json()

        # Add confirmation prompts and detailed output formatting
        panel = get_themed_panel(
            f"✓ Started workflow {result['workflow_id']}",
            title="Workflow Started",
            title_align="left",
            success=True,
        )
        console.print(panel)

        if verbose:
            console.print(f"[dim]Document ID:[/dim] {result['document_id']}")
            console.print(f"[dim]Reference:[/dim] {result.get('reference', 'N/A')}")
            console.print(f"[dim]Group ID:[/dim] {result['group_id']}")
            console.print(f"[dim]Status:[/dim] {result['status']}")

        console.print(f"\n[bold]Track progress with:[/bold] extralit workflows status --document-id {document_id}")

    except typer.Exit:
        raise
    except Exception as e:
        # Handle errors gracefully with user-friendly messages
        panel = get_themed_panel(
            f"Unexpected error starting workflow: {e}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)


@app.command()
def status(
    document_id: Optional[str] = typer.Option(None, "--document-id", help="Document UUID to check"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Document reference to check"),
    workspace_name: Optional[str] = typer.Option(None, "--workspace", "-w", help="Filter by workspace name"),
    watch: bool = typer.Option(False, "--watch", help="Watch status updates in real-time"),
    json_output: bool = typer.Option(False, "--json", help="Output status as JSON"),
) -> None:
    """Check workflow status for documents."""
    try:
        client = Extralit.from_credentials()
    except Exception as e:
        panel = get_themed_panel(
            f"Authentication failed: {e}",
            title="Authentication Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)

    try:
        if not document_id and not reference:
            panel = get_themed_panel(
                "Must specify either --document-id or --reference",
                title="Missing Required Parameter",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(1)

        # Validate document_id if provided
        if document_id:
            try:
                UUID(document_id)
            except ValueError:
                panel = get_themed_panel(
                    f"Invalid document ID format: {document_id}",
                    title="Invalid Input",
                    title_align="left",
                    success=False,
                )
                console.print(panel)
                raise typer.Exit(1)

        def get_workflow_status():
            """Get workflow status from API."""
            # Use client.api.http_client.get() to call /workflows/status endpoint
            params = {}
            if document_id:
                params["document_id"] = document_id
            if reference:
                params["reference"] = reference
            if workspace_name:
                params["workspace_name"] = workspace_name

            response = client.api.http_client.get(
                f"{client.api_url}/api/v1/workflows/status",
                params=params,
            )

            if response.status_code != 200:
                _handle_http_error(response, "checking workflow status")

            return response.json()

        if watch:
            # Add real-time status watching with --watch flag and periodic updates
            try:
                while True:
                    console.clear()
                    workflows = get_workflow_status()

                    if not workflows:
                        console.print("[yellow]No workflows found[/yellow]")
                    else:
                        # Support JSON output format for scripting and automation
                        if json_output:
                            console.print(json.dumps(workflows, indent=2, default=str))
                        else:
                            # Implement _display_workflow_status_table() helper function using Rich Table
                            _display_workflow_status_table(workflows)

                    console.print("\n[dim]Press Ctrl+C to stop watching[/dim]")
                    time.sleep(5)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped watching[/yellow]")
        else:
            workflows = get_workflow_status()

            if not workflows:
                console.print("[yellow]No workflows found[/yellow]")
                return

            # Support JSON output format for scripting and automation
            if json_output:
                console.print(json.dumps(workflows, indent=2, default=str))
                return

            # Implement _display_workflow_status_table() helper function using Rich Table
            _display_workflow_status_table(workflows)

    except typer.Exit:
        raise
    except Exception as e:
        panel = get_themed_panel(
            f"Unexpected error checking workflow status: {e}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)


def _display_workflow_status_table(workflows: list) -> None:
    """
    Implement _display_workflow_status_table() helper function using Rich Table.

    Calculate and display progress percentages and duration information.
    """
    table = Table(title="PDF Processing Workflows")
    table.add_column("Document ID", style="cyan", no_wrap=True)
    table.add_column("Reference", style="magenta")
    table.add_column("Workspace", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Progress", style="yellow")
    table.add_column("Started", style="dim")
    table.add_column("Duration", style="dim")

    for workflow in workflows:
        # Calculate progress percentage and duration information
        total_jobs = workflow.get("total_jobs", 0)
        completed_jobs = workflow.get("completed_jobs", 0)
        progress_pct = int(completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        progress = f"{completed_jobs}/{total_jobs} ({progress_pct}%)"

        # Format status with color
        status = workflow["status"]
        if status == "completed":
            status = f"[green]{status}[/green]"
        elif status == "failed":
            status = f"[red]{status}[/red]"
        elif status == "running":
            status = f"[yellow]{status}[/yellow]"

        # Calculate duration
        from datetime import datetime

        created_at = workflow.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    duration = str(datetime.utcnow() - created_dt.replace(tzinfo=None)).split(".")[0]
                except Exception:
                    duration = "Unknown"
            else:
                duration = "Unknown"
        else:
            duration = "Unknown"

        # Format started time
        started_str = "N/A"
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    started_str = created_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                started_str = "N/A"

        table.add_row(
            workflow["document_id"][:8] + "..." if len(workflow["document_id"]) > 8 else workflow["document_id"],
            workflow.get("reference", "N/A"),
            workflow.get("workspace_name", "N/A"),
            status,
            progress,
            started_str,
            duration,
        )

    console.print(table)


@app.command()
def restart(
    document_id: Optional[str] = typer.Option(None, "--document-id", help="Document UUID to restart"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Document reference to restart"),
    workspace_name: Optional[str] = typer.Option(None, "--workspace", "-w", help="Filter by workspace name"),
    failed_only: bool = typer.Option(True, "--failed-only/--all", help="Only restart failed jobs"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Restart failed workflow jobs for documents."""
    try:
        client = Extralit.from_credentials()
    except Exception as e:
        panel = get_themed_panel(
            f"Authentication failed: {e}",
            title="Authentication Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)

    try:
        if not document_id and not reference:
            panel = get_themed_panel(
                "Must specify either --document-id or --reference",
                title="Missing Required Parameter",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(1)

        # Validate document_id if provided
        if document_id:
            try:
                UUID(document_id)
            except ValueError:
                panel = get_themed_panel(
                    f"Invalid document ID format: {document_id}",
                    title="Invalid Input",
                    title_align="left",
                    success=False,
                )
                console.print(panel)
                raise typer.Exit(1)

        # First get workflows to restart
        params = {}
        if document_id:
            params["document_id"] = document_id
        if reference:
            params["reference"] = reference
        if workspace_name:
            params["workspace_name"] = workspace_name

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Getting workflow status...", total=None)

            status_response = client.api.http_client.get(
                f"{client.api_url}/api/v1/workflows/status",
                params=params,
            )

            progress.update(task, completed=True, description="Workflow status retrieved")

        if status_response.status_code != 200:
            _handle_http_error(status_response, "getting workflow status")

        workflows = status_response.json()
        failed_workflows = [w for w in workflows if w["status"] == "failed"]

        if not failed_workflows:
            panel = get_themed_panel(
                "No failed workflows found",
                title="No Workflows to Restart",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Add confirmation prompts before restarting workflows
        if not confirm:
            workflow_count = len(failed_workflows)
            restart_type = "failed jobs only" if failed_only else "all jobs"

            console.print(f"\n[bold]Found {workflow_count} failed workflow(s) to restart ({restart_type}):[/bold]")
            for workflow in failed_workflows:
                console.print(f"  • Document {workflow['document_id'][:8]}... - {workflow.get('reference', 'N/A')}")

            if not typer.confirm(f"\nRestart {workflow_count} workflow(s)?"):
                console.print("Cancelled")
                return

        # Restart workflows
        restarted_count = 0
        failed_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Restarting workflows...", total=len(failed_workflows))

            for _i, workflow in enumerate(failed_workflows):
                try:
                    # Use client.api.http_client.post() to call /workflows/restart endpoint
                    restart_response = client.api.http_client.post(
                        f"{client.api_url}/api/v1/workflows/restart",
                        json={
                            "document_id": workflow["document_id"],
                            "failed_only": failed_only,
                        },
                    )

                    if restart_response.status_code == 200:
                        result = restart_response.json()
                        restarted_jobs = result.get("restarted_jobs", [])
                        console.print(
                            f"[green]✓ Restarted workflow for document {workflow['document_id'][:8]}... "
                            f"({len(restarted_jobs)} jobs)[/green]"
                        )
                        restarted_count += 1
                    else:
                        try:
                            error_detail = restart_response.json().get("detail", "Unknown error")
                        except Exception:
                            error_detail = str(restart_response.text)
                        console.print(
                            f"[red]✗ Failed to restart workflow for document {workflow['document_id'][:8]}...: "
                            f"{error_detail}[/red]"
                        )
                        failed_count += 1

                except Exception as e:
                    console.print(
                        f"[red]✗ Failed to restart workflow for document {workflow['document_id'][:8]}...: {e}[/red]"
                    )
                    failed_count += 1

                progress.update(task, advance=1)

        # Display progress and results of restart operations
        if restarted_count > 0:
            panel = get_themed_panel(
                f"Successfully restarted {restarted_count} of {len(failed_workflows)} workflows",
                title="Restart Complete",
                title_align="left",
                success=True,
            )
            console.print(panel)

        if failed_count > 0:
            panel = get_themed_panel(
                f"Failed to restart {failed_count} workflows",
                title="Restart Errors",
                title_align="left",
                success=False,
            )
            console.print(panel)

    except typer.Exit:
        raise
    except Exception as e:
        panel = get_themed_panel(
            f"Unexpected error restarting workflows: {e}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)


@app.command()
def list(
    workspace_name: Optional[str] = typer.Option(None, "--workspace", "-w", help="Filter by workspace name"),
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status (running, completed, failed)"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of workflows to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List recent workflows."""
    try:
        client = Extralit.from_credentials()
    except Exception as e:
        panel = get_themed_panel(
            f"Authentication failed: {e}",
            title="Authentication Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)

    try:
        # Don't show progress for JSON output
        if not json_output:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching workflows...", total=None)

                # Use client.api.http_client.get() to call /workflows/ endpoint
                params = {"limit": limit}
                if workspace_name:
                    params["workspace_name"] = workspace_name
                if status_filter:
                    params["status_filter"] = status_filter

                response = client.api.http_client.get(
                    f"{client.api_url}/api/v1/workflows/",
                    params=params,
                )
                progress.update(task, completed=True, description="Workflows retrieved")
        else:
            # Use client.api.http_client.get() to call /workflows/ endpoint
            params = {"limit": limit}
            if workspace_name:
                params["workspace_name"] = workspace_name
            if status_filter:
                params["status_filter"] = status_filter

            response = client.api.http_client.get(
                f"{client.api_url}/api/v1/workflows/",
                params=params,
            )

        if response.status_code != 200:
            _handle_http_error(response, "listing workflows")

        workflows = response.json()

        if not workflows:
            panel = get_themed_panel(
                "No workflows found",
                title="No Workflows",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        # Support both table and JSON output formats
        if json_output:
            console.print(json.dumps(workflows, indent=2, default=str))
            return

        # Display comprehensive workflow information in formatted table
        _display_workflow_list_table(workflows)

    except typer.Exit:
        raise
    except Exception as e:
        panel = get_themed_panel(
            f"Unexpected error listing workflows: {e}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(1)


def _display_workflow_list_table(workflows: list) -> None:
    """
    Display comprehensive workflow information in formatted table.

    Add filtering capabilities by workspace and status.
    Implement pagination with configurable limits.
    """
    table = Table(title=f"Recent Workflows ({len(workflows)} shown)")
    table.add_column("Document ID", style="cyan", no_wrap=True)
    table.add_column("Reference", style="magenta")
    table.add_column("Workspace", style="blue")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Progress", style="yellow")
    table.add_column("Jobs", style="dim")
    table.add_column("Created", style="dim")
    table.add_column("Duration", style="dim")

    for workflow in workflows:
        # Calculate progress and job statistics
        total_jobs = workflow.get("total_jobs", 0)
        completed_jobs = workflow.get("completed_jobs", 0)
        failed_jobs = workflow.get("failed_jobs", 0)
        running_jobs = workflow.get("running_jobs", 0)

        progress_pct = int(completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        progress = f"{progress_pct}%"

        # Format status with color
        status = workflow["status"]
        if status == "completed":
            status = f"[green]{status}[/green]"
        elif status == "failed":
            status = f"[red]{status}[/red]"
        elif status == "running":
            status = f"[yellow]{status}[/yellow]"
        elif status == "pending":
            status = f"[blue]{status}[/blue]"

        # Format job statistics
        jobs_info = f"{completed_jobs}✓"
        if failed_jobs > 0:
            jobs_info += f" {failed_jobs}✗"
        if running_jobs > 0:
            jobs_info += f" {running_jobs}⟳"
        jobs_info += f"/{total_jobs}"

        # Calculate duration
        from datetime import datetime

        created_at = workflow.get("created_at")
        duration = "Unknown"
        created_str = "N/A"

        if created_at:
            try:
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    duration = str(datetime.utcnow() - created_dt.replace(tzinfo=None)).split(".")[0]
                    created_str = created_dt.strftime("%m-%d %H:%M")
            except Exception:
                pass

        table.add_row(
            workflow["document_id"][:8] + "..." if len(workflow["document_id"]) > 8 else workflow["document_id"],
            workflow.get("reference", "N/A")[:20] + ("..." if len(workflow.get("reference", "")) > 20 else ""),
            workflow.get("workspace_name", "N/A")[:15]
            + ("..." if len(workflow.get("workspace_name", "")) > 15 else ""),
            workflow.get("workflow_type", "unknown")[:10],
            status,
            progress,
            jobs_info,
            created_str,
            duration,
        )

    console.print(table)

    # Add summary information
    total_workflows = len(workflows)
    completed_count = len([w for w in workflows if w["status"] == "completed"])
    failed_count = len([w for w in workflows if w["status"] == "failed"])
    running_count = len([w for w in workflows if w["status"] == "running"])

    console.print(
        f"\n[dim]Summary: {completed_count} completed, {running_count} running, {failed_count} failed out of {total_workflows} total[/dim]"
    )


if __name__ == "__main__":
    app()
