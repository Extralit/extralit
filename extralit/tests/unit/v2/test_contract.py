import json
import subprocess
import sys
from pathlib import Path

import pytest

SDK_ROOT = Path(__file__).parents[3]
API_DIR = SDK_ROOT / "src" / "extralit" / "v2" / "_api"
SNAPSHOT = API_DIR / "openapi.json"
GENERATED = API_DIR / "_generated.py"
SERVER_DIR = SDK_ROOT.parent / "extralit-server"

EXPECTED_MODELS = [
    "SchemaRead",
    "Schemas",
    "SchemaCreate",
    "SchemaUpdate",
    "SchemaVersionCreate",
    "SchemaVersionRead",
    "RecordUpsert",
    "RecordsBulkUpsert",
    "RecordRead",
    "Records",
    "RecordFilter",
    "RecordSearchQuery",
    "ReferenceGroup",
    "ReferenceView",
    "QuestionCreate",
    "QuestionUpdate",
    "QuestionRead",
    "Questions",
    "SuggestionUpsert",
    "SuggestionRead",
    "Suggestions",
    "ResponseUpsert",
    "ResponseRead",
    "ProjectionCell",
    "ProjectionRecord",
    "ProjectionView",
    "SchemaStatus",
    "V2RecordStatus",
    "QuestionType",
    "SuggestionType",
    "ResponseStatus",
]


def test_generated_models_importable():
    import extralit.v2._api._generated as gen

    missing = [name for name in EXPECTED_MODELS if not hasattr(gen, name)]
    assert not missing, f"generated module lacks: {missing}"


def test_generated_matches_snapshot(tmp_path):
    """No-drift gate: regenerating from the committed snapshot must be byte-identical."""
    out = tmp_path / "regen.py"
    # Pin: datamodel-code-generator>=0.68.1,<0.69 — a bump requires re-running codegen
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(SNAPSHOT),
            "--input-file-type",
            "openapi",
            "--output",
            str(out),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.10",
            "--use-double-quotes",
            "--disable-timestamp",
            "--no-use-union-operator",
            "--formatters",
            "black",
            "isort",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"datamodel-codegen failed (rc={proc.returncode}):\n{proc.stderr}"
    assert out.read_text() == GENERATED.read_text(), (
        "src/extralit/v2/_api/_generated.py drifted from openapi.json — rerun datamodel-codegen (see plan Task 1 Step 3)"
    )


@pytest.mark.slow
@pytest.mark.skipif(not SERVER_DIR.exists(), reason="server tree not present")
def test_snapshot_matches_server():
    """Snapshot-vs-server gate: committed snapshot must equal a fresh openapi-dump."""
    proc = subprocess.run(
        ["uv", "run", "python", "-m", "extralit_server", "openapi-dump"],
        cwd=SERVER_DIR,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(proc.stdout) == json.loads(SNAPSHOT.read_text()), (
        "openapi.json snapshot drifted from the server — re-dump it (see plan Task 1 Step 2)"
    )
