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

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel


def upload_file(
    file_path: Path = typer.Argument(..., help="Path to the file to upload", exists=True, readable=True),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    remote_path: Optional[str] = typer.Option(
        None, "--remote-path", "-r", help="Remote path to store the file (default: same as local filename)"
    ),
    overwrite: bool = typer.Option(False, "--overwrite", "-o", help="Overwrite existing file"),
) -> None:
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

        # Determine the remote path
        if remote_path is None:
            remote_path = file_path.name

        # Check if the file already exists
        if not overwrite:
            try:
                files = workspace_obj.list_files(remote_path)
                for file_obj in files.objects:
                    if file_obj.object_name == remote_path:
                        panel = get_argilla_themed_panel(
                            f"File '{remote_path}' already exists in workspace '{workspace}'. Use --overwrite to overwrite.",
                            title="File already exists",
                            title_align="left",
                            success=False,
                        )
                        console.print(panel)
                        raise typer.Exit(code=1)
            except Exception:
                # If we can't list files, assume the file doesn't exist
                pass

        # Upload the file with a progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Uploading {file_path.name} to {workspace}/{remote_path}...", total=None)

            # Upload the file
            workspace_obj.put_file(remote_path, file_path)

            progress.update(task, completed=True, description=f"Uploaded {file_path.name} to {workspace}/{remote_path}")

        # Print a success message
        panel = get_argilla_themed_panel(
            f"File '{file_path.name}' uploaded to workspace '{workspace}' as '{remote_path}'.",
            title="File uploaded successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error uploading file: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
