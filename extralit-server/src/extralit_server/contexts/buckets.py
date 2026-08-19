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
    except ClientError as e:
        _LOGGER.error(f"Error creating bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating bucket: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def delete(storage: ObjectStorage, workspace_name: str) -> None:
    """Drain the workspace's bucket and delete it."""
    bucket, _prefix = workspace_root(workspace_name)

    if not _remote():
        shutil.rmtree(_local_root(bucket), ignore_errors=True)
        return

    store = storage.store_for(bucket)
    try:
        listing = await list_objects(storage, bucket)
    except HTTPException:
        return  # No such bucket; nothing to drain or delete.

    for object in listing.objects:
        try:
            await store.delete_async(object.object_name)
        except Exception as remove_err:
            _LOGGER.warning(f"Error removing object {object.object_name} during bucket delete: {remove_err}")

    try:
        async with _client() as client:
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
