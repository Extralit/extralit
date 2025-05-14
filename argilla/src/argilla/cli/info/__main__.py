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

from argilla.cli.callback import init_callback
from argilla.cli.rich import get_argilla_themed_panel
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(invoke_without_command=True)


@app.callback(help="Displays information about the Extralit client and server")
def info() -> None:
    """Display information about the Extralit client and server."""
    try:
        from argilla import __version__ as version
    except ImportError:
        version = "2.0.0"

    client = init_callback()

    panel = get_argilla_themed_panel(
        Markdown(f"Connected to {client.api_url}\n" f"- **Client version:** {version}\n"),
        title="Extralit Info",
        title_align="left",
    )

    Console().print(panel)


if __name__ == "__main__":
    app()
