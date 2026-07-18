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
    """Dump the /api/v2 OpenAPI schema as deterministic JSON (for frontend type generation)."""
    # Imported lazily so `--help` stays fast and settings load only when the command runs.
    from extralit_server.api.v2 import api_v2

    text = json.dumps(api_v2.openapi(), indent=2, sort_keys=True) + "\n"

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    else:
        typer.echo(text, nl=False)
