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

import warnings

from argilla.cli.typer_ext import ArgillaTyper

# Import all CLI modules that will be registered with the app
from argilla.cli import (
    datasets,
    documents,
    extraction,
    files,
    info,
    login,
    logout,
    schemas,
    training,
    users,
    whoami,
    workspaces,
)

warnings.simplefilter("ignore", UserWarning)

app = ArgillaTyper(help="Extralit CLI", no_args_is_help=True)


@app.error_handler(PermissionError)
def handler_permission_error(e: PermissionError) -> None:
    import sys
    from argilla.cli.rich import get_argilla_themed_panel
    from rich.console import Console

    panel = get_argilla_themed_panel(
        "Logged in user doesn't have enough permissions to execute this command",
        title="Not enough permissions",
        title_align="left",
        success=False,
    )
    Console().print(panel)
    sys.exit(1)


# Register all command modules (import inside block)
def register_subcommands():
    app.add_typer(datasets.app, name="datasets")
    app.add_typer(documents.app, name="documents")
    app.add_typer(extraction.app, name="extraction")
    app.add_typer(files.app, name="files", hidden=True)
    app.add_typer(info.app, name="info")
    app.add_typer(login.app, name="login")
    app.add_typer(logout.app, name="logout")
    app.add_typer(schemas.app, name="schemas")
    app.add_typer(training.app, name="training")
    app.add_typer(users.app, name="users")
    app.add_typer(whoami.app, name="whoami")
    app.add_typer(workspaces.app, name="workspaces")


register_subcommands()

if __name__ == "__main__":
    app()
