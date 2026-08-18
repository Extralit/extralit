"""Compare per-document Parquet sidecars against the workspace Lance datasets.

    uv run python scripts/bench_layout_store.py --docs 500 --items 250
    EXTRALIT_S3_ENDPOINT=http://localhost:9000 uv run python scripts/bench_layout_store.py --workspace bench

`--workspace` resolves the root through the same resolver production uses, so the S3 run measures
the real path (MinIO bucket `bench` must exist). Needs Redis for the workspace lock.
"""

from __future__ import annotations

import argparse
import io
import shutil
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from extralit_server.contexts.ocr import layout_store
from extralit_server.contexts.ocr.arrow import ITEM_SCHEMA, PAGE_SCHEMA
from extralit_server.contexts.ocr.layout_store import ITEMS_DATASET, PAGES_DATASET, LayoutStore

LABELS = ["text", "section_header", "table", "picture", "caption"]


def synth(document_id: str, n_items: int) -> tuple[pa.Table, pa.Table]:
    rows = [
        {
            "document_id": document_id,
            "self_ref": f"#/texts/{i}",
            "parent_ref": "#/body",
            "label": LABELS[i % len(LABELS)],
            "content_layer": "body",
            "level": 0,
            "reading_order": i,
            "prov_index": 0,
            "page_no": i % 10 + 1,
            "bbox": [10.0, float(i), 100.0, float(i) + 8.0],
            "coord_origin": "TOPLEFT",
            "charspan_start": 0,
            "charspan_end": 12,
            "text": f"item {i} of {document_id}",
            "html": None,
        }
        for i in range(n_items)
    ]
    pages = [{"document_id": document_id, "page_no": page, "width": 612.0, "height": 792.0} for page in range(1, 11)]
    return pa.Table.from_pylist(rows, schema=ITEM_SCHEMA), pa.Table.from_pylist(pages, schema=PAGE_SCHEMA)


def du(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def timed(label: str, fn):
    start = time.perf_counter()
    result = fn()
    print(f"{label:<44} {(time.perf_counter() - start) * 1000:8.1f} ms")
    return result


def lance_connection(store: LayoutStore) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    for name in (ITEMS_DATASET, PAGES_DATASET):
        connection.register(f"_{name}", store.source(name))
        connection.execute(f"create view {name} as select * from _{name}")
    return connection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", type=int, default=500)
    parser.add_argument("--items", type=int, default=250)
    parser.add_argument("--root", default="/tmp/bench-layout")
    parser.add_argument("--workspace", help="resolve the Lance root for this workspace instead of --root")
    args = parser.parse_args()

    root = Path(args.root)
    shutil.rmtree(root, ignore_errors=True)
    parquet_dir = root / "parquet" / "layout"
    parquet_dir.mkdir(parents=True)
    store = LayoutStore.for_workspace(args.workspace) if args.workspace else LayoutStore(str(root / "lance" / "layout"))

    documents = [
        (document_id, *synth(document_id, args.items)) for document_id in (str(uuid4()) for _ in range(args.docs))
    ]
    print(f"{args.docs} documents x {args.items} items at {store.root_uri}\n")

    def write_parquet():
        for document_id, items, _pages in documents:
            buffer = io.BytesIO()
            pq.write_table(items, buffer, compression="zstd")
            (parquet_dir / f"{document_id}.items.parquet").write_bytes(buffer.getvalue())

    def write_lance():
        for document_id, items, pages in documents:
            with store.locked_sync():
                store.replace_document(document_id, items, pages)
                store.maybe_compact()

    timed("write: parquet sidecars", write_parquet)
    elapsed = time.perf_counter()
    write_lance()
    print(f"{'write: lance replace + compaction':<44} {(time.perf_counter() - elapsed) * 1000 / args.docs:8.1f} ms/doc")

    glob = str(parquet_dir / "*.items.parquet")
    one = documents[0][0]
    connection = lance_connection(store)
    timed(
        "query: aggregate by label (parquet glob)",
        lambda: duckdb.sql(f"select label, page_no, count(*) from read_parquet('{glob}') group by 1, 2").fetchall(),
    )
    timed(
        "query: aggregate by label (lance)",
        lambda: connection.execute("select label, page_no, count(*) from items group by 1, 2").fetchall(),
    )
    timed(
        "query: one document (parquet glob)",
        lambda: duckdb.sql(f"select count(*) from read_parquet('{glob}') where document_id = '{one}'").fetchall(),
    )
    timed("query: one document (lance)", lambda: store.load_items(one).num_rows)

    print(f"\nfragments {store.fragment_count(ITEMS_DATASET)}")
    print(f"bytes: parquet {du(parquet_dir):,} over {len(list(parquet_dir.iterdir())):,} objects")
    if not args.workspace:
        lance_dir = root / "lance"
        print(f"bytes: lance   {du(lance_dir):,}  (retains {layout_store.CLEANUP_OLDER_THAN} of history)")
        store.open(ITEMS_DATASET).cleanup_old_versions(older_than=timedelta(0))
        store.open(PAGES_DATASET).cleanup_old_versions(older_than=timedelta(0))
        print(f"bytes: lance   {du(lance_dir):,}  (history dropped)")


if __name__ == "__main__":
    main()
