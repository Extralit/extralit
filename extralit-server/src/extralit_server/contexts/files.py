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
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Optional
from urllib.parse import urlparse
from uuid import UUID

import aioboto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

from extralit_server.api.schemas.v1.files import FileObjectResponse, ListObjectsResponse, ObjectMetadata
from extralit_server.settings import settings

EXCLUDED_VERSIONING_PREFIXES = ["pdf"]

_LOGGER = logging.getLogger(__name__)


# Custom exception for LocalFileStorage to match S3 behavior
class LocalS3Error(Exception):
    """Local file storage exception that mimics S3 ClientError."""
    
    def __init__(self, error_code: str, message: str, key: str = ""):
        self.response = {
            "Error": {
                "Code": error_code,
                "Message": message,
                "Key": key,
            }
        }
        super().__init__(f"{error_code}: {message}")


# Mock response class for LocalFileStorage
class LocalFileResponse:
    """Mock response class for LocalFileStorage get_object operations."""
    
    def __init__(self, content: bytes):
        self._content = content
        self._position = 0
    
    def read(self, size: int = -1) -> bytes:
        if size == -1:
            data = self._content[self._position:]
            self._position = len(self._content)
        else:
            data = self._content[self._position:self._position + size]
            self._position += len(data)
        return data
    
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        chunk = self.read(8192)  # Read in 8KB chunks
        if not chunk:
            raise StopAsyncIteration
        return chunk


# Mock write result for LocalFileStorage
class LocalObjectWriteResult:
    """Mock write result for LocalFileStorage put_object operations."""
    
    def __init__(self, bucket_name: str, object_name: str, version_id: str, etag: str):
        self.bucket_name = bucket_name
        self.object_name = object_name
        self.version_id = version_id
        self.etag = etag

# Singleton instances
_s3_session: Optional[aioboto3.Session] = None
_local_storage_client: Optional["LocalFileStorage"] = None


def _create_s3_session() -> Optional[aioboto3.Session]:
    """Create a new aioboto3 session instance."""
    if None in [settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key]:
        # Will use local file system storage if S3 settings are not provided
        return None

    try:
        return aioboto3.Session(
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
    except Exception as e:
        _LOGGER.error(f"Error creating S3 session: {e}", stack_info=True)
        raise e


def get_s3_session() -> Optional[aioboto3.Session]:
    """Get a singleton S3 session instance."""
    global _s3_session

    if _s3_session is None:
        _s3_session = _create_s3_session()

    return _s3_session


async def get_async_s3_client():
    """Get an async S3 client instance."""
    session = get_s3_session()
    if session is None:
        # Use local file system storage if S3 settings are not provided
        global _local_storage_client
        if _local_storage_client is None:
            local_storage_path = os.path.join(settings.home_path, "storage")  # type: ignore
            _LOGGER.info(f"Using local file storage at: {local_storage_path}")
            _local_storage_client = LocalFileStorage(local_storage_path)
        return _local_storage_client
    
    parsed_url = urlparse(settings.s3_endpoint)
    endpoint_url = settings.s3_endpoint
    use_ssl = parsed_url.scheme == "https"
    
    return session.client(
        "s3",
        endpoint_url=endpoint_url,
        use_ssl=use_ssl,
        verify=use_ssl,  # Only verify SSL certificates if using HTTPS
    )


def reset_s3_client():
    """Reset the singleton S3 session (useful for testing or reconnection)."""
    global _s3_session, _local_storage_client
    _s3_session = None
    _local_storage_client = None


# Backward compatibility function
def get_minio_client():
    """Backward compatibility function - returns LocalFileStorage if no S3 config."""
    session = get_s3_session()
    if session is None:
        global _local_storage_client
        if _local_storage_client is None:
            local_storage_path = os.path.join(settings.home_path, "storage")  # type: ignore
            _LOGGER.info(f"Using local file storage at: {local_storage_path}")
            _local_storage_client = LocalFileStorage(local_storage_path)
        return _local_storage_client
    
    # For S3, we need to return something that can be detected as non-LocalFileStorage
    # This is a placeholder for sync compatibility - actual async operations should use get_async_s3_client
    return "S3_SESSION_MARKER"


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
    ) -> LocalObjectWriteResult:
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

        return LocalObjectWriteResult(
            bucket_name=bucket_name,
            object_name=object_name,
            version_id=version_id,
            etag=content_hash,
        )

    def get_object(self, bucket_name: str, object_name: str, version_id: str | None = None) -> LocalFileResponse:
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f".{version_id}")
            if not version_path.exists():
                raise LocalS3Error("NoSuchKey", "The specified version does not exist", object_name)
            with open(version_path, "rb") as f:
                content = f.read()
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if not object_path.exists():
                raise LocalS3Error("NoSuchKey", "The specified key does not exist", object_name)
            with open(object_path, "rb") as f:
                content = f.read()

        # The metadata is not needed for the LocalFileResponse, but kept for consistency
        # with the original implementation's metadata fetching.
        meta_path = self._get_object_path(bucket_name, object_name).with_suffix(".metadata.json")
        if not meta_path.exists():
            raise LocalS3Error("NoSuchKey", "The specified key does not exist", object_name)
        with open(meta_path) as f:
            json.load(f)

        return LocalFileResponse(content)

    def stat_object(self, bucket_name: str, object_name: str, version_id: str | None = None) -> ObjectMetadata:
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f".{version_id}")
            if not version_path.exists():
                raise LocalS3Error("NoSuchKey", "The specified version does not exist", object_name)
            path = version_path
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if not object_path.exists():
                raise LocalS3Error("NoSuchKey", "The specified key does not exist", object_name)
            path = object_path

        # Get metadata from file
        meta_path = self._get_object_path(bucket_name, object_name).with_suffix(".metadata.json")
        if not meta_path.exists():
            raise LocalS3Error("NoSuchKey", "The specified key does not exist", object_name)

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


def get_thumbnail_s3_object_path(id: UUID | str) -> str:
    """
    Generate S3 object path for document thumbnail images.
    
    Args:
        id: Document UUID or string identifier
        
    Returns:
        S3 object path for thumbnail (e.g., "thumbnails/{document_id}")
    """
    if not id:
        raise Exception("id cannot be None")

    elif isinstance(id, UUID):
        object_path = f"thumbnails/{id!s}"
    else:
        object_path = f"thumbnails/{id}"

    return object_path


def get_proxy_document_url(bucket_name: str, object_path: str) -> str:
    return f"/api/v1/file/{bucket_name}/{object_path}"


async def get_presigned_url_from_document_url(
    client, document_url: str, expires: int = 3600
) -> str:
    """
    Generate a presigned URL from a document URL by parsing the bucket_name and object_path.

    Args:
        client: S3 client or LocalFileStorage instance
        document_url: URL in format "/api/v1/file/{bucket_name}/{object_path}"
        expires: Expiration time in seconds (default: 1 hour)

    Returns:
        Presigned URL if successful, None if parsing fails or client is LocalFileStorage
    """
    if isinstance(client, LocalFileStorage):
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

        presigned_url = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_path},
            ExpiresIn=expires
        )
        return presigned_url

    except Exception as e:
        _LOGGER.error(f"Error generating presigned URL from document URL {document_url}: {e}")
        return document_url


async def list_objects(
    client,
    bucket: str,
    prefix: str | None = None,
    include_version=True,
    recursive=True,
    start_after: str | None = None,
) -> ListObjectsResponse:
    """
    List objects in S3 bucket or LocalFileStorage.
    
    Args:
        client: S3 client or LocalFileStorage instance
        bucket: Bucket name
        prefix: Object prefix filter
        include_version: Include version information
        recursive: Recursive listing
        start_after: Start listing after this key
        
    Returns:
        ListObjectsResponse containing list of ObjectMetadata
    """
    if isinstance(client, LocalFileStorage):
        objects = client.list_objects(
            bucket, prefix=prefix, recursive=recursive, include_version=include_version, start_after=start_after
        )
        return ListObjectsResponse(objects=objects)
    
    # For S3 client
    try:
        kwargs = {
            "Bucket": bucket,
        }
        if prefix:
            kwargs["Prefix"] = prefix
        if start_after:
            kwargs["StartAfter"] = start_after
        
        objects = []
        
        if include_version:
            response = await client.list_object_versions(**kwargs)
            for version in response.get("Versions", []):
                obj_metadata = ObjectMetadata(
                    bucket_name=bucket,
                    object_name=version["Key"],
                    version_id=version.get("VersionId"),
                    etag=version.get("ETag", "").strip('"'),
                    size=version.get("Size", 0),
                    last_modified=version.get("LastModified"),
                    content_type="application/octet-stream",  # S3 doesn't provide content type in list operations
                    is_latest=version.get("IsLatest", False),
                )
                objects.append(obj_metadata)
        else:
            response = await client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                obj_metadata = ObjectMetadata(
                    bucket_name=bucket,
                    object_name=obj["Key"],
                    etag=obj.get("ETag", "").strip('"'),
                    size=obj.get("Size", 0),
                    last_modified=obj.get("LastModified"),
                    content_type="application/octet-stream",  # S3 doesn't provide content type in list operations
                )
                objects.append(obj_metadata)
        
        return ListObjectsResponse(objects=objects)
        
    except ClientError as e:
        _LOGGER.error(f"Error listing objects in bucket {bucket}: {e}")
        raise HTTPException(status_code=404, detail=f"Error listing objects: {e}")
    except Exception as e:
        _LOGGER.error(f"Error listing objects in bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def get_object(
    client,
    bucket: str,
    object: str,
    version_id: str | None = None,
    include_versions=False,
) -> FileObjectResponse:
    """
    Get object from S3 bucket or LocalFileStorage.
    
    Args:
        client: S3 client or LocalFileStorage instance
        bucket: Bucket name
        object: Object key
        version_id: Specific version ID
        include_versions: Include version information
        
    Returns:
        FileObjectResponse containing object data and metadata
    """
    if isinstance(client, LocalFileStorage):
        try:
            stat = client.stat_object(bucket, object, version_id=version_id)
        except LocalS3Error as se:
            if version_id:
                _LOGGER.warning(f"Error getting object {object} from bucket {bucket} with version {version_id}: {se}")
                try:
                    _LOGGER.info(f"Retrying without version_id for object {object} in bucket {bucket}")
                    stat = client.stat_object(bucket, object)
                except LocalS3Error as se_retry:
                    raise se_retry
            else:
                raise se

        try:
            obj = client.get_object(bucket, object, version_id=stat.version_id)

            if include_versions:
                versions = await list_objects(client, bucket, prefix=object, include_version=include_versions)
            else:
                versions = None

            return FileObjectResponse(
                response=obj,
                metadata=stat,
                versions=versions,
            )

        except LocalS3Error as se:
            _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {se}")
            raise HTTPException(status_code=404, detail=f"Object {object} not found in bucket {bucket}")
        except Exception as e:
            _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")
    
    # For S3 client
    try:
        # Get object metadata first
        kwargs = {"Bucket": bucket, "Key": object}
        if version_id:
            kwargs["VersionId"] = version_id
            
        head_response = await client.head_object(**kwargs)
        
        # Create ObjectMetadata from head response
        stat = ObjectMetadata(
            bucket_name=bucket,
            object_name=object,
            version_id=head_response.get("VersionId"),
            etag=head_response.get("ETag", "").strip('"'),
            size=head_response.get("ContentLength", 0),
            last_modified=head_response.get("LastModified"),
            content_type=head_response.get("ContentType", "application/octet-stream"),
            metadata=head_response.get("Metadata", {}),
        )
        
    except ClientError as ce:
        if version_id:
            _LOGGER.warning(f"Error getting object {object} from bucket {bucket} with version {version_id}: {ce}")
            try:
                _LOGGER.info(f"Retrying without version_id for object {object} in bucket {bucket}")
                head_response = await client.head_object(Bucket=bucket, Key=object)
                stat = ObjectMetadata(
                    bucket_name=bucket,
                    object_name=object,
                    version_id=head_response.get("VersionId"),
                    etag=head_response.get("ETag", "").strip('"'),
                    size=head_response.get("ContentLength", 0),
                    last_modified=head_response.get("LastModified"),
                    content_type=head_response.get("ContentType", "application/octet-stream"),
                    metadata=head_response.get("Metadata", {}),
                )
            except ClientError as ce_retry:
                raise ce_retry
        else:
            raise ce

    try:
        # Get the actual object data
        get_kwargs = {"Bucket": bucket, "Key": object}
        if stat.version_id:
            get_kwargs["VersionId"] = stat.version_id
            
        obj_response = await client.get_object(**get_kwargs)

        if include_versions:
            versions = await list_objects(client, bucket, prefix=object, include_version=include_versions)
        else:
            versions = None

        return FileObjectResponse(
            response=obj_response["Body"],
            metadata=stat,
            versions=versions,
        )

    except ClientError as ce:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {ce}")
        raise HTTPException(status_code=404, detail=f"Object {object} not found in bucket {bucket}")
    except Exception as e:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def put_object(
    client,
    bucket: str,
    object: str,
    data: BinaryIO | bytes | str,
    size: int,
    content_type: str = "application/octet-stream",
    metadata: dict[str, Any] | None = None,
    part_size: int = 100 * 1024 * 1024,
) -> ObjectMetadata:
    """
    Put object into S3 bucket or LocalFileStorage.
    
    Args:
        client: S3 client or LocalFileStorage instance
        bucket: Bucket name
        object: Object key
        data: Object data
        size: Data size
        content_type: MIME content type
        metadata: Object metadata
        part_size: Part size for multipart uploads (ignored for LocalFileStorage)
        
    Returns:
        ObjectMetadata for the created object
    """
    if isinstance(data, bytes):
        data_bytes_io = io.BytesIO(data)
        size = len(data)
    elif isinstance(data, str):
        encoded_data = data.encode("utf-8")
        data_bytes_io = io.BytesIO(encoded_data)
        size = len(encoded_data)
    else:
        data_bytes_io = data

    if isinstance(client, LocalFileStorage):
        try:
            response = client.put_object(
                bucket,
                object,
                data_bytes_io,
                content_type=content_type,
                length=size,
                metadata=metadata or {},
            )

            return ObjectMetadata(
                bucket_name=response.bucket_name,
                object_name=response.object_name,
                version_id=response.version_id,
                etag=response.etag,
                size=size,
                content_type=content_type,
                metadata=metadata or {},
            )

        except LocalS3Error as se:
            _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {se}")
            raise se
        except Exception as e:
            _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
            raise e
    
    # For S3 client
    try:
        kwargs = {
            "Bucket": bucket,
            "Key": object,
            "Body": data_bytes_io,
            "ContentType": content_type,
        }
        
        if metadata:
            kwargs["Metadata"] = metadata
            
        response = await client.put_object(**kwargs)
        
        return ObjectMetadata(
            bucket_name=bucket,
            object_name=object,
            version_id=response.get("VersionId"),
            etag=response.get("ETag", "").strip('"'),
            size=size,
            content_type=content_type,
            metadata=metadata or {},
        )

    except ClientError as ce:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {ce}")
        raise ce
    except Exception as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise e


async def delete_object(client, bucket: str, object: str, version_id: str | None = None):
    """
    Delete object from S3 bucket or LocalFileStorage.
    
    Args:
        client: S3 client or LocalFileStorage instance
        bucket: Bucket name
        object: Object key
        version_id: Specific version ID to delete
    """
    if isinstance(client, LocalFileStorage):
        try:
            client.remove_object(bucket, object, version_id=version_id)
        except LocalS3Error as se:
            _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {se}")
            raise se
        except Exception as e:
            _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
            raise e
        return
    
    # For S3 client
    try:
        kwargs = {"Bucket": bucket, "Key": object}
        if version_id:
            kwargs["VersionId"] = version_id
            
        await client.delete_object(**kwargs)

    except ClientError as ce:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {ce}")
        raise ce
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise e


async def create_bucket(
    client,
    workspace_name: str,
    excluded_prefixes: list[str] = EXCLUDED_VERSIONING_PREFIXES,
):
    """
    Create bucket in S3 or LocalFileStorage.
    
    Args:
        client: S3 client or LocalFileStorage instance
        workspace_name: Name of the bucket/workspace
        excluded_prefixes: Prefixes to exclude from versioning (not used for S3)
    """
    if isinstance(client, LocalFileStorage):
        try:
            client.make_bucket(workspace_name)
            try:
                client.set_bucket_versioning(workspace_name, None)  # LocalFileStorage doesn't need versioning config
            except Exception as e:
                _LOGGER.error(f"Error enabling versioning for bucket {workspace_name}: {e}")
        except LocalS3Error as se:
            if "BucketAlreadyExists" in str(se):
                pass
            else:
                _LOGGER.error(f"Error creating bucket {workspace_name}: {se}")
                raise se
        except Exception as e:
            _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
            raise e
        return
    
    # For S3 client
    try:
        await client.create_bucket(Bucket=workspace_name)
        try:
            # Enable versioning for the bucket
            await client.put_bucket_versioning(
                Bucket=workspace_name,
                VersioningConfiguration={"Status": "Enabled"}
            )
        except Exception as e:
            _LOGGER.error(f"Error enabling versioning for bucket {workspace_name}: {e}")

    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        if error_code in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
            pass
        else:
            _LOGGER.error(f"Error creating bucket {workspace_name}: {ce}")
            raise ce
    except Exception as e:
        _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
        raise e


async def put_document_file(
    client,
    workspace_name: str,
    document_id: UUID,
    file_data: bytes,
    filename: str,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """
    Upload a document file to S3/local storage with deduplication.

    Args:
        client: S3 client or LocalFileStorage instance
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
    existing_files = await list_objects(client, workspace_name, prefix=object_path, include_version=False, recursive=False)

    put_object_flag = False

    if existing_files.objects:
        new_file_hash = compute_hash(file_data)
        existing_hashes = [
            existing_file.etag.strip('"') for existing_file in existing_files.objects if existing_file.etag is not None
        ]

        if new_file_hash not in existing_hashes:
            put_object_flag = True
    else:
        put_object_flag = True

    if put_object_flag:
        response = await put_object(
            client,
            workspace_name,
            object_path,
            file_data,
            len(file_data),
            content_type="application/pdf",
            metadata=metadata or {},
        )

        return get_proxy_document_url(response.bucket_name, response.object_name)

    return None


async def download_file_content(client, document_url: str) -> bytes:
    """
    Download file content from a document URL.

    Args:
        client: S3 client or LocalFileStorage instance
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

    file_response = await get_object(client, bucket_name, object_path)
    
    # Handle different response types
    if isinstance(client, LocalFileStorage):
        return file_response.response.read()
    else:
        # For S3 client, response.response is a StreamingBody
        return await file_response.response.read()


async def delete_bucket(client, workspace_name: str):
    """
    Delete bucket from S3 or LocalFileStorage.
    
    Args:
        client: S3 client or LocalFileStorage instance
        workspace_name: Name of the bucket/workspace to delete
    """
    if isinstance(client, LocalFileStorage):
        try:
            bucket_path = client._get_bucket_path(workspace_name)
            if bucket_path.exists() and bucket_path.is_dir():
                shutil.rmtree(bucket_path)
                _LOGGER.info(f"Locally deleted bucket directory: {bucket_path}")
        except Exception as e:
            _LOGGER.error(f"Error deleting local bucket directory {workspace_name}: {e}")
            raise e
        return
    
    # For S3 client
    try:
        # List and delete all objects in the bucket
        objects_response = await list_objects(client, workspace_name, prefix="", include_version=True, recursive=True)
        
        for obj in objects_response.objects:
            try:
                if obj.object_name is not None:
                    await delete_object(client, workspace_name, obj.object_name, version_id=obj.version_id)
            except ClientError as remove_err:
                _LOGGER.warning(
                    f"Error removing object {obj.object_name} (version: {obj.version_id}) during bucket delete: {remove_err}"
                )

        # Delete the bucket itself
        await client.delete_bucket(Bucket=workspace_name)
        
    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        if error_code in {"NoSuchBucket", "NotImplemented"}:
            pass
        else:
            _LOGGER.error(f"Error deleting S3 bucket {workspace_name}: {ce}")
            raise ce
    except Exception as e:
        _LOGGER.error(f"Error deleting S3 bucket {workspace_name}: {e}")
        raise e
