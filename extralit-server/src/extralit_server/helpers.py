# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Common helper functions
"""

import hashlib
import io
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aioboto3
import aiofiles
import aiofiles.os
from botocore.exceptions import ClientError
from types_aiobotocore_s3.client import S3Client

from extralit_server.settings import settings

_LOGGER = logging.getLogger("extralit_server")
shared_resources = {}


def _compute_hash(data: bytes) -> str:
    """Compute MD5 hash for data."""
    return hashlib.md5(data).hexdigest()


class LocalFileClient(S3Client):
    """Local file storage implementation that mimics S3Client interface."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    async def _ensure_base_dir(self):
        """Ensure base directory exists."""
        await aiofiles.os.makedirs(self.base_dir, exist_ok=True)

    def _get_bucket_path(self, bucket_name: str) -> Path:
        """Get bucket directory path."""
        return self.base_dir / bucket_name

    def _get_object_path(self, bucket_name: str, key: str) -> Path:
        """Get object file path."""
        bucket_path = self._get_bucket_path(bucket_name)
        return bucket_path / key

    def _get_version_path(self, bucket_name: str, key: str) -> Path:
        """Get versions directory path for an object."""
        bucket_path = self._get_bucket_path(bucket_name)
        return bucket_path / ".versions" / key

    def _get_metadata_path(self, bucket_name: str, key: str) -> Path:
        """Get metadata file path for an object."""
        object_path = self._get_object_path(bucket_name, key)
        return object_path.with_suffix(object_path.suffix + ".metadata.json")

    async def create_bucket(self, Bucket: str, **kwargs) -> dict[str, Any]:
        """Create a bucket (directory)."""
        bucket_path = self._get_bucket_path(Bucket)
        await aiofiles.os.makedirs(bucket_path, exist_ok=True)
        # Create versions directory
        versions_path = bucket_path / ".versions"
        await aiofiles.os.makedirs(versions_path, exist_ok=True)
        return {}

    async def put_bucket_versioning(self, Bucket: str, VersioningConfiguration: dict, **kwargs) -> dict[str, Any]:
        """Enable bucket versioning (just ensure versions directory exists)."""
        bucket_path = self._get_bucket_path(Bucket)
        versions_path = bucket_path / ".versions"
        await aiofiles.os.makedirs(versions_path, exist_ok=True)
        return {}

    async def head_object(self, Bucket: str, Key: str, VersionId: str | None = None, **kwargs) -> dict[str, Any]:
        """Get object metadata."""
        try:
            if VersionId:
                version_path = self._get_version_path(Bucket, Key).with_suffix(f".{VersionId}")
                if not version_path.exists():
                    raise ClientError(
                        {"Error": {"Code": "NoSuchKey", "Message": "The specified version does not exist"}},
                        "HeadObject",
                    )
                file_path = version_path
            else:
                object_path = self._get_object_path(Bucket, Key)
                if not object_path.exists():
                    raise ClientError(
                        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}}, "HeadObject"
                    )
                file_path = object_path

            # Get file stats
            stat_result = await aiofiles.os.stat(file_path)

            # Get metadata
            metadata_path = self._get_metadata_path(Bucket, Key)
            if metadata_path.exists():
                async with aiofiles.open(metadata_path) as f:
                    metadata = json.loads(await f.read())
            else:
                metadata = {}

            return {
                "ContentLength": stat_result.st_size,
                "LastModified": datetime.fromtimestamp(stat_result.st_mtime),
                "ETag": f'"{metadata.get("etag", "")}"',
                "VersionId": VersionId or metadata.get("version_id"),
                "ContentType": metadata.get("content_type", "application/octet-stream"),
                "Metadata": metadata.get("metadata", {}),
            }

        except (FileNotFoundError, OSError):
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}}, "HeadObject"
            )

    async def get_object(
        self, Bucket: str, Key: str, VersionId: str | None = None, Range: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Get object content."""
        try:
            if VersionId:
                version_path = self._get_version_path(Bucket, Key).with_suffix(f".{VersionId}")
                if not version_path.exists():
                    raise ClientError(
                        {"Error": {"Code": "NoSuchKey", "Message": "The specified version does not exist"}}, "GetObject"
                    )
                file_path = version_path
            else:
                object_path = self._get_object_path(Bucket, Key)
                if not object_path.exists():
                    raise ClientError(
                        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}}, "GetObject"
                    )
                file_path = object_path

            # Read file content
            async with aiofiles.open(file_path, "rb") as f:
                if Range:
                    # Parse range like "bytes=0-1023"
                    range_match = Range.replace("bytes=", "").split("-")
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else None

                    await f.seek(start)
                    if end is not None:
                        content = await f.read(end - start + 1)
                    else:
                        content = await f.read()
                else:
                    content = await f.read()

            # Get metadata for response
            head_info = await self.head_object(Bucket, Key, VersionId)

            # Create a mock response body that can be read
            body = MockAsyncStreamingBody(content)

            return {
                "Body": body,
                "ContentLength": len(content),
                "LastModified": head_info["LastModified"],
                "ETag": head_info["ETag"],
                "ContentType": head_info["ContentType"],
                "VersionId": head_info.get("VersionId"),
                "Metadata": head_info.get("Metadata", {}),
            }

        except (FileNotFoundError, OSError):
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}}, "GetObject"
            )

    async def put_object(
        self,
        Bucket: str,
        Key: str,
        Body: Any,
        ContentType: str = "application/octet-stream",
        Metadata: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Put object to storage."""
        await self._ensure_base_dir()
        bucket_path = self._get_bucket_path(Bucket)
        await aiofiles.os.makedirs(bucket_path, exist_ok=True)

        # Convert body to bytes
        if hasattr(Body, "read"):
            if hasattr(Body, "seek"):
                Body.seek(0)
            data_bytes = Body.read()
        elif isinstance(Body, str):
            data_bytes = Body.encode("utf-8")
        else:
            data_bytes = Body

        # Generate version ID and hash
        content_hash = _compute_hash(data_bytes)
        version_id = str(uuid.uuid4())

        # Ensure versions directory exists
        version_dir = self._get_version_path(Bucket, Key).parent
        await aiofiles.os.makedirs(version_dir, exist_ok=True)

        # Write to version file
        version_path = self._get_version_path(Bucket, Key).with_suffix(f".{version_id}")
        async with aiofiles.open(version_path, "wb") as f:
            await f.write(data_bytes)

        # Update main object path (symlink or copy)
        object_path = self._get_object_path(Bucket, Key)
        await aiofiles.os.makedirs(object_path.parent, exist_ok=True)

        # Remove existing file/symlink
        if object_path.exists():
            await aiofiles.os.remove(object_path)

        # Create symlink to version file
        try:
            object_path.symlink_to(version_path)
        except OSError:
            # Fallback to copy if symlink fails
            async with aiofiles.open(version_path, "rb") as src, aiofiles.open(object_path, "wb") as dst:
                content = await src.read()
                await dst.write(content)

        # Save metadata
        metadata_info = {
            "etag": content_hash,
            "content_type": ContentType,
            "version_id": version_id,
            "metadata": Metadata or {},
        }

        metadata_path = self._get_metadata_path(Bucket, Key)
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata_info, default=str))

        return {
            "ETag": f'"{content_hash}"',
            "VersionId": version_id,
        }

    async def delete_object(self, Bucket: str, Key: str, VersionId: str | None = None, **kwargs) -> dict[str, Any]:
        """Delete object or specific version."""
        if VersionId:
            version_path = self._get_version_path(Bucket, Key).with_suffix(f".{VersionId}")
            if version_path.exists():
                await aiofiles.os.remove(version_path)
        else:
            object_path = self._get_object_path(Bucket, Key)
            if object_path.exists():
                await aiofiles.os.remove(object_path)

            # Remove metadata
            metadata_path = self._get_metadata_path(Bucket, Key)
            if metadata_path.exists():
                await aiofiles.os.remove(metadata_path)

        return {}

    async def list_objects_v2(
        self,
        Bucket: str,
        Prefix: str | None = None,
        Delimiter: str | None = None,
        StartAfter: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """List current objects in bucket."""
        bucket_path = self._get_bucket_path(Bucket)
        if not bucket_path.exists():
            return {"Contents": []}

        contents = []

        try:
            # Always search from bucket root and filter by prefix
            search_path = bucket_path

            if search_path.exists():
                # Use Path.rglob for recursive search (ignoring delimiter for now)
                files = [f for f in search_path.rglob("*") if f.is_file()]

                for file_path in files:
                    # Skip metadata files and version files
                    if file_path.name.endswith(".metadata.json") or ".versions" in str(
                        file_path.relative_to(bucket_path)
                    ):
                        continue

                    # Get the key relative to bucket path and normalize path separators
                    key = str(file_path.relative_to(bucket_path)).replace("\\", "/")

                    # Apply prefix filter (ensure prefix is normalized)
                    if Prefix:
                        normalized_prefix = Prefix.replace("\\", "/").rstrip("/")
                        if not key.startswith(normalized_prefix):
                            continue

                    # Apply start_after filter
                    if StartAfter and key <= StartAfter:
                        continue

                    try:
                        stat_result = await aiofiles.os.stat(file_path)

                        # Try to get metadata
                        metadata_path = self._get_metadata_path(Bucket, key)
                        etag = ""
                        if metadata_path.exists():
                            try:
                                async with aiofiles.open(metadata_path) as f:
                                    metadata = json.loads(await f.read())
                                    etag = metadata.get("etag", "")
                            except (json.JSONDecodeError, OSError):
                                # Ignore metadata read errors
                                pass

                        contents.append(
                            {
                                "Key": key,
                                "LastModified": datetime.fromtimestamp(stat_result.st_mtime),
                                "ETag": f'"{etag}"',
                                "Size": stat_result.st_size,
                            }
                        )
                    except (OSError, json.JSONDecodeError):
                        continue

        except OSError:
            pass

        # Sort by key
        contents.sort(key=lambda x: x["Key"])

        return {"Contents": contents}

    async def list_object_versions(
        self,
        Bucket: str,
        Prefix: str | None = None,
        Delimiter: str | None = None,
        KeyMarker: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """List all versions of objects."""
        bucket_path = self._get_bucket_path(Bucket)
        versions_path = bucket_path / ".versions"

        versions = []
        delete_markers = []

        if not versions_path.exists():
            return {"Versions": versions, "DeleteMarkers": delete_markers}

        try:
            # Find all version files
            for version_file in versions_path.rglob("*"):
                if not version_file.is_file():
                    continue

                # Parse version file name (key.version_id)
                relative_path = version_file.relative_to(versions_path)
                key_parts = str(relative_path).rsplit(".", 1)
                if len(key_parts) != 2:
                    continue

                key, version_id = key_parts

                # Apply prefix filter
                if Prefix and not key.startswith(Prefix):
                    continue

                # Apply key marker filter
                if KeyMarker and key <= KeyMarker:
                    continue

                try:
                    stat_result = await aiofiles.os.stat(version_file)

                    # Check if this is the latest version
                    current_object = self._get_object_path(Bucket, key)
                    is_latest = False
                    if current_object.exists():
                        # Get current version from metadata
                        metadata_path = self._get_metadata_path(Bucket, key)
                        if metadata_path.exists():
                            async with aiofiles.open(metadata_path) as f:
                                metadata = json.loads(await f.read())
                                is_latest = metadata.get("version_id") == version_id

                    # Get etag from version metadata (or compute from file)
                    etag = ""
                    version_metadata_path = version_file.with_suffix(version_file.suffix + ".metadata.json")
                    if version_metadata_path.exists():
                        async with aiofiles.open(version_metadata_path) as f:
                            metadata = json.loads(await f.read())
                            etag = metadata.get("etag", "")
                    else:
                        # Fallback: compute from file content
                        async with aiofiles.open(version_file, "rb") as f:
                            content = await f.read()
                            etag = _compute_hash(content)

                    versions.append(
                        {
                            "Key": key,
                            "VersionId": version_id,
                            "IsLatest": is_latest,
                            "LastModified": datetime.fromtimestamp(stat_result.st_mtime),
                            "ETag": f'"{etag}"',
                            "Size": stat_result.st_size,
                        }
                    )

                except (OSError, json.JSONDecodeError):
                    continue

        except OSError:
            pass

        # Sort by key and version
        versions.sort(key=lambda x: (x["Key"], x["LastModified"]), reverse=True)

        return {"Versions": versions, "DeleteMarkers": delete_markers}

    async def delete_bucket(self, Bucket: str, **kwargs) -> dict[str, Any]:
        """Delete bucket and all its contents."""
        bucket_path = self._get_bucket_path(Bucket)

        if bucket_path.exists():
            # Remove all files recursively
            import shutil

            shutil.rmtree(bucket_path)

        return {}

    async def generate_presigned_url(
        self, ClientMethod: str, Params: dict | None = None, ExpiresIn: int = 3600, **kwargs
    ) -> str:
        """Generate a presigned URL (return local file path for local storage)."""
        if not Params:
            return ""

        bucket = Params.get("Bucket", "")
        key = Params.get("Key", "")

        # For local files, return a proxy URL that matches the expected format
        return f"/api/v1/file/{bucket}/{key}"

    # Additional methods needed for compatibility
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockAsyncStreamingBody:
    """Mock streaming body for local file content."""

    def __init__(self, content: bytes, chunk_size: int = 8192):
        self._content = content
        self._stream = io.BytesIO(content)
        self._chunk_size = chunk_size
        self._position = 0

    async def read(self, amt: int | None = None) -> bytes:
        """Read content."""
        if amt is None:
            # For full reads, always return the complete content
            return self._content
        else:
            # For partial reads, use the stream position
            return self._stream.read(amt)

    def __aiter__(self):
        """Async iterator for streaming."""
        self._position = 0
        return self

    async def __anext__(self) -> bytes:
        """Return next chunk of data."""
        if self._position >= len(self._content):
            raise StopAsyncIteration

        chunk = self._content[self._position : self._position + self._chunk_size]
        self._position += len(chunk)
        return chunk

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def create_s3_client() -> "S3Client":
    """Initialize S3 client with settings configuration or LocalFileClient as fallback."""
    # Check if S3 is configured
    if not all([settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key]):
        # Use local file storage as fallback
        _LOGGER.info("S3 not configured, using local file storage at %s", settings.home_path)
        local_client = LocalFileClient(settings.home_path or os.path.expanduser("~/.extralit"))
        await local_client._ensure_base_dir()
        shared_resources["s3_client"] = local_client
        return local_client

    # Use real S3 client
    session = aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region or "us-east-1",
    )

    s3_client = await session.client(  # pyright: ignore[reportGeneralTypeIssues]
        "s3",
        endpoint_url=settings.s3_endpoint,
        use_ssl=settings.s3_endpoint.startswith("https://") if settings.s3_endpoint else True,
    ).__aenter__()

    shared_resources["s3_client"] = s3_client
    return s3_client


def remove_suffix(text: str, suffix: str):
    # TODO Move where is used
    """Give a text, removes suffix substring from it"""
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def replace_string_in_file(filename: str, string: str, replace_by: str, encoding: str = "utf-8"):
    # TODO Move where is used
    """Read a file and replace an old value in file by a new one"""
    # Safely read the input filename using 'with'
    with open(filename, encoding=encoding) as f:
        data = f.read()
        if string not in data:
            return

    # Safely write the changed content, if found in the file
    with open(filename, mode="w", encoding=encoding) as f:
        data = data.replace(string, replace_by)
        f.write(data)
