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

app = typer.Typer(invoke_without_command=True)


def remove_credentials():
    """Remove stored credentials."""
    from argilla.client.login import ArgillaCredentials

    try:
        ArgillaCredentials.remove()
    except FileNotFoundError:
        # If credentials don't exist, that's fine
        pass

    return True


@app.callback(help="Logout from an Extralit Server")
def logout(force: bool = typer.Option(False, help="Force the logout even if the server cannot be reached")) -> None:
    """Logout from an Extralit Server by removing stored credentials."""
    from argilla.cli.callback import init_callback
    from argilla.cli.rich import get_argilla_themed_panel
    from rich.console import Console
    from argilla.client.login import ArgillaCredentials

    if not force:
        try:
            init_callback()
        except Exception:
            panel = get_argilla_themed_panel(
                "Could not connect to the Extralit Server. Use --force to logout anyway.",
                title="Connection error",
                title_align="left",
                success=False,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

    # Remove the credentials
    remove_credentials()

    # Show success message
    panel = get_argilla_themed_panel(
        "Logged out successfully from Extralit server!",
        title="Logout",
        title_align="left",
    )
    Console().print(panel)


if __name__ == "__main__":
    app()