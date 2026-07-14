from __future__ import annotations

import typer


def add_v2_commands(app: typer.Typer) -> None:
    """Register v2 verbs at the TOP level of the extralit CLI (no `v2` prefix).
    v2 owns these names; the v1 `schemas` subcommand is deliberately replaced."""
    from extralit.v2.cli import schemas

    app.add_typer(schemas.app, name="schemas")
