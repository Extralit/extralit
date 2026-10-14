import difflib
from pathlib import Path

from extralit_server.cli.openapi_dump import build_openapi_document

COMMITTED_SPEC = Path(__file__).parents[3] / "openapi" / "v1.json"
REGENERATE = "cd extralit-server && uv run python -m extralit_server.cli openapi-dump -o ../openapi/v1.json"


def test_committed_openapi_matches_the_application():
    generated = build_openapi_document()
    committed = COMMITTED_SPEC.read_text()

    if generated == committed:
        return

    diff = list(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            fromfile=f"{COMMITTED_SPEC.name} (committed)",
            tofile=f"{COMMITTED_SPEC.name} (generated)",
            n=2,
        )
    )
    truncated = "".join(diff[:120])
    if len(diff) > 120:
        truncated += f"\n... {len(diff) - 120} more diff lines\n"

    raise AssertionError(
        f"The API contract changed but {COMMITTED_SPEC.name} was not regenerated.\n\n"
        f"{truncated}\nRegenerate with:\n  {REGENERATE}\n"
    )
