import json
from pathlib import Path
from typing import Optional

import typer


def openapi_dump(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the schema to this file instead of stdout",
    ),
) -> None:
    """Dump the /api/v1 OpenAPI schema as deterministic JSON (for frontend type generation)."""
    # Imported lazily so `--help` stays fast and settings load only when the command runs.
    from extralit_server.api.routes import api_v1

    text = json.dumps(api_v1.openapi(), indent=2, sort_keys=True) + "\n"

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    else:
        typer.echo(text, nl=False)
