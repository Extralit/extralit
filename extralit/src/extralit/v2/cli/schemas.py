from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Manage v2 schemas (Pandera, versioned)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("list")
@handle_errors
def list_schemas(
    workspace_id: str = typer.Option(..., "--workspace-id", help="Workspace UUID"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(client.schemas.list(UUID(workspace_id)), json_flag)


@app.command("get")
@handle_errors
def get_schema(schema_id: str = typer.Argument(...), json_flag: bool = JSON_FLAG):
    with get_client() as client:
        emit(client.schemas.get(UUID(schema_id)), json_flag)


@app.command("create")
@handle_errors
def create_schema(
    name: str = typer.Argument(...),
    workspace_id: str = typer.Option(..., "--workspace-id"),
    settings: Optional[str] = typer.Option(None, "--settings", help="Settings as a JSON object"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.schemas.create(UUID(workspace_id), name, settings=json.loads(settings) if settings else None),
            json_flag,
        )


@app.command("publish")
@handle_errors
def publish_version(
    schema_id: str = typer.Argument(...),
    file: Path = typer.Option(..., "--file", help="Pandera DataFrameSchema JSON (schema.to_json() output)"),
    review_widgets: Optional[str] = typer.Option(None, "--review-widgets", help="JSON: {column: widget config}"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.schemas.publish(
                UUID(schema_id),
                file.read_text(),
                review_widgets=json.loads(review_widgets) if review_widgets else None,
            ),
            json_flag,
        )


@app.command("versions")
@handle_errors
def list_versions(schema_id: str = typer.Argument(...), json_flag: bool = JSON_FLAG):
    with get_client() as client:
        emit(client.schemas.versions(UUID(schema_id)), json_flag)
