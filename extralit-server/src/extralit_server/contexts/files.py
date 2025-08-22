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

import hashlib
import io
import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException
from minio import Minio, S3Error
from minio.commonconfig import ENABLED
from minio.datatypes import Object
from minio.helpers import ObjectWriteResult
from minio.versioningconfig import VersioningConfig
from urllib3 import HTTPResponse

from extralit_server.api.schemas.v1.files import FileObjectResponse, ListObjectsResponse, ObjectMetadata
from extralit_server.settings import settings

EXCLUDED_VERSIONING_PREFIXES = ["pdf"]

_LOGGER = logging.getLogger(__name__)

# Singleton instances
_minio_client: Union[Minio, "LocalFileStorage"] | None = None
_local_storage_client: Optional["LocalFileStorage"] = None


def _create_minio_client() -> Union[Minio, "LocalFileStorage"]:
    """Create a new Minio client instance."""
    if None in [settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key]:
        # Use local file system storage if S3 settings are not provided
        local_storage_path = os.path.join(settings.home_path, "storage")  # type: ignore
        _LOGGER.info(f"Using local file storage at: {local_storage_path}")
        return LocalFileStorage(local_storage_path)

    try:
        parsed_url = urlparse(settings.s3_endpoint)
        hostname: str = str(parsed_url.hostname)
        port = parsed_url.port

        if hostname is None:
            raise ValueError("S3 endpoint hostname is required")

        return Minio(
            endpoint=f"{hostname}:{port}" if port else hostname,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
            secure=parsed_url.scheme == "https",
        )
    except Exception as e:
        _LOGGER.error(f"Error creating Minio client: {e}", stack_info=True)
        raise e


def get_minio_client() -> Union[Minio, "LocalFileStorage"]:
    """Get a singleton Minio client instance."""
    global _minio_client

    if _minio_client is None:
        _minio_client = _create_minio_client()

    return _minio_client


async def get_async_minio_client() -> Union[Minio, "LocalFileStorage"]:
    """Get a singleton Minio client instance for async operations."""
    # For now, return the sync client since Minio client operations are blocking
    # In the future, you could implement an async wrapper or use aioboto3 for S3
    return get_minio_client()


def reset_minio_client():
    """Reset the singleton Minio client (useful for testing or reconnection)."""
    global _minio_client
    _minio_client = None


class LocalFileStorage:
    """Local file storage implementation that mimics Minio client interface."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_bucket_path(self, bucket_name: str) -> Path:
        bucket_path = self.base_dir / bucket_name
        return bucket_path

    def _get_object_path(self, bucket_name: str, object_name: str) -> Path:
        bucket_path = self._get_bucket_path(bucket_name)
        object_path = bucket_path / object_name
        return object_path

    def _get_version_path(self, bucket_name: str, object_name: str) -> Path:
        bucket_path = self._get_bucket_path(bucket_name)
        version_path = bucket_path / ".versions" / object_name
        return version_path

    def make_bucket(self, bucket_name: str) -> None:
        bucket_path = self._get_bucket_path(bucket_name)
        bucket_path.mkdir(parents=True, exist_ok=True)
        # Create versions directory
        (bucket_path / ".versions").mkdir(exist_ok=True)

    def set_bucket_versioning(self, bucket_name: str, config: Any) -> None:
        # Just create the versions directory
        bucket_path = self._get_bucket_path(bucket_name)
        (bucket_path / ".versions").mkdir(exist_ok=True)

    def bucket_exists(self, bucket_name: str) -> bool:
        bucket_path = self._get_bucket_path(bucket_name)
        return bucket_path.exists() and bucket_path.is_dir()

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO | bytes,
        length: int | None = None,
        content_type: str | None = None,
        part_size: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ObjectWriteResult:
        # Ensure bucket exists
        bucket_path = self._get_bucket_path(bucket_name)
        bucket_path.mkdir(parents=True, exist_ok=True)

        if not isinstance(data, bytes):
            data_bytes = data.read()
        else:
            data_bytes = data

        # Generate content-based version ID and ETag
        content_hash = compute_hash(data_bytes)
        version_id = str(uuid.uuid4())

        version_path = self._get_version_path(bucket_name, object_name).with_suffix(f".{version_id}")
        version_path.parent.mkdir(parents=True, exist_ok=True)

        # Write data to version file
        with open(version_path, "wb") as f:
            f.write(data_bytes)

        object_path = self._get_object_path(bucket_name, object_name)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            object_path.unlink()  # Remove existing file/symlink
        object_path.symlink_to(version_path)

        # Always write metadata with content hash
        meta_path = object_path.with_suffix(".metadata.json")
        metadata = metadata or {}
        metadata.update(
            {"etag": content_hash, "content_type": content_type or "application/octet-stream", "version_id": version_id}
        )
        with open(meta_path, "w") as f:
            json.dump(metadata, f)

        return ObjectWriteResult(
            bucket_name=bucket_name,
            object_name=object_name,
            version_id=version_id,
            etag=content_hash,
            http_headers={},  # type: ignore
            last_modified=None,
            location=None,
        )

    def get_object(self, bucket_name: str, object_name: str, version_id: str | None = None) -> HTTPResponse:
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f".{version_id}")
            if not version_path.exists():
                raise S3Error("NoSuchKey", "The specified version does not exist", object_name, "", "", None)
            with open(version_path, "rb") as f:
                content = f.read()
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if not object_path.exists():
                raise S3Error("NoSuchKey", "The specified key does not exist", object_name, "", "", None)
            with open(object_path, "rb") as f:
                content = f.read()

        # The metadata is not needed for the HTTPResponse, but kept for consistency
        # with the original implementation's metadata fetching.
        meta_path = self._get_object_path(bucket_name, object_name).with_suffix(".metadata.json")
        if not meta_path.exists():
            raise S3Error("NoSuchKey", "The specified key does not exist", object_name, "", "", None)
        with open(meta_path) as f:
            json.load(f)

        return HTTPResponse(body=io.BytesIO(content), preload_content=False)  # type: ignore

    def stat_object(self, bucket_name: str, object_name: str, version_id: str | None = None) -> ObjectMetadata:
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f".{version_id}")
            if not version_path.exists():
                raise S3Error("NoSuchKey", "The specified version does not exist", object_name, "", "", None)
            path = version_path
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if not object_path.exists():
                raise S3Error("NoSuchKey", "The specified key does not exist", object_name, "", "", None)
            path = object_path

        # Get metadata from file
        meta_path = self._get_object_path(bucket_name, object_name).with_suffix(".metadata.json")
        if not meta_path.exists():
            raise S3Error("NoSuchKey", "The specified key does not exist", object_name, "", "", None)

        with open(meta_path) as f:
            metadata = json.load(f)

        stats = path.stat()

        return ObjectMetadata(
            bucket_name=bucket_name,
            object_name=object_name,
            version_id=version_id or metadata.get("version_id"),
            etag=metadata.get("etag"),
            size=stats.st_size,
            last_modified=datetime.fromtimestamp(stats.st_mtime),
            metadata=metadata,
            content_type=metadata.get("content_type", "application/octet-stream"),
        )

    def remove_object(self, bucket_name: str, object_name: str, version_id: str | None = None):
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f".{version_id}")
            if version_path.exists():
                version_path.unlink()
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if object_path.exists():
                object_path.unlink()

                # Remove metadata if exists
                meta_path = object_path.with_suffix(".metadata.json")
                if meta_path.exists():
                    meta_path.unlink()

    def list_objects(
        self,
        bucket_name: str,
        prefix: str | None = None,
        recursive: bool = False,
        include_version: bool = False,
        start_after: str | None = None,
    ) -> list[ObjectMetadata]:
        bucket_path = self._get_bucket_path(bucket_name)
        if not bucket_path.exists():
            _LOGGER.warning(
                f"LocalFileStorage: Bucket {bucket_name} did not exist, created new bucket at {bucket_path}"
            )
            self.make_bucket(bucket_name)

        pattern = "**/*" if recursive else "*"
        files = list(bucket_path.glob(pattern))

        if prefix:
            files = [f for f in files if str(f.relative_to(bucket_path)).startswith(prefix)]

        files = [
            f for f in files if f.is_file() and not f.name.endswith(".metadata.json") and ".versions" not in str(f)
        ]

        files.sort()

        if start_after:
            files = [f for f in files if str(f.relative_to(bucket_path)) > start_after]

        result = []
        for file_path in files:
            object_name = str(file_path.relative_to(bucket_path))
            stats = file_path.stat()

            # Get metadata from file
            meta_path = file_path.with_suffix(".metadata.json")
            if not meta_path.exists():
                continue  # Skip objects without metadata

            with open(meta_path) as f:
                metadata = json.load(f)

            obj = ObjectMetadata(
                bucket_name=bucket_name,
                object_name=object_name,
                etag=metadata.get("etag"),
                size=stats.st_size,
                last_modified=datetime.fromtimestamp(stats.st_mtime),
                metadata=metadata,
                content_type=metadata.get("content_type", "application/octet-stream"),
                version_id=metadata.get("version_id") if include_version else None,
            )

            result.append(obj)

        return result


def compute_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def get_pdf_s3_object_path(id: UUID | str) -> str:
    if not id:
        raise Exception("id cannot be None")

    elif isinstance(id, UUID):
        object_path = f"pdf/{id!s}"
    else:
        object_path = f"pdf/{id}"

    return object_path


def get_proxy_document_url(bucket_name: str, object_path: str) -> str:
    return f"/api/v1/file/{bucket_name}/{object_path}"


def get_presigned_url_from_document_url(
    client: Minio | LocalFileStorage, document_url: str, expires: int = 3600
) -> str:
    """
    Generate a presigned URL from a document URL by parsing the bucket_name and object_path.

    Args:
        document_url: URL in format "/api/v1/file/{bucket_name}/{object_path}"
        expires: Expiration time in seconds (default: 1 hour)

    Returns:
        Presigned URL if successful, None if parsing fails or client is not Minio
    """
    if not isinstance(client, Minio):
        return document_url

    try:
        # Parse the URL to extract bucket_name and object_path
        # Expected format: "/api/v1/file/{bucket_name}/{object_path}"
        if not document_url.startswith("/api/v1/file/"):
            _LOGGER.warning(f"Invalid document URL format: {document_url}")
            return document_url

        path_parts = document_url[13:].split("/", 1)  # 13 = len("/api/v1/file/")
        if len(path_parts) != 2:
            _LOGGER.warning(f"Invalid document URL format: {document_url}")
            return document_url

        bucket_name, object_path = path_parts

        presigned_url = client.presigned_get_object(bucket_name, object_path, expires=timedelta(seconds=expires))
        return presigned_url

    except Exception as e:
        _LOGGER.error(f"Error generating presigned URL from document URL {document_url}: {e}")
        return document_url


def list_objects(
    client: Minio | LocalFileStorage,
    bucket: str,
    prefix: str | None = None,
    include_version=True,
    recursive=True,
    start_after: str | None = None,
) -> ListObjectsResponse:
    objects: list[ObjectMetadata | Object] = client.list_objects(  # type: ignore
        bucket, prefix=prefix, recursive=recursive, include_version=include_version, start_after=start_after
    )
    objects: list[ObjectMetadata] = [
        obj if isinstance(obj, ObjectMetadata) else ObjectMetadata.from_minio_object(obj) for obj in objects
    ]
    return ListObjectsResponse(objects=objects)


def get_object(
    client: Minio | LocalFileStorage,
    bucket: str,
    object: str,
    version_id: str | None = None,
    include_versions=False,
) -> FileObjectResponse:
    try:
        stat = client.stat_object(bucket, object, version_id=version_id)
    except S3Error as se:
        if version_id:
            _LOGGER.warning(f"Error getting object {object} from bucket {bucket} with version {version_id}: {se}")
            try:
                _LOGGER.info(f"Retrying without version_id for object {object} in bucket {bucket}")
                stat = client.stat_object(bucket, object)
            except S3Error as se_retry:
                raise se_retry
        else:
            raise se

    try:
        obj = client.get_object(bucket, object, version_id=stat.version_id)

        if include_versions:
            versions = list_objects(client, bucket, prefix=object, include_version=include_versions)
        else:
            versions = None

        return FileObjectResponse(
            response=obj,
            metadata=stat if isinstance(stat, ObjectMetadata) else ObjectMetadata.from_minio_object(stat),
            versions=versions,
        )

    except S3Error as se:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {se}")
        raise HTTPException(status_code=404, detail=f"Object {object} not found in bucket {bucket}")
    except Exception as e:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {getattr(e, 'message', str(e))}")


def put_object(
    client: Minio | LocalFileStorage,
    bucket: str,
    object: str,
    data: BinaryIO | bytes | str,
    size: int,
    content_type: str = "application/octet-stream",
    metadata: dict[str, Any] | None = None,
    part_size: int = 100 * 1024 * 1024,
) -> ObjectMetadata:
    if isinstance(data, bytes):
        data_bytes_io = io.BytesIO(data)
        size = len(data)
    elif isinstance(data, str):
        encoded_data = data.encode("utf-8")
        data_bytes_io = io.BytesIO(encoded_data)
        size = len(encoded_data)
    else:
        data_bytes_io = data

    try:
        response = client.put_object(
            bucket,
            object,
            data_bytes_io,
            content_type=content_type,
            length=size,
            part_size=part_size,
            metadata=metadata or {},
        )

        return ObjectMetadata.from_minio_write_response(response)

    except S3Error as se:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {se}")
        raise se
    except Exception as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise e


def delete_object(client: Minio | LocalFileStorage, bucket: str, object: str, version_id: str | None = None):
    try:
        client.remove_object(bucket, object, version_id=version_id)

    except S3Error as se:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {se}")
        raise se
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise e


def create_bucket(
    client: Minio | LocalFileStorage,
    workspace_name: str,
    excluded_prefixes: list[str] = EXCLUDED_VERSIONING_PREFIXES,
):
    try:
        client.make_bucket(workspace_name)
        try:
            client.set_bucket_versioning(workspace_name, VersioningConfig(ENABLED))
        except Exception as e:
            _LOGGER.error(f"Error enabling versioning for bucket {workspace_name}: {e}")

    except S3Error as se:
        if se.code in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
            pass
        else:
            _LOGGER.error(f"Error creating bucket {workspace_name}: {se}")
            raise se
    except Exception as e:
        _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
        raise e


def put_document_file(
    client: Minio | LocalFileStorage,
    workspace_name: str,
    document_id: UUID,
    file_data: bytes,
    filename: str,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """
    Upload a document file to S3/local storage with deduplication.

    Args:
        client: Minio or LocalFileStorage client
        workspace_name: Name of the workspace bucket
        document_id: UUID of the document
        file_data: File data as bytes
        filename: Original filename
        metadata: Optional metadata to store with the file

    Returns:
        S3 object URL if file was uploaded, None if file already exists with same hash
    """
    object_path = get_pdf_s3_object_path(document_id)

    # Check if file already exists with same hash
    existing_files = list_objects(client, workspace_name, prefix=object_path, include_version=False, recursive=False)

    put_object = False

    if existing_files.objects:
        new_file_hash = compute_hash(file_data)
        existing_hashes = [
            existing_file.etag.strip('"') for existing_file in existing_files.objects if existing_file.etag is not None
        ]

        if new_file_hash not in existing_hashes:
            put_object = True
    else:
        put_object = True

    if put_object:
        response = client.put_object(
            workspace_name,
            object_path,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type="application/pdf",
            metadata=metadata or {},
        )

        return get_proxy_document_url(response.bucket_name, response.object_name)

    return None


def download_file_content(client: Minio | LocalFileStorage, document_url: str) -> bytes:
    """
    Download file content from a document URL.

    Args:
        client: Minio or LocalFileStorage client
        document_url: URL in format "/api/v1/file/{bucket_name}/{object_path}"

    Returns:
        File content as bytes
    """
    # Parse URL to get bucket and object path
    if not document_url.startswith("/api/v1/file/"):
        raise ValueError(f"Invalid document URL format: {document_url}")

    url_parts = document_url.replace("/api/v1/file/", "").split("/", 1)
    if len(url_parts) != 2:
        raise ValueError(f"Invalid document URL format: {document_url}")

    bucket_name, object_path = url_parts

    file_response = get_object(client, bucket_name, object_path)
    return file_response.response.read()


def delete_bucket(client: Minio | LocalFileStorage, workspace_name: str):
    if isinstance(client, LocalFileStorage):
        try:
            bucket_path = client._get_bucket_path(workspace_name)
            if bucket_path.exists() and bucket_path.is_dir():
                shutil.rmtree(bucket_path)
                _LOGGER.info(f"Locally deleted bucket directory: {bucket_path}")
        except Exception as e:
            _LOGGER.error(f"Error deleting local bucket directory {workspace_name}: {e}")
            raise e
    elif isinstance(client, Minio):
        try:
            # Existing Minio logic
            objects = client.list_objects(workspace_name, prefix="", recursive=True, include_version=True)
            # Convert generator to list to avoid issues during iteration
            obj_list = list(objects)
            for obj in obj_list:
                try:
                    if obj.object_name is not None:
                        client.remove_object(workspace_name, obj.object_name, version_id=obj.version_id)
                except S3Error as remove_err:
                    _LOGGER.warning(
                        f"Error removing object {obj.object_name} (version: {obj.version_id}) during bucket delete: {remove_err}"
                    )

            client.remove_bucket(workspace_name)
        except S3Error as se:
            if se.code in {"NoSuchBucket", "NotImplemented"}:
                pass
            else:
                _LOGGER.error(f"Error deleting Minio bucket {workspace_name}: {se}")
                raise se
        except Exception as e:
            _LOGGER.error(f"Error deleting Minio bucket {workspace_name}: {e}")
            raise e
    else:
        _LOGGER.error(f"Unknown client type for delete_bucket: {type(client)}")
        raise TypeError("Unsupported client type for delete_bucket")
