"""Bucket lifecycle, the one thing obstore cannot do.

An obstore store binds to an existing bucket and exposes no admin API, so CreateBucket /
DeleteBucket / HeadBucket stay on aioboto3. This module is the whole of that surface; everything
else in the object-storage path goes through `contexts.files`.
"""

import logging
import shutil
from pathlib import Path

import aioboto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

from extralit_server.contexts.files import ObjectStorage, list_objects, workspace_root
from extralit_server.settings import settings

_LOGGER = logging.getLogger(__name__)

# DeleteObjects caps one request at 1000 keys.
_DELETE_BATCH = 1000


def _remote() -> bool:
    return all([settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key])


def _local_root(bucket: str) -> Path:
    return Path(settings.home_path) / bucket


def _client():
    endpoint = settings.s3_endpoint or ""
    session = aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region or "us-east-1",
    )
    return session.client("s3", endpoint_url=endpoint, use_ssl=endpoint.startswith("https://"))


async def exists(storage: ObjectStorage, workspace_name: str) -> bool:
    """Check whether the workspace's bucket exists."""
    bucket, _prefix = workspace_root(workspace_name)

    if not _remote():
        return _local_root(bucket).is_dir()

    try:
        async with _client() as client:
            await client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ["404", "NoSuchBucket"]:
            return False
        # For other errors (like permissions), log and return False
        _LOGGER.warning(f"Error checking bucket {bucket}: {e}")
        return False
    except Exception as e:
        _LOGGER.warning(f"Unexpected error checking bucket {bucket}: {e}")
        return False


async def create(storage: ObjectStorage, workspace_name: str) -> None:
    """Create the workspace's bucket if it does not already exist."""
    bucket, _prefix = workspace_root(workspace_name)

    if not _remote():
        _local_root(bucket).mkdir(parents=True, exist_ok=True)
        return

    try:
        async with _client() as client:
            try:
                await client.create_bucket(Bucket=bucket)
            except ClientError as e:
                if e.response["Error"]["Code"] not in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
                    raise
                # Pre-dates the removal of object versioning, so it may still be Enabled.
                await suspend_versioning(client, bucket)
    except ClientError as e:
        _LOGGER.error(f"Error creating bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating bucket: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def suspend_versioning(client, bucket: str) -> bool:
    """Stop a legacy bucket from minting new object versions. True if it was Enabled.

    Buckets created before versioning was removed still carry `Status: Enabled`, and the
    lifecycle rule that expired their noncurrent layout versions went away with it -- so every
    layout rewrite would grow the bucket with nothing reaping it. Suspending is the migration;
    existing noncurrent versions stay until the bucket is drained or deleted.
    """
    try:
        current = await client.get_bucket_versioning(Bucket=bucket)
        if current.get("Status") != "Enabled":
            return False

        await client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Suspended"})
        _LOGGER.info(f"Suspended object versioning on legacy bucket {bucket}")
        return True
    except ClientError as e:
        # A backend without versioning support never had the problem in the first place.
        _LOGGER.warning(f"Could not suspend versioning on bucket {bucket}: {e}")
        return False


async def normalize_versioning(storage: ObjectStorage, workspace_name: str) -> bool:
    """Suspend versioning on the workspace's bucket if it is still Enabled. True if it changed."""
    bucket, _prefix = workspace_root(workspace_name)

    if not _remote():
        return False

    async with _client() as client:
        return await suspend_versioning(client, bucket)


async def _drain_every_version(client, bucket: str) -> None:
    """Delete every object version and delete marker in the bucket.

    A current-objects-only drain leaves the noncurrent versions and delete markers of a legacy
    versioned bucket behind, and `DeleteBucket` then fails with `BucketNotEmpty`. Objects in an
    unversioned bucket come back with `VersionId: "null"`, which is a valid delete target, so
    this one path covers both.
    """
    paginator = client.get_paginator("list_object_versions")
    async for page in paginator.paginate(Bucket=bucket):
        targets = [
            {"Key": entry["Key"], "VersionId": entry["VersionId"]}
            for section in ("Versions", "DeleteMarkers")
            for entry in page.get(section, [])
        ]
        for start in range(0, len(targets), _DELETE_BATCH):
            await client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": targets[start : start + _DELETE_BATCH], "Quiet": True},
            )


async def _drain_current_only(storage: ObjectStorage, bucket: str) -> None:
    """Fallback drain for a backend that does not implement ListObjectVersions."""
    store = storage.store_for(bucket)
    try:
        listing = await list_objects(storage, bucket)
    except HTTPException:
        return

    for object in listing.objects:
        try:
            await store.delete_async(object.object_name)
        except Exception as remove_err:
            _LOGGER.warning(f"Error removing object {object.object_name} during bucket delete: {remove_err}")


async def delete(storage: ObjectStorage, workspace_name: str) -> None:
    """Drain the workspace's bucket and delete it."""
    bucket, _prefix = workspace_root(workspace_name)

    if not _remote():
        shutil.rmtree(_local_root(bucket), ignore_errors=True)
        return

    try:
        async with _client() as client:
            try:
                await _drain_every_version(client, bucket)
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == "NoSuchBucket":
                    return  # Nothing to drain or delete.
                if code != "NotImplemented":
                    raise
                await _drain_current_only(storage, bucket)

            await client.delete_bucket(Bucket=bucket)
        _LOGGER.info(f"Successfully deleted bucket: {bucket}")
    except ClientError as e:
        if e.response["Error"]["Code"] in ["NoSuchBucket", "NotImplemented"]:
            pass  # Bucket doesn't exist, that's fine
        else:
            _LOGGER.error(f"Error deleting S3 bucket {bucket}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting bucket: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error deleting S3 bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")
