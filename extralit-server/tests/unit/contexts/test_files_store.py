"""End-to-end coverage of the object-storage port against a real `LocalStore`.

Every other test in the suite patches `contexts.files.*`, so until this module nothing
exercised a storage backend at all. `LocalStore` is real code rather than a mock, which is
the point of the obstore port: these assertions hold for `S3Store` too.
"""

import pytest
from fastapi import HTTPException

from extralit_server.contexts import files
from extralit_server.contexts.files import ObjectStorage

WORKSPACE = "test-workspace"


@pytest.fixture
def storage(monkeypatch, tmp_path) -> ObjectStorage:
    monkeypatch.setattr(files.settings, "storage_url", tmp_path.as_uri())
    return ObjectStorage()


@pytest.mark.asyncio
class TestRoundtrip:
    async def test_put_then_get_returns_the_body(self, storage):
        await files.put_object(storage, WORKSPACE, "a/b.txt", b"hello world", content_type="text/plain")

        file = await files.get_object(storage, WORKSPACE, "a/b.txt")

        assert bytes(await file.response.bytes_async()) == b"hello world"
        assert file.metadata.size == 11
        assert file.metadata.object_name == "a/b.txt"

    async def test_put_accepts_str_and_encodes_utf8(self, storage):
        await files.put_object(storage, WORKSPACE, "s.json", '{"k": "é"}', content_type="application/json")

        file = await files.get_object(storage, WORKSPACE, "s.json")

        assert bytes(await file.response.bytes_async()) == '{"k": "é"}'.encode()

    async def test_a_key_containing_dots_roundtrips(self, storage):
        # The client this replaced derived version paths with `Path.with_suffix`, which
        # silently truncated at the first dot: `pdf/a.b.pdf` came back as `pdf/a`.
        await files.put_object(storage, WORKSPACE, "pdf/a.b.pdf", b"%PDF-1.4")

        file = await files.get_object(storage, WORKSPACE, "pdf/a.b.pdf")

        assert file.metadata.object_name == "pdf/a.b.pdf"
        assert bytes(await file.response.bytes_async()) == b"%PDF-1.4"

    async def test_put_overwrites_in_place(self, storage):
        await files.put_object(storage, WORKSPACE, "k.txt", b"first")
        await files.put_object(storage, WORKSPACE, "k.txt", b"second")

        file = await files.get_object(storage, WORKSPACE, "k.txt")

        assert bytes(await file.response.bytes_async()) == b"second"


@pytest.mark.asyncio
class TestRanges:
    async def test_a_single_byte_range_returns_one_byte(self, storage):
        # An HTTP range is inclusive of its end, obstore's is exclusive. Off by one here
        # and `Range: bytes=0-0` returns nothing.
        await files.put_object(storage, WORKSPACE, "k.bin", b"0123456789")
        store = storage.for_workspace(WORKSPACE)

        result = await store.get_async("k.bin", options={"range": (0, 0 + 1)})

        assert bytes(result.bytes()) == b"0"

    async def test_a_range_reaching_the_last_byte(self, storage):
        await files.put_object(storage, WORKSPACE, "k.bin", b"0123456789")
        store = storage.for_workspace(WORKSPACE)

        result = await store.get_async("k.bin", options={"range": (5, 9 + 1)})

        assert bytes(result.bytes()) == b"56789"


@pytest.mark.asyncio
class TestListing:
    async def test_list_is_recursive_by_default(self, storage):
        for key in ("p/one.txt", "p/nested/two.txt", "other.txt"):
            await files.put_object(storage, WORKSPACE, key, b"x")

        listing = await files.list_objects(storage, WORKSPACE, prefix="p")

        assert {object.object_name for object in listing.objects} == {"p/one.txt", "p/nested/two.txt"}

    async def test_non_recursive_list_stops_at_the_delimiter(self, storage):
        for key in ("p/one.txt", "p/nested/two.txt"):
            await files.put_object(storage, WORKSPACE, key, b"x")

        listing = await files.list_objects(storage, WORKSPACE, prefix="p", recursive=False)

        assert {object.object_name for object in listing.objects} == {"p/one.txt"}

    async def test_listing_an_empty_prefix_is_not_an_error(self, storage):
        await files.put_object(storage, WORKSPACE, "k.txt", b"x")

        listing = await files.list_objects(storage, WORKSPACE, prefix="absent")

        assert list(listing.objects) == []


@pytest.mark.asyncio
class TestDeletion:
    async def test_delete_then_get_raises_404(self, storage):
        await files.put_object(storage, WORKSPACE, "k.txt", b"x")
        await files.delete_object(storage, WORKSPACE, "k.txt")

        with pytest.raises(HTTPException) as error:
            await files.get_object(storage, WORKSPACE, "k.txt")

        assert error.value.status_code == 404

    async def test_deleting_an_absent_key_is_a_no_op(self, storage):
        await files.delete_object(storage, WORKSPACE, "never/existed.txt")

    async def test_a_deleted_object_leaves_the_listing(self, storage):
        # The delete-marker model this replaced kept returning deleted keys from listings.
        await files.put_object(storage, WORKSPACE, "p/k.txt", b"x")
        await files.delete_object(storage, WORKSPACE, "p/k.txt")

        listing = await files.list_objects(storage, WORKSPACE, prefix="p")

        assert list(listing.objects) == []


@pytest.mark.asyncio
class TestContentType:
    async def test_it_is_derived_from_the_key_extension(self, storage):
        await files.put_object(storage, WORKSPACE, "a/b.txt", b"x", content_type="text/plain")

        file = await files.get_object(storage, WORKSPACE, "a/b.txt")

        assert file.metadata.content_type == "text/plain"

    async def test_extensionless_minted_keys_fall_back_to_their_prefix(self, storage):
        # `pdf/{id}` and `thumbnails/{id}` carry no extension, and LocalStore cannot persist
        # attributes, so the prefix map is the only thing standing between a local-dev PDF
        # and being served as application/octet-stream.
        await files.put_object(storage, WORKSPACE, "pdf/some-uuid", b"%PDF-1.4", content_type="application/pdf")

        file = await files.get_object(storage, WORKSPACE, "pdf/some-uuid")

        assert file.metadata.content_type == "application/pdf"

    async def test_an_unknown_key_defaults_to_octet_stream(self, storage):
        await files.put_object(storage, WORKSPACE, "mystery", b"x")

        file = await files.get_object(storage, WORKSPACE, "mystery")

        assert file.metadata.content_type == "application/octet-stream"


@pytest.mark.asyncio
class TestDocumentUrls:
    async def test_download_file_content_reads_the_whole_body(self, storage):
        await files.put_object(storage, WORKSPACE, "pdf/doc-1", b"%PDF-1.4 body")
        url = files.get_proxy_document_url(WORKSPACE, "pdf/doc-1")

        assert await files.download_file_content(storage, url) == b"%PDF-1.4 body"

    async def test_a_malformed_url_is_rejected(self, storage):
        with pytest.raises(ValueError):
            await files.download_file_content(storage, "https://example.com/not-a-proxy-url")

    async def test_local_storage_cannot_presign_so_it_keeps_the_proxy_url(self, storage):
        url = files.get_proxy_document_url(WORKSPACE, "pdf/doc-1")

        assert await files.get_presigned_url_from_document_url(storage, url, expires=60) == url


@pytest.mark.asyncio
class TestPutDocumentFile:
    async def test_the_first_upload_returns_a_proxy_url(self, storage):
        from uuid import uuid4

        url = await files.put_document_file(storage, WORKSPACE, uuid4(), b"%PDF-1.4", "a.pdf")

        assert url is not None
        assert url.startswith(f"/api/v1/file/{WORKSPACE}/pdf/")


@pytest.mark.asyncio
class TestWorkspacePrefix:
    async def test_objects_land_under_the_workspace_directory(self, storage, tmp_path):
        await files.put_object(storage, WORKSPACE, "pdf/x", b"1")

        assert (tmp_path / WORKSPACE / "pdf" / "x").read_bytes() == b"1"

    async def test_delete_workspace_objects_removes_only_that_workspace(self, storage, tmp_path):
        await files.put_object(storage, WORKSPACE, "pdf/x", b"1")
        await files.put_object(storage, "other", "pdf/y", b"2")

        await files.delete_workspace_objects(storage, WORKSPACE)

        assert not (tmp_path / WORKSPACE).exists()
        assert (tmp_path / "other" / "pdf" / "y").exists()
