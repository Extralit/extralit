from __future__ import annotations

from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Inspect v2 questions (column-bound)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("list")
@handle_errors
def list_questions(schema_id: str = typer.Argument(...), json_flag: bool = JSON_FLAG):
    with get_client() as client:
        emit(client.questions.list(UUID(schema_id)), json_flag)
