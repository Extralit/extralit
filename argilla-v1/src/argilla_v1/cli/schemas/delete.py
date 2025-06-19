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

import os
from typing import Optional
import typer

from argilla_v1.client.workspaces import Workspace
from extralit_v1.extraction.models.schema import DEFAULT_SCHEMA_S3_PATH


def delete_schema(
    ctx: typer.Context,
    name: str = typer.Argument(
        ...,
        help="The schema name (case-sensitive) to delete from the Workspace.",
    ),
    version_id: Optional[str] = typer.Option(
        None,
        "--version-id",
        "-v",
        help="The version ID of the schema to delete.",
    ),
    prefix: str = typer.Option(
        DEFAULT_SCHEMA_S3_PATH,
        "--prefix",
        help="The directory prefix containing the schema files in the Workspace's S3 bucket.",
        hidden=True,
    ),
) -> None:
    from argilla_v1.cli.rich import echo_in_panel

    try:
        workspace: Workspace = ctx.obj["workspace"]
        path = os.path.join(prefix, name)
        workspace.delete_file(path, version_id=version_id)

        echo_in_panel(
            f"Schema (name='{name}') in workspace '{workspace.name}' have been deleted successfully.",
            title="File deleted",
            title_align="left",
        )

    except Exception as e:
        echo_in_panel(
            f"Unable to list schemas in workspace:\n{e}",
            title="Unexpected error",
            title_align="left",
            success=False,
        )
        raise typer.Exit(code=1) from e
