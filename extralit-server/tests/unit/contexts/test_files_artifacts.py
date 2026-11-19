"""Tests for the per-document object layout and its cleanup."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage
from extralit_server.contexts.ocr.storage import layout_object_path

WORKSPACE = "ws1"
DOCUMENT_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def storage(monkeypatch, tmp_path) -> ObjectStorage:
    monkeypatch.setattr(files.settings, "storage_url", tmp_path.as_uri())
    return ObjectStorage()


class TestPaths:
    def test_every_object_of_a_document_lives_in_its_directory(self):
        assert files.document_prefix(DOCUMENT_ID) == f"documents/{DOCUMENT_ID}/"
        assert files.get_pdf_s3_object_path(DOCUMENT_ID) == f"documents/{DOCUMENT_ID}/source.pdf"
        assert files.get_ocr_pdf_s3_object_path(DOCUMENT_ID) == f"documents/{DOCUMENT_ID}/ocr.pdf"
        assert files.get_docling_json_s3_object_path(DOCUMENT_ID) == f"documents/{DOCUMENT_ID}/docling.json"
        assert files.get_thumbnail_s3_object_path(DOCUMENT_ID) == f"documents/{DOCUMENT_ID}/thumbnail.png"
        assert layout_object_path(DOCUMENT_ID) == files.get_docling_json_s3_object_path(DOCUMENT_ID)

    def test_a_uuid_and_its_string_give_the_same_key(self):
        document_id = uuid4()
        assert files.get_pdf_s3_object_path(document_id) == files.get_pdf_s3_object_path(str(document_id))

    @pytest.mark.parametrize("bad", ["", None, "../other", "not-a-uuid"])
    def test_anything_but_a_uuid_is_rejected(self, bad):
        with pytest.raises(ValueError):
            files.document_prefix(bad)

    @pytest.mark.parametrize(
        ("name", "content_type"),
        [
            ("source.pdf", "application/pdf"),
            ("ocr.pdf", "application/pdf"),
            ("docling.json", "application/json"),
            ("thumbnail.png", "image/png"),
        ],
    )
    def test_content_type_comes_from_the_extension(self, name, content_type):
        assert files.content_type_of(files.document_prefix(DOCUMENT_ID) + name) == content_type


@pytest.mark.asyncio
class TestDeleteDocumentArtifacts:
    async def test_the_document_directory_is_removed_and_nothing_else(self, storage):
        other = str(uuid4())
        for document_id in (DOCUMENT_ID, other):
            for key in (
                files.get_pdf_s3_object_path(document_id),
                files.get_ocr_pdf_s3_object_path(document_id),
                files.get_docling_json_s3_object_path(document_id),
            ):
                await files.put_object(storage, WORKSPACE, key, b"x")

        with patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock()) as delete_rows:
            await files.delete_document_artifacts(storage, WORKSPACE, DOCUMENT_ID)

        remaining = [o.object_name for o in (await files.list_objects(storage, WORKSPACE)).objects]
        assert remaining and all(key.startswith(files.document_prefix(other)) for key in remaining)
        assert not (storage.root.local_path / WORKSPACE / "documents" / DOCUMENT_ID).exists()
        assert delete_rows.await_args.args[1:] == (WORKSPACE, DOCUMENT_ID)

    async def test_a_failing_prefix_delete_still_drops_the_rows(self):
        with (
            patch.object(files, "delete_object_prefix", AsyncMock(side_effect=RuntimeError("gone"))),
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock()) as delete_rows,
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, uuid4())

        assert delete_rows.await_count == 1

    async def test_a_failing_row_delete_is_swallowed(self):
        with (
            patch.object(files, "delete_object_prefix", AsyncMock()),
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, uuid4())
