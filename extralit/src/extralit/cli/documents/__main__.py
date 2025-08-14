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

from extralit.cli.documents.add import add_document
from extralit.cli.documents.delete import delete_document
from extralit.cli.documents.import_bib import import_bib
from extralit.cli.documents.import_history import list_import_histories
from extralit.cli.documents.list import list_documents
from extralit.cli.typer_ext import ExtralitTyper

app = ExtralitTyper(help="Manage documents in workspaces", no_args_is_help=True)

# Register all commands
app.command(name="list")(list_documents)
app.command(name="add")(add_document)
app.command(name="import")(import_bib)
app.command(name="delete")(delete_document)

# Import history commands - new structure
app.command(name="history")(list_import_histories)

if __name__ == "__main__":
    app()
