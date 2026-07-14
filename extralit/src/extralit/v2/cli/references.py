from __future__ import annotations

from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Cross-schema reference views", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("get")
@handle_errors
def get_reference(
    reference: str = typer.Argument(..., help="Reference (DOI/URL/filename; slashes fine)"),
    workspace_id: str = typer.Option(..., "--workspace-id"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(client.records.get_reference(UUID(workspace_id), reference), json_flag)
