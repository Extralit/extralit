from __future__ import annotations

import typer


def add_v2_commands(app: typer.Typer) -> None:
    """Register v2 verbs at the TOP level of the extralit CLI (no `v2` prefix).
    v2 owns these names; the v1 `schemas` subcommand is deliberately replaced."""
    from extralit.v2.cli import questions, records, schemas

    app.add_typer(schemas.app, name="schemas")
    app.add_typer(records.app, name="records")
    app.add_typer(questions.app, name="questions")
