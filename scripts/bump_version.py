#!/usr/bin/env python3
"""Single owner of the project version, which lives in three hand-synced files.

    python scripts/bump_version.py check                  # print the version, fail if they disagree
    python scripts/bump_version.py check --expect 0.7.0   # post-condition assertion
    python scripts/bump_version.py set --version 0.7.0    # rewrite all three

`check` prints the bare version to stdout and everything else to stderr, so CI can do
`V=$(python scripts/bump_version.py check)`. Called by the release workflow and by the
build workflows that previously each grepped `_version.py` by hand.

Stdlib only, and paths resolve relative to this file rather than the CWD — workflow steps
run it from `extralit-server/`, `extralit/`, and the repo root.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# X.Y.Z only. Deliberately matches the validation in .github/workflows/release.yml so the
# two can't disagree about what a releasable version looks like.
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# `^__version__ = "..."` anchored at line start so a version string inside a docstring or
# comment can't be picked up.
PY_VERSION = re.compile(r'^(__version__\s*=\s*")([^"]*)(")', re.MULTILINE)

# The first `"version": "..."` in package.json. Anchored to line start; the result is
# re-parsed as JSON afterwards to prove we hit the top-level key and not a nested one.
JSON_VERSION = re.compile(r'^(\s*"version"\s*:\s*")([^"]*)(")', re.MULTILINE)


@dataclass(frozen=True)
class VersionFile:
    path: Path
    pattern: re.Pattern
    is_json: bool = False

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(REPO_ROOT))

    def read(self) -> str:
        if not self.path.exists():
            die(f"{self.rel}: file not found")
        text = self.path.read_text()
        if self.is_json:
            # Authoritative for reads: no regex ambiguity about which key we got.
            try:
                version = json.loads(text).get("version")
            except json.JSONDecodeError as exc:
                die(f"{self.rel}: invalid JSON ({exc})")
            if not isinstance(version, str):
                die(f'{self.rel}: no top-level string "version" key')
            return version
        match = self.pattern.search(text)
        if not match:
            die(f'{self.rel}: no `__version__ = "..."` assignment found')
        return match.group(2)

    def write(self, version: str) -> bool:
        """Rewrite in place. Returns True if the file changed."""
        text = self.path.read_text()
        new_text, count = self.pattern.subn(
            lambda m: f"{m.group(1)}{version}{m.group(3)}", text, count=1
        )
        if count != 1:
            die(f"{self.rel}: version pattern did not match; refusing to guess")
        if self.is_json:
            # Prove the substitution landed on the top-level key rather than a nested one.
            try:
                parsed = json.loads(new_text)
            except json.JSONDecodeError as exc:
                die(f"{self.rel}: rewrite produced invalid JSON ({exc})")
            if parsed.get("version") != version:
                die(
                    f'{self.rel}: rewrite hit a nested "version" key, not the top-level one '
                    f"(top-level is still {parsed.get('version')!r})"
                )
        if new_text == text:
            return False
        self.path.write_text(new_text)
        return True


FILES = (
    VersionFile(
        REPO_ROOT / "extralit" / "src" / "extralit" / "_version.py", PY_VERSION
    ),
    VersionFile(
        REPO_ROOT / "extralit-server" / "src" / "extralit_server" / "_version.py",
        PY_VERSION,
    ),
    VersionFile(
        REPO_ROOT / "extralit-frontend" / "package.json", JSON_VERSION, is_json=True
    ),
)


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def current_versions() -> dict[str, str]:
    return {f.rel: f.read() for f in FILES}


def cmd_check(args: argparse.Namespace) -> int:
    versions = current_versions()
    distinct = set(versions.values())

    if len(distinct) != 1:
        print("error: version files disagree:", file=sys.stderr)
        for rel, version in versions.items():
            print(f"  {version}  {rel}", file=sys.stderr)
        print("run `bump_version.py set --version X.Y.Z` to resync", file=sys.stderr)
        return 1

    version = distinct.pop()

    if args.expect is not None and version != args.expect:
        print(f"error: expected {args.expect}, found {version}", file=sys.stderr)
        return 1

    for rel in versions:
        print(f"  {version}  {rel}", file=sys.stderr)
    print(version)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    version = args.version
    if not SEMVER.match(version):
        die(f"{version!r} is not X.Y.Z")

    changed = []
    for f in FILES:
        if f.write(version):
            changed.append(f.rel)

    if changed:
        for rel in changed:
            print(f"  updated  {rel}", file=sys.stderr)
    else:
        print(f"already at {version}; nothing to do", file=sys.stderr)

    # Post-condition: never claim success on a partial rewrite.
    versions = current_versions()
    if set(versions.values()) != {version}:
        die(f"post-condition failed, files are now inconsistent: {versions}")

    print(version)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser(
        "check", help="print the version; fail if the files disagree"
    )
    p_check.add_argument(
        "--expect", metavar="X.Y.Z", help="also assert the version equals this"
    )
    p_check.set_defaults(func=cmd_check)

    p_set = sub.add_parser("set", help="rewrite the version in every file")
    p_set.add_argument("--version", required=True, metavar="X.Y.Z")
    p_set.set_defaults(func=cmd_set)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
