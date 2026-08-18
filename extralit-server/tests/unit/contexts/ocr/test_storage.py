"""Tests for the layout artifacts written per document."""

from unittest.mock import AsyncMock, patch

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size

from extralit_server.contexts.ocr import storage
from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, append_blocks, new_document
from extralit_server.contexts.ocr.layout_store import LayoutStore

DOCUMENT_ID = "11111111-2222-3333-4444-555555555555"
WORKSPACE = "ws1"

pytestmark = pytest.mark.asyncio


@pytest.fixture
def doc():
    document = new_document("sample")
    ctx = PageContext(page_no=1, size=Size(width=612, height=792))
    append_blocks(
        document,
        ctx,
        [
            LayoutBlock(
                label=DocItemLabel.TEXT,
                bbox=BoundingBox(l=10, t=10, r=100, b=30, coord_origin=CoordOrigin.TOPLEFT),
                text="Body",
            )
        ],
    )
    return document


@pytest.fixture
def store(tmp_path):
    layout_store = LayoutStore(str(tmp_path / WORKSPACE / "layout"))
    with patch.object(storage.LayoutStore, "for_workspace", return_value=layout_store):
        yield layout_store


class TestStoreLayout:
    async def test_writes_canonical_json_and_returns_lance_uris(self, doc, store):
        with patch.object(storage.files, "put_object", AsyncMock()) as put_object:
            paths = await storage.store_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID, doc)

        assert paths["layout_url"] == f"layout/{DOCUMENT_ID}.docling.json"
        assert paths["items_uri"] == store.items_uri()
        assert paths["pages_uri"] == store.pages_uri()
        assert paths["items_version"] == 1 and paths["pages_version"] == 1
        assert put_object.await_count == 1
        assert put_object.await_args.kwargs["content_type"] == "application/json"

    async def test_rows_land_in_the_workspace_datasets(self, doc, store):
        with patch.object(storage.files, "put_object", AsyncMock()):
            await storage.store_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID, doc)

        assert store.load_items(DOCUMENT_ID).num_rows == 1
        assert store.load_pages(DOCUMENT_ID).num_rows == 1

    async def test_a_caller_holding_the_lock_can_pass_its_own_store(self, doc, store):
        with patch.object(storage.files, "put_object", AsyncMock()):
            async with store.locked():
                await storage.store_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID, doc, store=store)

        assert store.load_items(DOCUMENT_ID).num_rows == 1


class TestDeleteLayout:
    async def test_removes_json_and_rows(self, doc, store):
        with patch.object(storage.files, "put_object", AsyncMock()):
            await storage.store_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID, doc)

        with patch.object(storage.files, "delete_object", AsyncMock()) as delete_object:
            await storage.delete_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID)

        assert delete_object.await_args.args[2] == f"layout/{DOCUMENT_ID}.docling.json"
        assert store.load_items(DOCUMENT_ID).num_rows == 0

    async def test_survives_a_missing_object(self, store):
        with patch.object(storage.files, "delete_object", AsyncMock(side_effect=RuntimeError("gone"))):
            await storage.delete_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID)

    async def test_survives_a_failing_dataset(self, store):
        with (
            patch.object(storage.files, "delete_object", AsyncMock()),
            patch.object(LayoutStore, "delete_document", side_effect=RuntimeError("lance down")),
        ):
            await storage.delete_layout(AsyncMock(), WORKSPACE, DOCUMENT_ID)
