import hashlib
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, BinaryIO
from uuid import UUID

from botocore.exceptions import ClientError
from fastapi import HTTPException

from extralit_server.api.schemas.v1.files import FileObjectResponse, ListObjectsResponse, ObjectMetadata
from extralit_server.helpers import shared_resources

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client

EXCLUDED_VERSIONING_PREFIXES = ["pdf"]
CHUNK_LENGTH_MB = 10 * 1024 * 1024

_LOGGER = logging.getLogger(__name__)


async def get_s3_client() -> "S3Client":
    """Dependency function to get shared S3 client."""
    s3_client = shared_resources.get("s3_client")
    if s3_client is None:
        from extralit_server.helpers import create_s3_client

        try:
            s3_client = await create_s3_client()
            shared_resources["s3_client"] = s3_client
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return s3_client


async def get_file_chunk(
    s3_client: "S3Client", bucket_name: str, key: str, chunk_length: int
) -> AsyncGenerator[bytes, None]:
    """Async generator to get file chunks for streaming."""
    head = await s3_client.head_object(Bucket=bucket_name, Key=key)
    content_length = head["ContentLength"]

    for offset in range(0, content_length, chunk_length):
        end = min(offset + chunk_length - 1, content_length - 1)
        s3_file = await s3_client.get_object(Bucket=bucket_name, Key=key, Range=f"bytes={offset}-{end}")

        async with s3_file["Body"] as stream:
            yield await stream.read()


async def _put_object_to_s3(
    s3_client: "S3Client",
    bucket: str,
    key: str,
    data: BinaryIO | bytes,
    content_type: str,
    metadata: dict[str, Any] | None = None,
):
    """Put object to S3."""
    kwargs = {
        "Bucket": bucket,
        "Key": key,
        "Body": data,
        "ContentType": content_type,
    }
    if metadata:
        kwargs["Metadata"] = metadata

    return await s3_client.put_object(**kwargs)


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


async def get_presigned_url_from_document_url(s3_client, document_url: str, expires: int = 3600) -> str:
    """
    Generate a presigned URL from a document URL by parsing the bucket_name and object_path.

    Args:
        s3_client: aioboto3 S3 client
        document_url: URL in format "/api/v1/file/{bucket_name}/{object_path}"
        expires: Expiration time in seconds (default: 1 hour)

    Returns:
        Presigned URL if successful, original URL if parsing fails
    """
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

        presigned_url = await s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_path},
            ExpiresIn=expires,
        )
        return presigned_url

    except Exception as e:
        _LOGGER.error(f"Error generating presigned URL from document URL {document_url}: {e}")
        return document_url


async def list_objects(
    s3_client: "S3Client",
    bucket: str,
    prefix: str | None = None,
    include_version=True,
    recursive=True,
    start_after: str | None = None,
) -> ListObjectsResponse:
    """List objects in S3 bucket and return as ListObjectsResponse."""
    try:
        kwargs = {"Bucket": bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        if not recursive:
            kwargs["Delimiter"] = "/"

        objects = []

        if include_version:
            # Use list_object_versions to get all versions of objects
            version_kwargs = {"Bucket": bucket}
            if prefix:
                version_kwargs["Prefix"] = prefix
            if start_after:
                version_kwargs["KeyMarker"] = start_after
            if not recursive:
                version_kwargs["Delimiter"] = "/"

            response = await s3_client.list_object_versions(**version_kwargs)

            # Process versions
            for version in response.get("Versions", []):
                objects.append(
                    ObjectMetadata(
                        bucket_name=bucket,
                        object_name=version.get("Key") or "",
                        etag=version.get("ETag", "").strip('"'),
                        size=version.get("Size"),
                        last_modified=version.get("LastModified"),
                        content_type="application/octet-stream",  # Default, would need head_object for actual
                        version_id=version.get("VersionId"),
                        is_latest=version.get("IsLatest", False),
                        metadata={},
                    )
                )

            # Process delete markers if needed
            for delete_marker in response.get("DeleteMarkers", []):
                objects.append(
                    ObjectMetadata(
                        bucket_name=bucket,
                        object_name=delete_marker.get("Key") or "",
                        etag="",  # Delete markers don't have ETags
                        size=0,
                        last_modified=delete_marker.get("LastModified"),
                        content_type="application/octet-stream",
                        version_id=delete_marker.get("VersionId"),
                        is_latest=delete_marker.get("IsLatest", False),
                        metadata={},
                    )
                )
        else:
            # Use list_objects_v2 for current versions only
            if start_after:
                kwargs["StartAfter"] = start_after

            response = await s3_client.list_objects_v2(**kwargs)

            for obj in response.get("Contents", []):
                objects.append(
                    ObjectMetadata(
                        bucket_name=bucket,
                        object_name=obj.get("Key") or "",
                        etag=obj.get("ETag", "").strip('"'),
                        size=obj.get("Size"),
                        last_modified=obj.get("LastModified"),
                        content_type="application/octet-stream",  # Default, would need head_object for actual
                        is_latest=True,  # All objects from list_objects_v2 are latest versions
                        metadata={},
                    )
                )

        return ListObjectsResponse(objects=objects)
    except ClientError as e:
        _LOGGER.error(f"Error listing objects in bucket {bucket}: {e}")
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket}' not found")


async def get_object(
    s3_client: "S3Client",
    bucket: str,
    object: str,
    version_id: str | None = None,
    include_versions=False,
) -> FileObjectResponse:
    """Get object from S3 and return as FileObjectResponse."""
    try:
        # Get object metadata first
        head_kwargs = {"Bucket": bucket, "Key": object}
        if version_id:
            head_kwargs["VersionId"] = version_id
        head_response = await s3_client.head_object(**head_kwargs)

        # Get the actual object
        get_kwargs = {"Bucket": bucket, "Key": object}
        if version_id:
            get_kwargs["VersionId"] = version_id
        get_response = await s3_client.get_object(**get_kwargs)

        metadata = ObjectMetadata(
            bucket_name=bucket,
            object_name=object,
            etag=head_response["ETag"].strip('"'),
            size=head_response["ContentLength"],
            last_modified=head_response["LastModified"],
            content_type=head_response.get("ContentType", "application/octet-stream"),
            version_id=head_response.get("VersionId") or version_id,
            metadata=head_response.get("Metadata", {}),
        )

        versions = None
        if include_versions:
            versions = await list_objects(s3_client, bucket, prefix=object, include_version=include_versions)

        return FileObjectResponse(
            response=get_response["Body"],
            metadata=metadata,
            versions=versions,
        )

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            _LOGGER.error(f"Object {object} not found in bucket {bucket}")
            raise HTTPException(status_code=404, detail=f"Object {object} not found in bucket {bucket}")
        else:
            _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def put_object(
    s3_client: "S3Client",
    bucket: str,
    object: str,
    data: BinaryIO | bytes | str,
    content_type: str = "application/octet-stream",
    metadata: dict[str, Any] | None = None,
) -> ObjectMetadata:
    """Put object to S3 and return ObjectMetadata."""
    try:
        # Prepare data
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif hasattr(data, "read"):  # File-like object
            data = data.read()

        # Upload to S3
        await _put_object_to_s3(s3_client, bucket, object, data, content_type, metadata)

        # Get metadata for response
        head_response = await s3_client.head_object(Bucket=bucket, Key=object)

        return ObjectMetadata(
            bucket_name=bucket,
            object_name=object,
            etag=head_response["ETag"].strip('"'),
            size=head_response["ContentLength"],
            last_modified=head_response["LastModified"],
            content_type=head_response.get("ContentType", content_type),
            # Propagate the S3 object version (mirrors get_object) so callers can pin the
            # immutable version; otherwise schema_versions.object_version_id is always NULL.
            version_id=head_response.get("VersionId"),
            metadata=head_response.get("Metadata", {}),
        )

    except ClientError as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def delete_object(s3_client, bucket: str, object: str, version_id: str | None = None):
    """Delete object from S3."""
    try:
        kwargs = {"Bucket": bucket, "Key": object}
        if version_id:
            kwargs["VersionId"] = version_id
        await s3_client.delete_object(**kwargs)
    except ClientError as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def bucket_exists(s3_client: "S3Client", bucket_name: str) -> bool:
    """Check if S3 bucket exists."""
    try:
        await s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ["404", "NoSuchBucket"]:
            return False
        # For other errors (like permissions), log and return False
        _LOGGER.warning(f"Error checking bucket {bucket_name}: {e}")
        return False
    except Exception as e:
        _LOGGER.warning(f"Unexpected error checking bucket {bucket_name}: {e}")
        return False


async def get_bucket_versioning(s3_client: "S3Client", bucket_name: str) -> dict[str, str] | None:
    """Get bucket versioning configuration."""
    try:
        response = await s3_client.get_bucket_versioning(Bucket=bucket_name)
        return {
            "status": response.get("Status", "Disabled"),
            "mfa_delete": response.get("MFADelete", "Disabled"),
        }
    except ClientError as e:
        _LOGGER.error(f"Error getting bucket versioning for {bucket_name}: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"Unexpected error getting bucket versioning for {bucket_name}: {e}")
        return None


async def create_bucket(
    s3_client: "S3Client",
    workspace_name: str,
    excluded_prefixes: list[str] = EXCLUDED_VERSIONING_PREFIXES,
):
    """Create S3 bucket."""
    try:
        await s3_client.create_bucket(Bucket=workspace_name)

        await s3_client.put_bucket_versioning(
            Bucket=workspace_name,
            VersioningConfiguration={
                "Status": "Enabled",
                "MFADelete": "Disabled",
            },
        )

    except ClientError as e:
        if e.response["Error"]["Code"] in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
            pass  # Bucket already exists, that's fine
        else:
            _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating bucket: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def put_document_file(
    s3_client: "S3Client",
    workspace_name: str,
    document_id: UUID,
    file_data: bytes,
    filename: str,
    content_type: str = "application/pdf",
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """
    Upload a document file to S3 with deduplication.

    Args:
        s3_client: aioboto3 S3 client
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
    try:
        existing_files = await list_objects(
            s3_client, workspace_name, prefix=object_path, include_version=False, recursive=False
        )

        should_upload = True
        if existing_files.objects:
            new_file_hash = compute_hash(file_data)
            existing_hashes = [
                existing_file.etag for existing_file in existing_files.objects if existing_file.etag is not None
            ]

            if new_file_hash in existing_hashes:
                should_upload = False

        if should_upload:
            await _put_object_to_s3(
                s3_client,
                workspace_name,
                object_path,
                file_data,
                content_type,
                metadata,
            )

            return get_proxy_document_url(workspace_name, object_path)

        return None

    except Exception as e:
        _LOGGER.error(f"Error uploading document file {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {e!s}")


async def download_file_content(s3_client, document_url: str) -> bytes:
    """
    Download file content from a document URL.

    Args:
        s3_client: aioboto3 S3 client
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

    try:
        response = await s3_client.get_object(Bucket=bucket_name, Key=object_path)
        return await response["Body"].read()
    except ClientError as e:
        _LOGGER.error(f"Error downloading file content from {document_url}: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {document_url}")


async def delete_bucket(s3_client, workspace_name: str):
    """Delete S3 bucket and all its contents."""
    try:
        # First, delete all objects in the bucket
        response = await s3_client.list_objects_v2(Bucket=workspace_name)

        if "Contents" in response:
            for obj in response["Contents"]:
                try:
                    await s3_client.delete_object(Bucket=workspace_name, Key=obj["Key"])
                except ClientError as remove_err:
                    _LOGGER.warning(f"Error removing object {obj['Key']} during bucket delete: {remove_err}")

        # Then delete the bucket itself
        await s3_client.delete_bucket(Bucket=workspace_name)
        _LOGGER.info(f"Successfully deleted bucket: {workspace_name}")

    except ClientError as e:
        if e.response["Error"]["Code"] in ["NoSuchBucket", "NotImplemented"]:
            pass  # Bucket doesn't exist, that's fine
        else:
            _LOGGER.error(f"Error deleting S3 bucket {workspace_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting bucket: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error deleting S3 bucket {workspace_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")
