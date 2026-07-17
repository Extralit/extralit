from __future__ import annotations

from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Read v2 projections (response-or-suggestion per question)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("get")
@handle_errors
def get_projection(
    reference: str = typer.Argument(..., help="Reference (DOI/URL/filename; slashes fine)"),
    workspace_id: str = typer.Option(..., "--workspace-id"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(client.projections.get(UUID(workspace_id), reference), json_flag)
