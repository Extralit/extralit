"""Bucket lifecycle against a faked S3 admin client.

The drain is the part worth pinning: a legacy workspace bucket still carries
`Status: Enabled`, so a current-objects-only drain leaves noncurrent versions and delete
markers behind and `DeleteBucket` fails with `BucketNotEmpty`.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from extralit_server.contexts import buckets

BUCKET = "test-workspace"


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "op")


class FakeClient:
    """Just enough S3 admin surface for buckets.py, recording what it was asked to delete."""

    def __init__(self, pages=None, versioning="Enabled"):
        self._pages = pages if pages is not None else [{}]
        self._versioning = versioning
        self.deleted: list[dict] = []
        self.delete_calls = 0
        self.deleted_bucket: str | None = None
        self.versioning_set: str | None = None
        self.create_bucket = AsyncMock()
        self.head_bucket = AsyncMock()

    def get_paginator(self, name):
        assert name == "list_object_versions"
        pages = self._pages

        class _Paginator:
            def paginate(self, **kwargs):
                async def _gen():
                    for page in pages:
                        yield page

                return _gen()

        return _Paginator()

    async def delete_objects(self, Bucket, Delete):
        self.delete_calls += 1
        self.deleted.extend(Delete["Objects"])

    async def delete_bucket(self, Bucket):
        self.deleted_bucket = Bucket

    async def get_bucket_versioning(self, Bucket):
        return {"Status": self._versioning} if self._versioning else {}

    async def put_bucket_versioning(self, Bucket, VersioningConfiguration):
        self.versioning_set = VersioningConfiguration["Status"]


@asynccontextmanager
async def _yield(client):
    yield client


@pytest.fixture
def remote(monkeypatch):
    monkeypatch.setattr(buckets, "_remote", lambda: True)


@pytest.mark.asyncio
class TestDelete:
    async def test_it_deletes_noncurrent_versions_and_delete_markers(self, remote):
        client = FakeClient(
            pages=[
                {
                    "Versions": [
                        {"Key": "pdf/a", "VersionId": "v2"},
                        {"Key": "pdf/a", "VersionId": "v1"},
                    ],
                    "DeleteMarkers": [{"Key": "pdf/gone", "VersionId": "v3"}],
                }
            ]
        )

        with patch.object(buckets, "_client", lambda: _yield(client)):
            await buckets.delete(MagicMock(), BUCKET)

        assert client.deleted == [
            {"Key": "pdf/a", "VersionId": "v2"},
            {"Key": "pdf/a", "VersionId": "v1"},
            {"Key": "pdf/gone", "VersionId": "v3"},
        ]
        assert client.deleted_bucket == BUCKET

    async def test_an_unversioned_bucket_drains_through_the_same_path(self, remote):
        # Objects in a bucket that was never versioned come back as VersionId "null".
        client = FakeClient(pages=[{"Versions": [{"Key": "k.txt", "VersionId": "null"}]}])

        with patch.object(buckets, "_client", lambda: _yield(client)):
            await buckets.delete(MagicMock(), BUCKET)

        assert client.deleted == [{"Key": "k.txt", "VersionId": "null"}]
        assert client.deleted_bucket == BUCKET

    async def test_deletes_are_batched_under_the_thousand_key_cap(self, remote):
        page = {"Versions": [{"Key": f"k{i}", "VersionId": "null"} for i in range(2500)]}
        client = FakeClient(pages=[page])

        with patch.object(buckets, "_client", lambda: _yield(client)):
            await buckets.delete(MagicMock(), BUCKET)

        assert client.delete_calls == 3
        assert len(client.deleted) == 2500

    async def test_an_empty_bucket_is_still_deleted(self, remote):
        client = FakeClient(pages=[{}])

        with patch.object(buckets, "_client", lambda: _yield(client)):
            await buckets.delete(MagicMock(), BUCKET)

        assert client.deleted == []
        assert client.deleted_bucket == BUCKET

    async def test_a_missing_bucket_is_not_an_error(self, remote):
        client = FakeClient()
        client.get_paginator = MagicMock(side_effect=_client_error("NoSuchBucket"))

        with patch.object(buckets, "_client", lambda: _yield(client)):
            await buckets.delete(MagicMock(), BUCKET)

        assert client.deleted_bucket is None

    async def test_it_falls_back_when_the_backend_lacks_version_listing(self, remote):
        client = FakeClient()
        client.get_paginator = MagicMock(side_effect=_client_error("NotImplemented"))

        with (
            patch.object(buckets, "_client", lambda: _yield(client)),
            patch.object(buckets, "_drain_current_only", AsyncMock()) as fallback,
        ):
            await buckets.delete(MagicMock(), BUCKET)

        assert fallback.await_count == 1
        assert client.deleted_bucket == BUCKET


@pytest.mark.asyncio
class TestSuspendVersioning:
    async def test_an_enabled_bucket_is_suspended(self):
        client = FakeClient(versioning="Enabled")

        assert await buckets.suspend_versioning(client, BUCKET) is True
        assert client.versioning_set == "Suspended"

    async def test_an_unversioned_bucket_is_left_alone(self):
        client = FakeClient(versioning=None)

        assert await buckets.suspend_versioning(client, BUCKET) is False
        assert client.versioning_set is None

    async def test_a_backend_without_versioning_support_is_not_fatal(self):
        client = FakeClient()
        client.get_bucket_versioning = AsyncMock(side_effect=_client_error("NotImplemented"))

        assert await buckets.suspend_versioning(client, BUCKET) is False

    async def test_creating_over_a_legacy_bucket_suspends_it(self, remote):
        client = FakeClient(versioning="Enabled")
        client.create_bucket = AsyncMock(side_effect=_client_error("BucketAlreadyOwnedByYou"))

        with patch.object(buckets, "_client", lambda: _yield(client)):
            await buckets.create(MagicMock(), BUCKET)

        assert client.versioning_set == "Suspended"

    async def test_local_storage_has_nothing_to_normalize(self, monkeypatch):
        monkeypatch.setattr(buckets, "_remote", lambda: False)

        assert await buckets.normalize_versioning(MagicMock(), BUCKET) is False
