"""Assert the retrieval pipeline's non-Python payloads are present in this environment.

    docker run --rm extralit/extralit-server:latest python smoke_retrieval_deps.py

Each of these fails late and confusingly in production — a first hybrid search that cannot
reach the DuckDB extension repository, or a first scanned page that finds no language data —
so the image build runs this instead of discovering them under load.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def check_lance_extension() -> str:
    import duckdb

    connection = duckdb.connect()
    # No INSTALL: the point is that the extension is already on disk.
    connection.execute("LOAD lance")
    functions = connection.execute(
        "select function_name from duckdb_functions() where function_name in ('lance_fts', 'lance_vector_search')"
    ).fetchall()
    missing = {"lance_fts", "lance_vector_search"} - {name for (name,) in functions}
    if missing:
        raise RuntimeError(f"the lance extension loaded without {sorted(missing)}")
    return f"duckdb {duckdb.__version__} + lance extension"


def check_liteparse() -> str:
    import liteparse

    parser = liteparse.LiteParse(extract_blocks=True, quiet=True)
    parser.close()
    return f"liteparse {liteparse.__version__}"


def check_tessdata() -> str:
    prefix = os.environ.get("TESSDATA_PREFIX")
    if not prefix:
        raise RuntimeError("TESSDATA_PREFIX is unset, so OCR would download language data on first use")
    if not (Path(prefix) / "eng.traineddata").is_file():
        raise RuntimeError(f"no eng.traineddata under {prefix}")
    return f"tessdata at {prefix}"


def check_chonkie() -> str:
    from chonkie import RecursiveChunker, RecursiveRules

    chunker = RecursiveChunker(tokenizer="character", chunk_size=64, rules=RecursiveRules())
    if not chunker("one two three. four five six."):
        raise RuntimeError("RecursiveChunker returned no chunks")
    import chonkie

    return f"chonkie {chonkie.__version__}"


def main() -> int:
    failures = 0
    for check in (check_lance_extension, check_liteparse, check_tessdata, check_chonkie):
        name = check.__name__.removeprefix("check_")
        try:
            print(f"ok    {name}: {check()}")
        except Exception as error:
            failures += 1
            print(f"FAIL  {name}: {type(error).__name__}: {error}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
