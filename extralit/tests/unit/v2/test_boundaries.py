import re
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parents[3] / "src" / "extralit"
V2 = SRC / "v2"

# The single allowed v1 import inside v2 (credentials helper outlives v1 retirement).
ALLOWED_V1_IMPORT = "extralit.client.login"
V1_IMPORT = re.compile(r"^\s*(?:from|import)\s+(extralit\.(?!v2\b)[\w.]*)", re.MULTILINE)
V2_IMPORT = re.compile(r"^\s*(?:from|import)\s+extralit\.v2[\w.]*", re.MULTILINE)


def test_v2_imports_no_v1_except_credentials():
    violations = []
    for path in V2.rglob("*.py"):
        if path.name == "_generated.py":
            continue
        for match in V1_IMPORT.finditer(path.read_text()):
            if match.group(1) != ALLOWED_V1_IMPORT:
                violations.append(f"{path.relative_to(SRC)}: {match.group(0).strip()}")
    assert not violations, "v2 -> v1 imports outside the credentials exception:\n" + "\n".join(violations)


def test_v1_never_imports_v2_except_composition_root():
    violations = []
    for path in SRC.rglob("*.py"):
        if V2 in path.parents or path == SRC / "cli" / "app.py":
            continue
        if V2_IMPORT.search(path.read_text()):
            violations.append(str(path.relative_to(SRC)))
    assert not violations, "v1 files importing v2 (only cli/app.py may):\n" + "\n".join(violations)


HEAVY = ("pandas", "pandera", "datasets", "huggingface_hub")


def _heavy_after(imports: str) -> set:
    code = f"import sys; {imports}; print(','.join(sorted(m for m in {HEAVY!r} if m in sys.modules)))"
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    return set(filter(None, proc.stdout.strip().split(",")))


def test_v2_adds_no_heavy_imports():
    """Agents make many short CLI calls: importing extralit.v2 (incl. cli) must not add
    heavy modules beyond what `import extralit` (the v1 package init) already drags in.
    Delta-based on purpose: v1's own import weight is Phase 6 scope, measured at the
    baseline (today: datasets + huggingface_hub via extralit/__init__.py)."""
    baseline = _heavy_after("import extralit")
    with_v2 = _heavy_after("import extralit; import extralit.v2; import extralit.v2.cli")
    added = with_v2 - baseline
    assert not added, f"extralit.v2 import added heavy modules: {sorted(added)}"
