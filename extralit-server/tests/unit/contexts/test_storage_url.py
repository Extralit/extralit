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
