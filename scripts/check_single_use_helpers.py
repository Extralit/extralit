"""Warn about short functions with exactly one consumer in their package. Always exits 0.

Ruff cannot do this: it has no custom rules and analyses one file at a time. References are
matched by name across the package's `src/`, so tests are not consumers and a common name reads
as used often, which errs towards silence. Skipped: decorated functions, dunders, names in
`__all__`, and public names defined more than once, such as Protocol implementations. A private
module-level function is counted within its own module, so another module's `_bbox` does not hide it.
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def package_src(path: Path) -> Path | None:
    parts = path.parts
    return Path(*parts[: parts.index("src") + 1]) if "src" in parts else None


def definitions(tree: ast.Module) -> Iterator[FunctionNode]:
    """Module-level functions and methods; a nested function is not reachable from elsewhere."""
    for node in tree.body:
        if isinstance(node, FunctionNode):
            yield node
        elif isinstance(node, ast.ClassDef):
            yield from (child for child in node.body if isinstance(child, FunctionNode))


def exported_names(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "__all__" for t in node.targets
        ):
            return {
                e.value
                for e in getattr(node.value, "elts", [])
                if isinstance(e, ast.Constant)
            }
    return set()


def statement_count(node: FunctionNode) -> int:
    body = node.body[1:] if ast.get_docstring(node) is not None else node.body
    return sum(isinstance(child, ast.stmt) for stmt in body for child in ast.walk(stmt))


def references(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            yield node.id, node.lineno
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            yield node.attr, node.lineno


def check_package(src: Path, files: set[Path], max_statements: int) -> list[str]:
    defined: dict[str, int] = defaultdict(int)
    consumers: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    trees: dict[Path, ast.Module] = {}

    for path in src.rglob("*.py"):
        trees[path] = ast.parse(path.read_text(encoding="utf-8"))
        for node in definitions(trees[path]):
            defined[node.name] += 1
        for name, line in references(trees[path]):
            consumers[name].append((path, line))

    warnings = []
    for path in sorted(files):
        exported = exported_names(trees[path])
        module_level = {id(node) for node in trees[path].body}
        for node in definitions(trees[path]):
            name = node.name
            statements = statement_count(node)
            private = name.startswith("_") and id(node) in module_level
            skipped = node.decorator_list or name.startswith("__") or name in exported
            skipped = skipped or (defined[name] > 1 and not private)
            own_lines = range(node.lineno, (node.end_lineno or node.lineno) + 1)
            sites = [
                (p, line)
                for p, line in consumers[name]
                if p != path or line not in own_lines
            ]
            if private:
                sites = [(p, line) for p, line in sites if p == path]
            if not skipped and statements <= max_statements and len(sites) == 1:
                site_path, site_line = sites[0]
                warnings.append(
                    f"{path}:{node.lineno}: {name} ({statements} statements) has one consumer: {site_path}:{site_line}"
                )
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--max-statements", type=int, default=5)
    args = parser.parse_args()

    by_package: dict[Path, set[Path]] = defaultdict(set)
    for path in args.files:
        src = package_src(path)
        if src is not None and path.suffix == ".py":
            by_package[src].add(path)

    for src, files in by_package.items():
        for warning in check_package(src, files, args.max_statements):
            print(warning)


if __name__ == "__main__":
    main()
