"""Tests for the per-document object layout and its cleanup."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage
from extralit_server.contexts.ocr.storage import layout_object_path

WORKSPACE = "ws1"
DOCUMENT_ID = "11111111-2222-3333-4444-555555555555"
PREFIX = f"documents/{DOCUMENT_ID}/"


@pytest.fixture
def storage(monkeypatch, tmp_path) -> ObjectStorage:
    monkeypatch.setattr(files.settings, "storage_url", tmp_path.as_uri())
    return ObjectStorage()


class TestPaths:
    def test_file_one_is_the_default(self):
        assert files.document_prefix(DOCUMENT_ID) == PREFIX
        assert files.get_original_s3_object_path(DOCUMENT_ID, "pdf") == PREFIX + "1_orig.pdf"
        assert files.get_ocr_pdf_s3_object_path(DOCUMENT_ID) == PREFIX + "1.pdf"
        assert files.get_docling_json_s3_object_path(DOCUMENT_ID) == PREFIX + "1.docling.json"
        assert files.get_thumbnail_s3_object_path(DOCUMENT_ID) == PREFIX + "thumbnail.png"
        assert layout_object_path(DOCUMENT_ID) == PREFIX + "1.docling.json"

    def test_paths_carry_the_file_index_and_extension(self):
        assert files.get_original_s3_object_path(DOCUMENT_ID, ".XLSX", index=2) == PREFIX + "2_orig.xlsx"
        assert files.get_ocr_pdf_s3_object_path(DOCUMENT_ID, index=3) == PREFIX + "3.pdf"
        assert files.get_docling_json_s3_object_path(DOCUMENT_ID, index=3) == PREFIX + "3.docling.json"
        assert layout_object_path(DOCUMENT_ID, index=2) == PREFIX + "2.docling.json"

    @pytest.mark.parametrize("index", [0, -1, 1.0, "1", True, None])
    def test_an_index_that_is_not_a_positive_integer_is_rejected(self, index):
        with pytest.raises(ValueError, match="positive integer"):
            files.get_ocr_pdf_s3_object_path(DOCUMENT_ID, index=index)
        with pytest.raises(ValueError, match="positive integer"):
            files.get_original_s3_object_path(DOCUMENT_ID, "pdf", index=index)

    @pytest.mark.parametrize("extension", ["", "tar.gz", "../x", "a" * 11])
    def test_a_malformed_extension_is_rejected(self, extension):
        with pytest.raises(ValueError, match="extension"):
            files.get_original_s3_object_path(DOCUMENT_ID, extension)

    def test_a_uuid_and_its_string_give_the_same_key(self):
        document_id = uuid4()
        assert files.get_ocr_pdf_s3_object_path(document_id) == files.get_ocr_pdf_s3_object_path(str(document_id))

    @pytest.mark.parametrize("bad", ["", None, "../other", "not-a-uuid"])
    def test_anything_but_a_uuid_is_rejected(self, bad):
        with pytest.raises(ValueError):
            files.document_prefix(bad)

    @pytest.mark.parametrize(
        ("name", "content_type"),
        [
            ("1_orig.pdf", "application/pdf"),
            ("1.pdf", "application/pdf"),
            ("1.docling.json", "application/json"),
            ("2_orig.csv", "text/csv"),
            ("thumbnail.png", "image/png"),
        ],
    )
    def test_content_type_comes_from_the_extension(self, name, content_type):
        assert files.content_type_of(PREFIX + name) == content_type


class TestSniffFileType:
    @pytest.mark.parametrize("name", ["paper.pdf", "paper", "paper.bin", None])
    def test_pdf_bytes_are_a_pdf_whatever_the_name(self, name):
        assert files.sniff_file_type(b"%PDF-1.7\n...", name) == ("pdf", "application/pdf")

    def test_a_pdf_header_after_leading_junk_is_found(self):
        assert files.sniff_file_type(b"\xef\xbb\xbf\n%PDF-1.4", "x.pdf")[0] == "pdf"

    def test_a_pdf_name_on_non_pdf_bytes_is_not_trusted(self):
        assert files.sniff_file_type(b"<html>", "fake.pdf") == ("bin", "application/octet-stream")

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Supplement.XLSX", ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("data.csv", ("csv", "text/csv")),
            ("notes.md", ("md", "text/markdown")),
            ("no-extension", ("bin", "application/octet-stream")),
            ("weird.ex$t", ("bin", "application/octet-stream")),
        ],
    )
    def test_other_types_come_from_the_name(self, name, expected):
        assert files.sniff_file_type(b"col1,col2\n", name) == expected


@pytest.mark.asyncio
class TestListDocumentFiles:
    async def test_originals_and_derived_files_are_grouped_by_index(self, storage):
        for name in ("1_orig.pdf", "1.pdf", "1.docling.json", "2_orig.xlsx", "thumbnail.png"):
            await files.put_object(storage, WORKSPACE, PREFIX + name, b"x")

        listed = await files.list_document_files(storage, WORKSPACE, DOCUMENT_ID)

        assert listed == {
            1: files.DocumentFile(
                index=1,
                original_key=PREFIX + "1_orig.pdf",
                extension="pdf",
                ocr_pdf_key=PREFIX + "1.pdf",
                docling_json_key=PREFIX + "1.docling.json",
            ),
            2: files.DocumentFile(index=2, original_key=PREFIX + "2_orig.xlsx", extension="xlsx"),
        }
        assert listed[1].is_pdf and not listed[2].is_pdf

    async def test_the_original_pdf_is_never_mistaken_for_the_processed_one(self, storage):
        await files.put_object(storage, WORKSPACE, PREFIX + "1_orig.pdf", b"x")

        listed = await files.list_document_files(storage, WORKSPACE, DOCUMENT_ID)

        assert listed[1].ocr_pdf_key is None

    async def test_names_with_bad_indexes_or_other_documents_are_ignored(self, storage):
        other = str(uuid4())
        for key in (
            PREFIX + "0_orig.pdf",
            PREFIX + "01_orig.pdf",
            PREFIX + "x_orig.pdf",
            PREFIX + "3.pdf",
            f"documents/{other}/1_orig.pdf",
        ):
            await files.put_object(storage, WORKSPACE, key, b"x")

        assert await files.list_document_files(storage, WORKSPACE, DOCUMENT_ID) == {}

    async def test_an_empty_document_lists_nothing(self, storage):
        assert await files.list_document_files(storage, WORKSPACE, DOCUMENT_ID) == {}


@pytest.mark.asyncio
class TestPutDocumentFile:
    async def test_the_upload_lands_at_its_index_and_sniffed_extension(self, storage):
        url = await files.put_document_file(storage, WORKSPACE, DOCUMENT_ID, b"a,b\n1,2\n", "table.CSV", index=2)

        assert url == f"/api/v1/file/{WORKSPACE}/{PREFIX}2_orig.csv"
        stored = await files.get_object(storage, WORKSPACE, PREFIX + "2_orig.csv")
        assert stored.metadata.content_type == "text/csv"


@pytest.mark.asyncio
class TestDeleteDocumentArtifacts:
    async def test_the_document_directory_is_removed_and_nothing_else(self, storage):
        other = str(uuid4())
        for document_id in (DOCUMENT_ID, other):
            prefix = files.document_prefix(document_id)
            for name in ("1_orig.pdf", "1.pdf", "1.docling.json", "2_orig.xlsx", "thumbnail.png"):
                await files.put_object(storage, WORKSPACE, prefix + name, b"x")

        with patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock()) as delete_layout:
            await files.delete_document_artifacts(storage, WORKSPACE, DOCUMENT_ID)

        remaining = [o.object_name for o in (await files.list_objects(storage, WORKSPACE)).objects]
        assert len(remaining) == 5 and all(key.startswith(files.document_prefix(other)) for key in remaining)
        assert not (storage.root.local_path / WORKSPACE / "documents" / DOCUMENT_ID).exists()
        assert delete_layout.await_args.args[1:] == (WORKSPACE, DOCUMENT_ID)

    async def test_a_failing_prefix_delete_still_drops_the_rows(self):
        with (
            patch.object(files, "delete_object_prefix", AsyncMock(side_effect=RuntimeError("gone"))),
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock()) as delete_layout,
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, uuid4())

        assert delete_layout.await_count == 1

    async def test_a_failing_row_delete_is_swallowed(self):
        with (
            patch.object(files, "delete_object_prefix", AsyncMock()),
            patch("extralit_server.contexts.ocr.storage.delete_layout", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            await files.delete_document_artifacts(AsyncMock(), WORKSPACE, uuid4())
