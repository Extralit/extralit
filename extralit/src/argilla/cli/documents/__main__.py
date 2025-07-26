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

"""Documents CLI commands."""

from argilla.cli.typer_ext import ArgillaTyper

from argilla.cli.documents.list import list_documents
from argilla.cli.documents.add import add_document
from argilla.cli.documents.import_bib import import_bib
from argilla.cli.documents.delete import delete_document
from argilla.cli.documents.import_history import (
    list_import_histories,
    export_import_history,
    show_import_history,
)

app = ArgillaTyper(help="Manage documents in workspaces", no_args_is_help=True)

# Register all commands
app.command(name="list")(list_documents)
app.command(name="add")(add_document)
app.command(name="import-bibtex")(import_bib)
app.command(name="delete")(delete_document)

# Import history commands
app.command(name="list-imports")(list_import_histories)
app.command(name="export-imports")(export_import_history)
app.command(name="show-imports")(show_import_history)

if __name__ == "__main__":
    app()
