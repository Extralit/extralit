from __future__ import annotations

import json
import sys
from typing import Optional
from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Manage v2 records (schema-version-pinned, reference-keyed)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


def _parse_filter(raw: str) -> tuple:
    """col:op:value — value is JSON-decoded when possible ('age:ge:18' -> int 18)."""
    column, op, value = raw.split(":", 2)
    try:
        value = json.loads(value)
    except ValueError:
        pass  # keep as string
    return (column, op, value)


def _read_jsonl(file: Optional[str]) -> list[dict]:
    stream = sys.stdin if file in (None, "-") else open(file, encoding="utf-8")
    try:
        return [json.loads(line) for line in stream if line.strip()]
    finally:
        if stream is not sys.stdin:
            stream.close()


@app.command("upsert")
@handle_errors
def upsert_records(
    schema_id: str = typer.Argument(...),
    file: Optional[str] = typer.Option(None, "--file", help="JSONL file of items; '-' or omitted reads stdin"),
    reference: Optional[str] = typer.Option(None, "--reference", help="Reference applied to items lacking one"),
    json_flag: bool = JSON_FLAG,
):
    items = _read_jsonl(file)
    with get_client() as client:
        emit(client.records.bulk_upsert(UUID(schema_id), items, reference=reference), json_flag)


@app.command("search")
@handle_errors
def search_records(
    schema_id: str = typer.Argument(...),
    text: Optional[str] = typer.Option(None, "--text"),
    filters: list[str] = typer.Option([], "--filter", help="col:op:value (op: eq|in|ge|le); repeatable"),
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(50, "--limit"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.records.search(
                UUID(schema_id),
                text=text,
                filters=[_parse_filter(raw) for raw in filters],
                offset=offset,
                limit=limit,
            ),
            json_flag,
        )


@app.command("list")
@handle_errors
def list_records(
    schema_id: str = typer.Argument(...),
    status: Optional[str] = typer.Option(None, "--status"),
    reference: Optional[str] = typer.Option(None, "--reference"),
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(50, "--limit"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.records.list(UUID(schema_id), status=status, reference=reference, offset=offset, limit=limit),
            json_flag,
        )


@app.command("delete")
@handle_errors
def delete_records(
    schema_id: str = typer.Argument(...),
    ids: str = typer.Option(..., "--ids", help="Comma-separated record ids"),
    json_flag: bool = JSON_FLAG,
):
    record_ids = ids.split(",")
    with get_client() as client:
        client.records.delete(UUID(schema_id), record_ids)
    emit({"deleted": len(record_ids)}, json_flag)
