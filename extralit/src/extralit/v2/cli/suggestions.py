from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Write v2 suggestions (per record x question)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("upsert")
@handle_errors
def upsert_suggestion(
    record_id: str = typer.Argument(...),
    question_id: Optional[str] = typer.Option(None, "--question-id", help="Question UUID"),
    question: Optional[str] = typer.Option(None, "--question", help="Question NAME (needs --schema-id)"),
    schema_id: Optional[str] = typer.Option(None, "--schema-id", help="Schema UUID for name resolution"),
    value: str = typer.Option(..., "--value", help="Suggested value as JSON (e.g. '\"120\"' or '[1,2]')"),
    score: Optional[float] = typer.Option(None, "--score"),
    agent: Optional[str] = typer.Option(None, "--agent"),
    json_flag: bool = JSON_FLAG,
):
    if question_id is None and question is None:
        raise typer.BadParameter("pass --question-id or --question")
    if question is not None and question_id is None and schema_id is None:
        raise typer.BadParameter("--question (a name) requires --schema-id to resolve against")
    with get_client() as client:
        emit(
            client.suggestions.upsert(
                record_id,
                question_id or question,
                json.loads(value),
                score=score,
                agent=agent,
                schema_id=UUID(schema_id) if schema_id else None,
            ),
            json_flag,
        )
