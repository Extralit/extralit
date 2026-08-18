"""Tests for the workspace-scoped Lance layout store."""

from __future__ import annotations

import threading
import time
from uuid import uuid4

import pyarrow as pa
import pytest

from extralit_server.contexts import files
from extralit_server.contexts.ocr.arrow import ITEM_SCHEMA, PAGE_SCHEMA
from extralit_server.contexts.ocr.layout_store import (
    ITEMS_DATASET,
    LAYOUT_PREFIX,
    LayoutStore,
    duckdb_connection,
)
from extralit_server.settings import settings

WORKSPACE = "ws-layout"


def items(document_id: str, count: int = 3, label: str = "text") -> pa.Table:
    return pa.Table.from_pylist(
        [
            {
                "document_id": document_id,
                "self_ref": f"#/texts/{i}",
                "parent_ref": "#/body",
                "label": label,
                "content_layer": "body",
                "level": 1,
                "reading_order": i,
                "prov_index": 0,
                "page_no": 1,
                "bbox": [0.0, 0.0, 10.0, 10.0],
                "coord_origin": "TOPLEFT",
                "charspan_start": 0,
                "charspan_end": 5,
                "text": f"row {i}",
                "html": None,
            }
            for i in range(count)
        ],
        schema=ITEM_SCHEMA,
    )


def pages(document_id: str, count: int = 1) -> pa.Table:
    return pa.Table.from_pylist(
        [{"document_id": document_id, "page_no": i + 1, "width": 612.0, "height": 792.0} for i in range(count)],
        schema=PAGE_SCHEMA,
    )


@pytest.fixture
def local_store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "home_path", str(tmp_path))
    monkeypatch.setattr(settings, "s3_endpoint", None)
    return LayoutStore.for_workspace(WORKSPACE)


class TestAddressing:
    def test_local_root_matches_where_the_local_file_client_puts_objects(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "home_path", str(tmp_path))
        monkeypatch.setattr(settings, "s3_endpoint", None)

        bucket, prefix = files.workspace_root(WORKSPACE)
        store = LayoutStore.for_workspace(WORKSPACE)

        # `{home_path}/{bucket}/{key}` is exactly LocalFileClient's object path.
        assert store.root_uri == f"{tmp_path}/{bucket}/{prefix}{LAYOUT_PREFIX}"
        assert store.items_uri().endswith(f"{LAYOUT_PREFIX}/{ITEMS_DATASET}.lance")

    def test_s3_root_matches_the_bucket_and_prefix_files_resolve(self, monkeypatch):
        monkeypatch.setattr(settings, "s3_endpoint", "http://localhost:9000")
        monkeypatch.setattr(settings, "s3_access_key", "minio")
        monkeypatch.setattr(settings, "s3_secret_key", "secret")

        bucket, prefix = files.workspace_root(WORKSPACE)
        store = LayoutStore.for_workspace(WORKSPACE)

        assert store.root_uri == f"s3://{bucket}/{prefix}{LAYOUT_PREFIX}"
        assert store.storage_options["allow_http"] == "true"

    def test_pdf_and_thumbnail_keys_share_the_layout_root(self, monkeypatch):
        # A later single-bucket mode must move every artifact of a workspace together.
        monkeypatch.setattr(settings, "s3_endpoint", "http://localhost:9000")
        monkeypatch.setattr(settings, "s3_access_key", "minio")
        monkeypatch.setattr(settings, "s3_secret_key", "secret")
        document_id = uuid4()

        bucket, prefix = files.workspace_root(WORKSPACE)
        store = LayoutStore.for_workspace(WORKSPACE)

        for key in (files.get_pdf_s3_object_path(document_id), files.get_thumbnail_s3_object_path(document_id)):
            assert store.root_uri.startswith(f"s3://{bucket}/{prefix}")
            assert not key.startswith("/")

    def test_the_resolver_agrees_with_the_bucket_files_addresses_today(self):
        # files.py still passes `Bucket=workspace_name`; the resolver must not silently disagree.
        assert files.workspace_root(WORKSPACE) == (WORKSPACE, "")


class TestReplace:
    def test_a_second_replace_leaves_one_vintage(self, local_store):
        document_id = str(uuid4())

        local_store.replace_document(document_id, items(document_id, 3), pages(document_id, 1))
        local_store.replace_document(document_id, items(document_id, 5), pages(document_id, 2))

        assert local_store.load_items(document_id).num_rows == 5
        assert local_store.load_pages(document_id).num_rows == 2

    def test_other_documents_are_untouched(self, local_store):
        keeper, replaced = str(uuid4()), str(uuid4())

        local_store.replace_document(keeper, items(keeper, 4), pages(keeper))
        local_store.replace_document(replaced, items(replaced, 2), pages(replaced))
        local_store.replace_document(replaced, items(replaced, 1), pages(replaced))

        assert local_store.load_items(keeper).num_rows == 4
        assert local_store.load_items(replaced).num_rows == 1

    def test_a_zero_row_document_still_clears_its_old_rows(self, local_store):
        document_id = str(uuid4())
        local_store.replace_document(document_id, items(document_id, 3), pages(document_id))

        empty_items = pa.Table.from_pylist([], schema=ITEM_SCHEMA)
        empty_pages = pa.Table.from_pylist([], schema=PAGE_SCHEMA)
        local_store.replace_document(document_id, empty_items, empty_pages)

        assert local_store.load_items(document_id).num_rows == 0
        assert local_store.load_pages(document_id).num_rows == 0

    def test_replace_reports_the_dataset_versions(self, local_store):
        document_id = str(uuid4())

        versions = local_store.replace_document(document_id, items(document_id), pages(document_id))

        assert versions["items_version"] >= 1
        assert versions["pages_version"] >= 1

    def test_concurrent_replaces_of_one_document_neither_lose_nor_duplicate_rows(self, local_store, monkeypatch):
        # Replacing is a delete commit then an append commit. Both writers are held at the append
        # until the other has passed its delete, which is exactly the interleaving that doubles
        # rows when the workspace lock is not held.
        document_id = str(uuid4())
        local_store.replace_document(document_id, items(document_id, 2), pages(document_id))
        original_write = LayoutStore._write
        arrivals = {"count": 0}
        counter_lock = threading.Lock()

        def synchronized_write(self, name, data, mode):
            if mode == "append" and name == ITEMS_DATASET:
                with counter_lock:
                    arrivals["count"] += 1
                deadline = time.monotonic() + 2.0
                while arrivals["count"] < 2 and time.monotonic() < deadline:
                    time.sleep(0.01)
            return original_write(self, name, data, mode)

        monkeypatch.setattr(LayoutStore, "_write", synchronized_write)
        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        def replace(count: int):
            store = LayoutStore.for_workspace(WORKSPACE)
            try:
                barrier.wait(timeout=30)
                with store.locked_sync():
                    store.replace_document(document_id, items(document_id, count), pages(document_id))
            except Exception as error:  # surfaced below; a raise here would be swallowed
                errors.append(error)

        threads = [threading.Thread(target=replace, args=(7,)) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert errors == []
        assert local_store.load_items(document_id).num_rows == 7


class TestDelete:
    def test_delete_removes_items_and_pages(self, local_store):
        document_id, other = str(uuid4()), str(uuid4())
        local_store.replace_document(document_id, items(document_id, 3), pages(document_id, 2))
        local_store.replace_document(other, items(other, 1), pages(other, 1))

        local_store.delete_document(document_id)

        assert local_store.load_items(document_id).num_rows == 0
        assert local_store.load_pages(document_id).num_rows == 0
        assert local_store.load_items(other).num_rows == 1

    def test_delete_on_a_missing_dataset_is_a_no_op(self, local_store):
        local_store.delete_document(str(uuid4()))


class TestReads:
    def test_missing_datasets_read_as_empty_tables_with_the_right_schema(self, local_store):
        table = local_store.load_items(str(uuid4()))

        assert table.num_rows == 0
        assert table.schema.names == ITEM_SCHEMA.names

    def test_projection_and_filter_are_pushed_down(self, local_store):
        document_id = str(uuid4())
        local_store.replace_document(document_id, items(document_id, 4), pages(document_id))

        table = local_store.load_items(document_id, columns=["self_ref", "page_no"], where="reading_order < 2")

        assert table.schema.names == ["self_ref", "page_no"]
        assert table.num_rows == 2

    def test_duckdb_views_aggregate_across_documents(self, local_store):
        first, second = str(uuid4()), str(uuid4())
        local_store.replace_document(first, items(first, 3, label="text"), pages(first))
        local_store.replace_document(second, items(second, 2, label="table"), pages(second))

        with duckdb_connection([WORKSPACE]) as connection:
            counts = dict(connection.execute("select label, count(*) from items group by label").fetchall())
            page_count = connection.execute("select count(*) from pages").fetchone()[0]

        assert counts == {"text": 3, "table": 2}
        assert page_count == 2

    def test_duckdb_views_exist_before_anything_is_written(self, local_store):
        with duckdb_connection([WORKSPACE]) as connection:
            assert connection.execute("select count(*) from items").fetchone()[0] == 0
            assert connection.execute("select count(*) from pages").fetchone()[0] == 0


class TestCompaction:
    def test_compaction_fires_past_the_threshold_and_preserves_rows(self, local_store, monkeypatch):
        monkeypatch.setattr("extralit_server.contexts.ocr.layout_store.COMPACT_FRAGMENT_THRESHOLD", 3)
        document_ids = [str(uuid4()) for _ in range(6)]
        for document_id in document_ids:
            local_store.replace_document(document_id, items(document_id, 2), pages(document_id))

        before = local_store.fragment_count(ITEMS_DATASET)
        local_store.maybe_compact()

        assert before > 3
        assert local_store.fragment_count(ITEMS_DATASET) < before
        for document_id in document_ids:
            assert local_store.load_items(document_id).num_rows == 2

    def test_a_broken_compaction_never_reaches_the_caller(self, local_store, monkeypatch):
        document_id = str(uuid4())
        local_store.replace_document(document_id, items(document_id), pages(document_id))
        monkeypatch.setattr(
            LayoutStore, "fragment_count", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        local_store.maybe_compact()
