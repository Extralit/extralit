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

import typer

from argilla.client import Argilla
from argilla.cli.rich import get_argilla_themed_panel, print_rich_table


def list_files(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    path: str = typer.Option("", "--path", "-p", help="Path prefix to filter files"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="List files recursively"),
    include_version: bool = typer.Option(False, "--versions/--no-versions", help="Include version information"),
) -> None:
    from rich.console import Console

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

        files = workspace_obj.list_files(path, recursive=recursive, include_version=include_version)

        files.objects = [obj for obj in files.objects if obj.etag is not None]

        if not files.objects:
            panel = get_argilla_themed_panel(
                f"No files found in workspace '{workspace}' with path prefix '{path}'.",
                title="No files found",
                title_align="left",
                success=True,
            )
            console.print(panel)
            return

        print_rich_table(files.objects)

        panel = get_argilla_themed_panel(
            f"Found {len(files.objects)} files in workspace '{workspace}'.",
            title="Files listed successfully",
            title_align="left",
            success=True,
        )
        console.print(panel)

    except Exception as e:
        panel = get_argilla_themed_panel(
            f"Error listing files: {str(e)}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
