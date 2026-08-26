"""Bake DuckDB's `lance` extension into the image, for this stage's target architecture.

`INSTALL lance` would be the obvious way to do this, but a release builds the non-native
arch under QEMU, where importing duckdb segfaults. Nothing here loads the native module:
the version comes from package metadata and the payload is a plain download, so the step
survives emulation. `smoke_retrieval_deps.py` is what proves the file landed where DuckDB
looks for it.
"""

from __future__ import annotations

import gzip
import platform
import urllib.request
from importlib.metadata import version
from pathlib import Path

REPOSITORY = "http://extensions.duckdb.org"
# The CDN 403s the default Python-urllib agent; any identifiable one is served.
USER_AGENT = "extralit-server image build"
PLATFORMS = {"aarch64": "linux_arm64", "x86_64": "linux_amd64"}


def main() -> None:
    machine = platform.machine()
    try:
        target = PLATFORMS[machine]
    except KeyError:
        raise SystemExit(f"no DuckDB extension platform for {machine}") from None

    duckdb_version = f"v{version('duckdb')}"
    destination = Path.home() / ".duckdb" / "extensions" / duckdb_version / target
    destination.mkdir(parents=True, exist_ok=True)

    url = f"{REPOSITORY}/{duckdb_version}/{target}/lance.duckdb_extension.gz"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        payload = gzip.decompress(response.read())

    written = destination / "lance.duckdb_extension"
    written.write_bytes(payload)
    print(f"wrote {written} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
