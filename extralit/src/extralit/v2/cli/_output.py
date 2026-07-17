from __future__ import annotations

import functools
import json
import sys
from typing import Any

import typer

from extralit.v2._api._errors import V2APIError, ValidationError


def to_jsonable(data: Any) -> Any:
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [to_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {key: to_jsonable(value) for key, value in data.items()}
    return data


def emit(data: Any, json_flag: bool) -> None:
    """JSON-first: --json forces JSON; a non-TTY stdout (pipes, agents, CI) defaults to it.
    Humans at a terminal get Rich output."""
    if json_flag or not sys.stdout.isatty():
        typer.echo(json.dumps(to_jsonable(data), default=str))
        return
    from rich.console import Console  # lazy: JSON path must not pay for rich

    Console().print(to_jsonable(data))


def fail(error: Exception) -> None:
    status = getattr(error, "status_code", None)
    payload = {
        "error": {"type": type(error).__name__, "status": status, "detail": str(getattr(error, "detail", error))}
    }
    typer.echo(json.dumps(payload, default=str), err=True)
    raise typer.Exit(code=3 if isinstance(error, ValidationError) else 1)


def handle_errors(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except V2APIError as error:
            fail(error)
        except (ValueError, OSError) as error:
            # Catches malformed UUID/JSON input (ValueError, JSONDecodeError) and
            # missing/unreadable --file paths (OSError/FileNotFoundError)
            fail(error)

    return wrapper
