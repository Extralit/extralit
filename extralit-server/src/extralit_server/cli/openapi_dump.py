import copy
import json
from pathlib import Path
from typing import Optional

import typer

# The contract version, not the package version: pinning it keeps the committed artifact
# stable across releases so `bump_version.py` never has to touch it.
CONTRACT_VERSION = "v1"


def build_openapi_document() -> str:
    """Render the /api/v1 OpenAPI schema as deterministic JSON."""
    # Imported lazily so `--help` stays fast and settings load only when the command runs.
    from extralit_server.api.routes import api_v1

    # `FastAPI.openapi()` returns its cached `openapi_schema`; mutating it would change /docs.
    schema = copy.deepcopy(api_v1.openapi())
    schema["info"]["version"] = CONTRACT_VERSION

    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def openapi_dump(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the schema to this file instead of stdout",
    ),
) -> None:
    """Dump the /api/v1 OpenAPI schema as deterministic JSON (for frontend type generation)."""
    text = build_openapi_document()

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text)
    else:
        typer.echo(text, nl=False)
