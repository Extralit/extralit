from pathlib import Path

import pytest
from obstore.store import LocalStore, S3Store

from extralit_server.contexts.files import ObjectStorage
from extralit_server.settings import parse_storage_url, settings


class TestParseStorageUrl:
    def test_file_url_is_a_local_root(self):
        root = parse_storage_url("file:///var/lib/extralit/storage")

        assert not root.remote
        assert root.local_path == Path("/var/lib/extralit/storage")

    def test_s3_url_splits_bucket_and_prefix(self):
        root = parse_storage_url("s3://extralit/prod/")

        assert (root.endpoint, root.bucket, root.prefix) == (None, "extralit", "prod")

    def test_http_url_keeps_host_and_port_as_the_endpoint(self):
        root = parse_storage_url("http://minio:9000/extralit/a/b")

        assert (root.endpoint, root.bucket, root.prefix) == ("http://minio:9000", "extralit", "a/b")

    def test_r2_url(self):
        root = parse_storage_url("https://acct.r2.cloudflarestorage.com/extralit")

        assert (root.endpoint, root.bucket, root.prefix) == ("https://acct.r2.cloudflarestorage.com", "extralit", "")

    @pytest.mark.parametrize("url", ["http://minio:9000", "http://minio:9000/", "s3://", "ftp://x/y"])
    def test_missing_bucket_or_unknown_scheme_is_rejected(self, url):
        with pytest.raises(ValueError):
            parse_storage_url(url)


class TestObjectStorage:
    def test_local_store_is_rooted_at_the_workspace_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "storage_url", tmp_path.as_uri())

        store = ObjectStorage().for_workspace("ws")

        assert isinstance(store, LocalStore)
        assert store.prefix == tmp_path / "ws"
        assert (tmp_path / "ws").is_dir()

    def test_s3_store_is_prefixed_with_root_prefix_and_workspace(self, monkeypatch):
        monkeypatch.setattr(settings, "storage_url", "http://minio:9000/extralit/prod")
        monkeypatch.setattr(settings, "s3_access_key", "k")
        monkeypatch.setattr(settings, "s3_secret_key", "s")

        store = ObjectStorage().for_workspace("ws")

        assert isinstance(store, S3Store)
        assert store.prefix == "prod/ws"
        assert store.config["endpoint"] == "http://minio:9000"
        assert str(store.client_options["allow_http"]).lower() == "true"

    def test_keys_are_omitted_so_obstore_uses_its_own_credential_chain(self, monkeypatch):
        monkeypatch.setattr(settings, "storage_url", "s3://extralit")
        monkeypatch.setattr(settings, "s3_access_key", None)
        monkeypatch.setattr(settings, "s3_secret_key", None)

        storage = ObjectStorage()

        assert "access_key_id" not in storage._s3_config()
        assert "aws_access_key_id" not in storage.lance_storage_options()
        assert storage.lance_uri("ws", "layout") == "s3://extralit/ws/layout"


@pytest.mark.asyncio
class TestGuards:
    def test_a_percent_encoded_local_path_is_decoded(self):
        # `Path.as_uri()` escapes spaces, and that is how the default is built.
        root = parse_storage_url("file:///home/a%20user/.extralit/storage")

        assert root.local_path == Path("/home/a user/.extralit/storage")

    @pytest.mark.parametrize("url", ["http://key:secret@minio:9000/b", "https://key@host/b"])
    def test_credentials_in_the_url_are_rejected_without_echoing_them(self, url):
        with pytest.raises(ValueError) as error:
            parse_storage_url(url)

        assert "secret" not in str(error.value)
        assert "EXTRALIT_S3_ACCESS_KEY" in str(error.value)

    @pytest.mark.parametrize("workspace", ["", "..", ".", "../escape", "a/b", "..\\escape"])
    def test_a_workspace_that_could_escape_the_root_is_rejected(self, workspace, tmp_path, monkeypatch):
        # LocalStore accepts `..` in a prefix where S3Store rejects it, and the name reaches
        # here straight from a URL path segment.
        monkeypatch.setattr(settings, "storage_url", tmp_path.as_uri())

        with pytest.raises(ValueError):
            ObjectStorage().for_workspace(workspace)

    async def test_healthy_creates_a_local_root_that_does_not_exist_yet(self, tmp_path, monkeypatch):
        root = tmp_path / "storage"
        monkeypatch.setattr(settings, "storage_url", root.as_uri())

        assert await ObjectStorage().healthy() is True
        assert root.is_dir()

    async def test_healthy_is_false_when_the_local_root_cannot_be_created(self, tmp_path, monkeypatch):
        blocker = tmp_path / "file"
        blocker.write_bytes(b"")
        monkeypatch.setattr(settings, "storage_url", (blocker / "storage").as_uri())

        assert await ObjectStorage().healthy() is False
