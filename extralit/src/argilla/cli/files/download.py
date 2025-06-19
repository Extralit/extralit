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

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def download_file(
    remote_path: str = typer.Argument(..., help="Remote path of the file to download"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Local path to save the file (default: same as remote filename)"
    ),
    version_id: Optional[str] = typer.Option(None, "--version-id", "-v", help="Version ID of the file to download"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing file"),
) -> None:
    """Download a file from a workspace."""
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

        # Determine the output path
        if output_path is None:
            output_path = Path(os.path.basename(remote_path))

        # Check if the output file already exists
        if output_path.exists() and not overwrite:
            panel = get_argilla_themed_panel(
                f"Output file '{output_path}' already exists. Use --overwrite to overwrite.",
                title="File already exists",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Download the file with a progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Downloading {remote_path} from {workspace}...", total=None)

            # Download the file
            file_response = workspace_obj.get_file(remote_path, version_id=version_id)

            # Save the file
            with open(output_path, "wb") as f:
                f.write(file_response.content)

            progress.update(task, completed=True, description=f"Downloaded {remote_path} from {workspace}")

        # Print a success message
        panel = get_argilla_themed_panel(
            f"File '{remote_path}' downloaded from workspace '{workspace}' to '{output_path}'.",
            title="File downloaded successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error downloading file: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
