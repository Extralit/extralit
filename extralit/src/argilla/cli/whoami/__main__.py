# Copyright 2024-present, Argilla, Inc.
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
from rich.markdown import Markdown

app = typer.Typer(invoke_without_command=True)


def get_current_user():
    """Get information about the current user.

    Returns:
        User: The current user.

    Raises:
        ValueError: If not logged in.
    """
    from argilla.cli.callback import init_callback

    # Initialize client and get current user
    client = init_callback()

    # Return the current user
    return client.me


@app.callback(help="Show information about the current user")
def whoami() -> None:
    """Display information about the current user."""
    from argilla.cli.rich import get_argilla_themed_panel
    from rich.console import Console

    try:
        # Get current user (this will initialize the client)
        user = get_current_user()

        panel = get_argilla_themed_panel(
            Markdown(
                f"- **Username**: {user.username}\n"
                f"- **Role**: {user.role}\n"
                f"- **First name**: {user.first_name}\n"
                f"- **Last name**: {user.last_name}\n"
            ),
            title="Current User",
            title_align="left",
        )
        Console().print(panel)
    except ValueError as e:
        panel = get_argilla_themed_panel(
            str(e),
            title="Not logged in",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()