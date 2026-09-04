"""Bake DuckDB's `lance` extension into the image, for this stage's target architecture.

    python install_lance_extension.py --duckdb-home /lance --duckdb-version 1.5.5
    python install_lance_extension.py --check --duckdb-version 1.5.5

`INSTALL lance` would be the obvious way to fetch it, but a release builds the non-native arch
under QEMU, where importing duckdb segfaults. Nothing here loads the native module: the payload
is a plain download and `--check` reads package metadata, so both survive emulation.

The version is passed in rather than derived so the fetch can live in a stage that does not
depend on the application wheel — otherwise a one-line code change re-downloads 231 MB. `--check`
is what keeps that pin honest: it fails the build if the venv resolved a different duckdb.

This extension is native code that the server later loads into its own process, so the payload
is fetched over TLS and checked against a pinned digest before it is written. An unpinned
version fails the build rather than trusting whatever the network returned.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import platform
import urllib.request
from importlib.metadata import version
from pathlib import Path

REPOSITORY = "https://extensions.duckdb.org"
# The CDN 403s the default Python-urllib agent; any identifiable one is served.
USER_AGENT = "extralit-server image build"
PLATFORMS = {"aarch64": "linux_arm64", "x86_64": "linux_amd64"}

#: sha256 of the *decompressed* extension, per duckdb version and target platform. Bumping
#: DUCKDB_VERSION means adding an entry here; see `--digest` for how to produce one.
DIGESTS = {
    "1.5.5": {
        "linux_amd64": "a8b1463e8541a960859b05c39096a60a3c777d12fd63d9867ce62bb251ab2a1a",
        "linux_arm64": "a710b8c2453e996ff810c718ccc9b26253a1cf6c1b6687fad0dd805f8878e2c9",
    },
}


def target_platform() -> str:
    machine = platform.machine()
    try:
        return PLATFORMS[machine]
    except KeyError:
        raise SystemExit(f"no DuckDB extension platform for {machine}") from None


def expected_digest(duckdb_version: str, target: str) -> str:
    try:
        return DIGESTS[duckdb_version][target]
    except KeyError:
        raise SystemExit(
            f"no pinned sha256 for the lance extension at duckdb {duckdb_version} on {target}. "
            f"This build will not load an unverified native extension into the server. Obtain the "
            f"digest, confirm it independently of this download, and add it to DIGESTS in "
            f"{Path(__file__).name} (`--digest` prints what the repository is currently serving)."
        ) from None


def download(duckdb_version: str, target: str) -> bytes:
    url = f"{REPOSITORY}/v{duckdb_version}/{target}/lance.duckdb_extension.gz"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return gzip.decompress(response.read())


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
    target = target_platform()
    expected = expected_digest(duckdb_version, target)

    payload = download(duckdb_version, target)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected:
        # Nothing is written: the bytes are not what this image is pinned to.
        raise SystemExit(
            f"the lance extension served for duckdb {duckdb_version} on {target} has sha256 "
            f"{digest}, but this image pins {expected}. Refusing to bake an unverified native "
            f"extension."
        )

    destination = duckdb_home / "extensions" / f"v{duckdb_version}" / target
    destination.mkdir(parents=True, exist_ok=True)
    written = destination / "lance.duckdb_extension"
    written.write_bytes(payload)
    print(f"wrote {written} ({len(payload)} bytes, sha256 {digest})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duckdb-version", help="defaults to the installed duckdb")
    parser.add_argument("--duckdb-home", type=Path, default=Path.home() / ".duckdb")
    parser.add_argument("--check", action="store_true", help="assert the venv agrees with the pin")
    parser.add_argument("--digest", action="store_true", help="print the served digest, for pinning")
    args = parser.parse_args()

    duckdb_version = args.duckdb_version or version("duckdb")
    if args.check:
        check(duckdb_version)
        print(f"ok: venv duckdb matches the baked lance extension ({duckdb_version})")
        return
    if args.digest:
        target = target_platform()
        print(f'"{target}": "{hashlib.sha256(download(duckdb_version, target)).hexdigest()}",')
        return
    fetch(duckdb_version, args.duckdb_home)


if __name__ == "__main__":
    main()
