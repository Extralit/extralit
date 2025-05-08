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

from typing import TYPE_CHECKING, List
import typer

if TYPE_CHECKING:
    from argilla.client.core import Argilla


def echo_in_panel(text, title=None, title_align="center", success=True):
    """Echoes a message in a rich panel with Argilla theme."""
    from argilla.cli.rich import get_argilla_themed_panel
    from rich.console import Console

    panel = get_argilla_themed_panel(
        renderable=text,
        title=title,
        title_align=title_align,
        success=success,
    )
    Console().print(panel)


def init_callback() -> "Argilla":
    """Initialize Argilla client if user is logged in, otherwise exit."""
    from argilla.client.login import ArgillaCredentials

    if not ArgillaCredentials.exists():
        echo_in_panel(
            "You are not logged in. Please run 'extralit login' to login to the Extralit server.",
            title="Not logged in",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1)

    try:
        from argilla.client import Argilla

        client = Argilla.from_credentials()
        return client
    except Exception as e:
        echo_in_panel(
            f"The Extralit Server you are logged in is not available or not responding. Please make sure it's running and try again.\n{e}",
            title="Server not available",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1)


def autocomplete_workspace(incomplete: str) -> List[str]:
    """Autocomplete workspaces based on the partial input."""
    try:
        client = init_callback()
        workspaces = client.workspaces

        # Filter workspaces that start with the incomplete string
        return [workspace.name for workspace in workspaces if workspace.name.startswith(incomplete)]
    except Exception:
        # If there's any error during autocompletion, just return empty list
        return []


def deprecated_database_cmd_callback(ctx: typer.Context) -> None:
    """Display warning for deprecated database commands."""
    echo_in_panel(
        f"Instead you should run `extralit server database the {typer.style(ctx.invoked_subcommand, bold=True)}`",
        title="Deprecated command",
        title_align="left",
        success=False,
    )
