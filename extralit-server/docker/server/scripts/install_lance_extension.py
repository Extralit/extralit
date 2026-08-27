"""Bake DuckDB's `lance` extension into the image, for this stage's target architecture.

    python install_lance_extension.py --duckdb-home /lance --duckdb-version 1.5.5
    python install_lance_extension.py --check --duckdb-version 1.5.5

`INSTALL lance` would be the obvious way to fetch it, but a release builds the non-native arch
under QEMU, where importing duckdb segfaults. Nothing here loads the native module: the payload
is a plain download and `--check` reads package metadata, so both survive emulation.

The version is passed in rather than derived so the fetch can live in a stage that does not
depend on the application wheel — otherwise a one-line code change re-downloads 231 MB. `--check`
is what keeps that pin honest: it fails the build if the venv resolved a different duckdb.
"""

from __future__ import annotations

import argparse
import gzip
import platform
import urllib.request
from importlib.metadata import version
from pathlib import Path

REPOSITORY = "http://extensions.duckdb.org"
# The CDN 403s the default Python-urllib agent; any identifiable one is served.
USER_AGENT = "extralit-server image build"
PLATFORMS = {"aarch64": "linux_arm64", "x86_64": "linux_amd64"}


def target_platform() -> str:
    machine = platform.machine()
    try:
        return PLATFORMS[machine]
    except KeyError:
        raise SystemExit(f"no DuckDB extension platform for {machine}") from None


def check(expected: str) -> None:
    installed = version("duckdb")
    if installed != expected:
        raise SystemExit(
            f"the image bakes the lance extension for duckdb {expected}, but the venv resolved "
            f"{installed}. DuckDB looks extensions up under a version-named directory, so this "
            f"would ship an image whose first hybrid search fails. Set DUCKDB_VERSION={installed} "
            f"in the Dockerfile."
        )


def fetch(duckdb_version: str, duckdb_home: Path) -> None:
    destination = duckdb_home / "extensions" / f"v{duckdb_version}" / target_platform()
    destination.mkdir(parents=True, exist_ok=True)

    url = f"{REPOSITORY}/v{duckdb_version}/{target_platform()}/lance.duckdb_extension.gz"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        payload = gzip.decompress(response.read())

    written = destination / "lance.duckdb_extension"
    written.write_bytes(payload)
    print(f"wrote {written} ({len(payload)} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duckdb-version", help="defaults to the installed duckdb")
    parser.add_argument("--duckdb-home", type=Path, default=Path.home() / ".duckdb")
    parser.add_argument("--check", action="store_true", help="assert the venv agrees with the pin")
    args = parser.parse_args()

    duckdb_version = args.duckdb_version or version("duckdb")
    if args.check:
        check(duckdb_version)
        print(f"ok: venv duckdb matches the baked lance extension ({duckdb_version})")
        return
    fetch(duckdb_version, args.duckdb_home)


if __name__ == "__main__":
    main()
