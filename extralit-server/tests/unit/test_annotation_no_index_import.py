import ast
from pathlib import Path

import pytest

import extralit_server

ROOT = Path(extralit_server.__file__).parent
GUARDED = [
    ROOT / "contexts" / "v2" / "annotation.py",
    ROOT / "contexts" / "v2" / "projection.py",
    ROOT / "api" / "v2" / "annotation.py",
    ROOT / "api" / "v2" / "questions.py",
]


def _imports_index_engine(source: str) -> bool:
    """Return True if `source` imports extralit_server's Lance index engine (spec §17.5).

    Catches every realistic violating form, including:
      - `import extralit_server.index.lancedb_engine`
      - `import extralit_server.contexts.v2.index_sync`
      - `from extralit_server.index import ...`
      - `from extralit_server import index`
      - `from extralit_server.contexts.v2.index_sync import sync_upserted_records`
      - `from extralit_server.contexts.v2 import index_sync` (bare name, no "index"
        substring in `node.module` — the idiom actually used in
        api/v2/records.py and api/v2/schemas.py)
      - relative forms `from . import index_sync` / `from .. import index_sync`
        (where `node.module` is None)
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if "extralit_server" in name and "index" in name:
                    return True
                if name.endswith("index_sync"):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Relative imports (module is None/"") are necessarily within the
            # extralit_server package tree, since the guarded files live there.
            is_extralit_scoped = module == "" or "extralit_server" in module
            for alias in node.names:
                name = alias.name
                qualified = f"{module}.{name}" if module else name
                if name.endswith("index_sync"):
                    return True
                if "extralit_server" in qualified and "index" in qualified:
                    return True
                if is_extralit_scoped and name == "index":
                    return True
    return False


def test_annotation_modules_do_not_import_index_engine():
    for path in GUARDED:
        source = path.read_text()
        assert not _imports_index_engine(source), f"{path} imports the index engine"


VIOLATING_SNIPPETS = {
    "import extralit_server.index.lancedb_engine": "import extralit_server.index.lancedb_engine\n",
    "import extralit_server.contexts.v2.index_sync": "import extralit_server.contexts.v2.index_sync\n",
    "from extralit_server.index import ...": "from extralit_server.index import lancedb_engine\n",
    "from extralit_server import index": "from extralit_server import index\n",
    "from extralit_server.contexts.v2.index_sync import sync_upserted_records": (
        "from extralit_server.contexts.v2.index_sync import sync_upserted_records\n"
    ),
    "from extralit_server.contexts.v2 import index_sync": ("from extralit_server.contexts.v2 import index_sync\n"),
    "relative: from . import index_sync": "from . import index_sync\n",
    "relative: from .. import index_sync": "from .. import index_sync\n",
}

INNOCENT_SNIPPETS = {
    "from extralit_server.models.v2 import V2Record": "from extralit_server.models.v2 import V2Record\n",
    "from extralit_server.contexts.v2 import annotation": "from extralit_server.contexts.v2 import annotation\n",
    "import extralit_server.contexts.v2.annotation": "import extralit_server.contexts.v2.annotation\n",
    "from extralit_server.database import get_async_db": "from extralit_server.database import get_async_db\n",
}


@pytest.mark.parametrize("source", VIOLATING_SNIPPETS.values(), ids=VIOLATING_SNIPPETS.keys())
def test_detector_flags_every_violating_import_form(source):
    assert _imports_index_engine(source), f"detector failed to flag violating source: {source!r}"


@pytest.mark.parametrize("source", INNOCENT_SNIPPETS.values(), ids=INNOCENT_SNIPPETS.keys())
def test_detector_does_not_flag_innocent_imports(source):
    assert not _imports_index_engine(source), f"detector incorrectly flagged innocent source: {source!r}"
