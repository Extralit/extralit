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

from argilla.cli.typer_ext import ArgillaTyper

# Import all files CLI commands
from argilla.cli.files.list import list_files
from argilla.cli.files.upload import upload_file
from argilla.cli.files.download import download_file
from argilla.cli.files.delete import delete_file

app = ArgillaTyper(help="Manage files in workspaces", no_args_is_help=True)

# Register all commands
app.command(name="list")(list_files)
app.command(name="upload")(upload_file)
app.command(name="download")(download_file)
app.command(name="delete")(delete_file)

if __name__ == "__main__":
    app()
