"""Probe how DuckDB's `lance` extension reads dictionary, JSON and VARIANT columns written by pylance.

Standalone (no extralit imports) so it also runs under older pins:

    uv run python scripts/probe_lance_types.py                # every probe, one subprocess each
    uv run python scripts/probe_lance_types.py --probe dict   # one probe, JSON result on stdout
    uv run --isolated --no-project --python 3.12 --with duckdb==1.5.5 --with duckdb-extension-lance==1.5.5 \
        --with pylance==14.0.2 --with pyarrow==26.0.0 --with numpy python scripts/probe_lance_types.py
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import statistics
import subprocess
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

import duckdb
import lance
import numpy as np
import pyarrow as pa

DIM = 16
ROWS = 1_000
TIMING_ROWS = 100_000
KINDS = ("text", "table", "figure")
SECTIONS = ("Methods", "Results", "Discussion")
VOCAB = [f"w{i}" for i in range(500)]
PROBES = ("dict", "dict_nofilter", "json", "json_large", "variant", "self_match", "ivf_rq", "timing")


def connect(root: str) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(config={"extension_directory": tempfile.mkdtemp()})
    path = (
        importlib.resources.files("duckdb_extension_lance")
        / "extensions"
        / f"v{duckdb.__version__}"
        / "lance.duckdb_extension"
    )
    connection.execute(f"LOAD '{path}'")
    connection.execute(f"ATTACH '{root}' AS ns (TYPE LANCE, READ_ONLY false)")
    return connection


def base_columns(n: int, seed: int = 0) -> dict[str, pa.Array]:
    rng = np.random.default_rng(seed)
    words = rng.integers(0, len(VOCAB), size=(n, 12))
    texts = [" ".join(VOCAB[w] for w in row) + (" quokka" if i % 97 == 0 else "") for i, row in enumerate(words)]
    vectors = rng.standard_normal((n, DIM)).astype(np.float32)
    kinds = [KINDS[0] if i % 10 else KINDS[1] for i in range(n)]
    kinds = [KINDS[2] if i % 10 == 5 else k for i, k in enumerate(kinds)]
    return {
        "chunk_id": pa.array([f"c{i}" for i in range(n)]),
        "kind": pa.array(kinds),
        "text": pa.array(texts),
        "vector": pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel()), DIM),
    }


def meta_values(n: int) -> list[str]:
    return [json.dumps({"section": SECTIONS[i % 3], "n": i}) for i in range(n)]


def write(root: Path, table: pa.Table, index: str = "IVF_HNSW_FLAT", **index_args) -> lance.LanceDataset:
    dataset = lance.write_dataset(table, (root / "chunks.lance").as_uri(), mode="create")
    dataset.create_scalar_index("text", "INVERTED")
    dataset.create_index("vector", index, num_partitions=1, **index_args)
    return lance.dataset((root / "chunks.lance").as_uri())


def vector_literal(vector) -> str:
    return f"[{', '.join(repr(float(x)) for x in vector)}]::FLOAT[{DIM}]"


def check(results: dict, name: str, fn) -> None:
    # Streamed so the driver keeps finished steps and can name the one that segfaulted.
    print(f"STEP {name}", flush=True)
    try:
        results[name] = fn()
    except Exception as error:
        results[name] = {"ok": False, "error": f"{type(error).__name__}: {str(error)[:300]}"}
    print("RESULT " + json.dumps({name: results[name]}), flush=True)


# --- probes ------------------------------------------------------------------------------------


def probe_dict(root: Path) -> dict:
    columns = base_columns(ROWS)
    columns["kind"] = columns["kind"].dictionary_encode().cast(pa.dictionary(pa.int8(), pa.string()))
    write(root, pa.table(columns))
    connection = connect(root.as_uri())
    expected = {k: sum(1 for x in base_columns(ROWS)["kind"].to_pylist() if x == k) for k in KINDS}
    query = vector_literal(columns["vector"][0].values.to_numpy())
    results: dict = {}

    def scan():
        got = dict(connection.execute("SELECT kind, count(*) FROM ns.main.chunks GROUP BY 1").fetchall())
        return {"ok": got == expected, "got": got}

    def fts():
        rows = connection.execute(
            "SELECT kind FROM lance_fts('ns.main.chunks', 'text', 'w1 w2 w3', k=20, "
            "filter := 'kind = ''table''', prefilter := true)"
        ).fetchall()
        return {
            "ok": len(rows) == 20 and {r[0] for r in rows} == {"table"},
            "n": len(rows),
            "kinds": sorted({r[0] for r in rows}),
        }

    def vector(projection: str):
        def run():
            rows = connection.execute(
                f"SELECT {projection} FROM lance_vector_search('ns.main.chunks', 'vector', {query}, k=20, "
                "filter := 'kind = ''table''', prefilter := true)"
            ).fetchall()
            kinds = {r[0] for r in rows}
            return {"ok": len(rows) == 20 and kinds == {"table"}, "n": len(rows), "kinds": sorted(kinds)}

        return run

    check(results, "scan", scan)
    check(results, "fts_prefilter", fts)
    check(results, "vector_prefilter_kind_only", vector("kind"))
    check(results, "vector_prefilter_full_row", vector("kind, chunk_id, text, vector"))
    return results


def probe_dict_nofilter(root: Path) -> dict:
    columns = base_columns(ROWS)
    columns["kind"] = columns["kind"].dictionary_encode().cast(pa.dictionary(pa.int8(), pa.string()))
    write(root, pa.table(columns))
    connection = connect(root.as_uri())
    query = vector_literal(columns["vector"][0].values.to_numpy())
    truth = dict(zip(base_columns(ROWS)["chunk_id"].to_pylist(), base_columns(ROWS)["kind"].to_pylist(), strict=True))
    results: dict = {}

    def leg(sql: str):
        def run():
            rows = connection.execute(sql).fetchall()
            wrong = sum(1 for chunk_id, kind in rows if truth[chunk_id] != kind)
            return {"ok": len(rows) == 20 and wrong == 0, "n": len(rows), "wrong_kind": wrong}

        return run

    check(
        results,
        "fts_kind_values",
        leg("SELECT chunk_id, kind FROM lance_fts('ns.main.chunks', 'text', 'w1 w2 w3', k=20)"),
    )
    check(
        results,
        "vector_kind_values",
        leg(f"SELECT chunk_id, kind FROM lance_vector_search('ns.main.chunks', 'vector', {query}, k=20)"),
    )
    return results


def _probe_json(root: Path, json_type: pa.DataType) -> dict:
    columns = base_columns(ROWS)
    columns["meta"] = pa.array(meta_values(ROWS), json_type)
    results: dict = {}
    try:
        dataset = write(root, pa.table(columns))
    except Exception as error:
        return {"write": {"ok": False, "error": f"{type(error).__name__}: {str(error)[:300]}"}}
    results["write"] = {"ok": True, "stored_type": str(dataset.schema.field("meta").type)}
    connection = connect(root.as_uri())

    def duck_type():
        return {"ok": True, "type": connection.execute("SELECT typeof(meta) FROM ns.main.chunks LIMIT 1").fetchone()[0]}

    def extract():
        rows = connection.execute(
            "SELECT json_extract_string(meta, '$.section') FROM ns.main.chunks ORDER BY chunk_id LIMIT 5"
        ).fetchall()
        got = [r[0] for r in rows]
        ordered = sorted([f"c{i}" for i in range(ROWS)])[:5]
        want = [SECTIONS[int(c[1:]) % 3] for c in ordered]
        return {"ok": got == want, "got": got}

    def pushdown(expression: str):
        def run():
            rows = connection.execute(
                f"SELECT chunk_id FROM lance_fts('ns.main.chunks', 'text', 'w1 w2 w3', k=20, "
                f"filter := '{expression}', prefilter := true)"
            ).fetchall()
            ids = [int(r[0][1:]) for r in rows]
            return {"ok": len(ids) > 0 and all(i % 3 == 0 for i in ids), "n": len(ids)}

        return run

    check(results, "duckdb_type", duck_type)
    check(results, "duckdb_json_extract", extract)
    check(results, "lance_filter_json_extract", pushdown("json_extract(meta, ''$.section'') = ''\"Methods\"''"))
    check(results, "lance_filter_json_get_string", pushdown("json_get_string(meta, ''section'') = ''Methods''"))
    return results


def probe_json(root: Path) -> dict:
    return _probe_json(root, pa.json_())


def probe_json_large(root: Path) -> dict:
    return _probe_json(root, pa.json_(pa.large_string()))


def probe_variant(root: Path) -> dict:
    results: dict = {}
    scratch = duckdb.connect()
    try:
        scratch.execute("SELECT 1::VARIANT").fetchall()
        results["duckdb_has_variant"] = {"ok": True}
    except Exception as error:
        return {"duckdb_has_variant": {"ok": False, "error": f"{type(error).__name__}: {str(error)[:200]}"}}

    sections = ", ".join(f"'{s}'" for s in SECTIONS)
    variants = scratch.sql(
        f"SELECT {{'section': [{sections}][(i % 3) + 1], 'n': i}}::VARIANT AS v FROM range({ROWS}) t(i) ORDER BY i"
    ).to_arrow_table()
    results["arrow_type_from_duckdb"] = {
        "ok": True,
        "type": str(variants.schema.field("v").type),
        "metadata": str(variants.schema.field("v").metadata),
    }

    columns = base_columns(ROWS)
    columns["v"] = variants.column("v").combine_chunks()
    table = pa.Table.from_arrays(
        list(columns.values()),
        schema=pa.schema(
            [pa.field(name, array.type) for name, array in columns.items() if name != "v"]
            + [variants.schema.field("v")]
        ),
    )
    try:
        dataset = write(root, table)
        field = dataset.schema.field("v")
        results["lance_write"] = {"ok": True, "stored_type": str(field.type), "metadata": str(field.metadata)}
    except Exception as error:
        results["lance_write"] = {"ok": False, "error": f"{type(error).__name__}: {str(error)[:300]}"}
        return results

    def pylance_roundtrip():
        back = lance.dataset((root / "chunks.lance").as_uri()).to_table(columns=["v"]).column("v")
        return {"ok": back.combine_chunks().equals(columns["v"].cast(back.type)), "type": str(back.type)}

    connection = connect(root.as_uri())

    def duck_type():
        return {"ok": True, "type": connection.execute("SELECT typeof(v) FROM ns.main.chunks LIMIT 1").fetchone()[0]}

    def duck_extract():
        rows = connection.execute(
            "SELECT variant_extract(v, 'section')::VARCHAR FROM ns.main.chunks ORDER BY chunk_id LIMIT 5"
        ).fetchall()
        ordered = sorted([f"c{i}" for i in range(ROWS)])[:5]
        want = [SECTIONS[int(c[1:]) % 3] for c in ordered]
        return {"ok": [r[0] for r in rows] == want, "got": [r[0] for r in rows]}

    def pushdown(expression: str):
        def run():
            rows = connection.execute(
                f"SELECT chunk_id FROM lance_fts('ns.main.chunks', 'text', 'w1 w2 w3', k=20, "
                f"filter := '{expression}', prefilter := true)"
            ).fetchall()
            ids = [int(r[0][1:]) for r in rows]
            return {"ok": len(ids) > 0 and all(i % 3 == 0 for i in ids), "n": len(ids)}

        return run

    def accepted(expression: str):
        def run():
            rows = connection.execute(
                f"SELECT chunk_id FROM lance_fts('ns.main.chunks', 'text', 'w1 w2 w3', k=20, "
                f"filter := '{expression}', prefilter := true)"
            ).fetchall()
            return {"ok": len(rows) == 20, "n": len(rows)}

        return run

    check(results, "pylance_roundtrip", pylance_roundtrip)
    check(results, "duckdb_type", duck_type)
    check(results, "duckdb_variant_extract", duck_extract)
    check(results, "lance_filter_variant_get", pushdown("variant_get(v, ''$.section'', ''string'') = ''Methods''"))
    check(results, "lance_filter_struct_field_accepted", accepted("v.value IS NOT NULL"))
    return results


def _self_match(root: Path, index: str, **index_args) -> dict:
    columns = base_columns(ROWS, seed=1)
    dataset = write(root, pa.table(columns), index=index, **index_args)
    connection = connect(root.as_uri())
    sample = range(0, ROWS, ROWS // 20)
    duck_hits = pylance_hits = 0
    for i in sample:
        vector = columns["vector"][i].values.to_numpy()
        top = connection.execute(
            f"SELECT chunk_id FROM lance_vector_search('ns.main.chunks', 'vector', {vector_literal(vector)}, k=10) "
            "ORDER BY _distance LIMIT 1"
        ).fetchone()[0]
        duck_hits += top == f"c{i}"
        nearest = dataset.to_table(nearest={"column": "vector", "q": vector, "k": 10}, columns=["chunk_id"])
        pylance_hits += nearest.column(0)[0].as_py() == f"c{i}"
    return {
        "ok": duck_hits == len(sample),
        "duckdb_top1": f"{duck_hits}/{len(sample)}",
        "pylance_top1": f"{pylance_hits}/{len(sample)}",
    }


def probe_self_match(root: Path) -> dict:
    return {"ivf_hnsw_flat": _self_match(root, "IVF_HNSW_FLAT")}


def probe_ivf_rq(root: Path) -> dict:
    results = {}
    for bits in (1, 4):
        sub = root / f"rq{bits}"
        sub.mkdir()
        check(results, f"num_bits={bits}", lambda sub=sub, bits=bits: _self_match(sub, "IVF_RQ", num_bits=bits))
    return results


def probe_timing(root: Path) -> dict:
    columns = base_columns(TIMING_ROWS, seed=2)
    write(root, pa.table(columns))
    connection = connect(root.as_uri())
    query = vector_literal(columns["vector"][123].values.to_numpy())
    filter_ = "kind = ''table''"
    leg = f"k=50, filter := '{filter_}', prefilter := true)"
    fts = f"SELECT chunk_id, _score AS s FROM lance_fts('ns.main.chunks', 'text', 'w1 w2 quokka', {leg}"
    vec = f"SELECT chunk_id, _distance AS d FROM lance_vector_search('ns.main.chunks', 'vector', {query}, {leg}"
    hybrid = f"""
        WITH f AS (SELECT chunk_id, row_number() OVER (ORDER BY s DESC) AS r FROM ({fts})),
             v AS (SELECT chunk_id, row_number() OVER (ORDER BY d ASC) AS r FROM ({vec}))
        SELECT coalesce(f.chunk_id, v.chunk_id) AS chunk_id,
               coalesce(1.0 / (60 + f.r), 0) + coalesce(1.0 / (60 + v.r), 0) AS rrf
        FROM f FULL OUTER JOIN v ON f.chunk_id = v.chunk_id ORDER BY rrf DESC LIMIT 10"""
    timings = {}
    for name, sql in (("fts", fts), ("vector", vec), ("hybrid", hybrid)):
        connection.execute(sql).fetchall()
        samples = []
        for _ in range(7):
            start = time.perf_counter()
            connection.execute(sql).fetchall()
            samples.append((time.perf_counter() - start) * 1000)
        timings[name] = {
            "ok": True,
            "median_ms": round(statistics.median(samples), 1),
            "min_ms": round(min(samples), 1),
        }
    return timings


# --- driver ------------------------------------------------------------------------------------


def versions() -> dict[str, str]:
    out = {"python": sys.version.split()[0]}
    for package in ("duckdb", "duckdb-extension-lance", "pylance", "pyarrow"):
        out[package] = version(package)
    return out


def run_one(name: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        print("RESULT " + json.dumps(globals()[f"probe_{name}"](Path(directory))), flush=True)


def run_all() -> None:
    report = {"versions": versions(), "probes": {}}
    for name in PROBES:
        process = subprocess.run(
            [sys.executable, __file__, "--probe", name], capture_output=True, text=True, timeout=1800
        )
        results, started = {}, None
        for line in process.stdout.splitlines():
            if line.startswith("STEP "):
                started = line[5:]
            elif line.startswith("RESULT "):
                results.update(json.loads(line[7:]))
        if process.returncode != 0:
            tail = [x for x in (process.stderr or "").strip().splitlines() if "Fatal" in x or "Error" in x][-2:]
            results[started or "probe"] = {"crash": True, "returncode": process.returncode, "stderr": tail}
        report["probes"][name] = results
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", choices=PROBES)
    args = parser.parse_args()
    run_one(args.probe) if args.probe else run_all()
