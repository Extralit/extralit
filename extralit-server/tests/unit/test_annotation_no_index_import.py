import ast
from pathlib import Path

import extralit_server

ROOT = Path(extralit_server.__file__).parent
GUARDED = [
    ROOT / "contexts" / "v2" / "annotation.py",
    ROOT / "contexts" / "v2" / "projection.py",
    ROOT / "api" / "v2" / "annotation.py",
    ROOT / "api" / "v2" / "questions.py",
]


def test_annotation_modules_do_not_import_index_engine():
    for path in GUARDED:
        tree = ast.parse(path.read_text())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert not any("index" in m and "extralit_server" in m for m in imported), f"{path} imports the index engine"
        assert not any(m.endswith("index_sync") for m in imported), f"{path} imports index_sync"
