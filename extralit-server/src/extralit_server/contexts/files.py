import hashlib
import logging
import mimetypes
from datetime import timedelta
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

import obstore
from fastapi import HTTPException
from obstore.exceptions import BaseError as ObjectStoreError
from obstore.store import LocalStore, S3Store

from extralit_server.api.schemas.v1.files import FileObjectResponse, ListObjectsResponse, ObjectMetadata
from extralit_server.helpers import shared_resources
from extralit_server.settings import settings

# LocalStore cannot persist attributes (obstore raises NotImplementedError for `put_opts` with
# attributes), so in local mode the content type has to be recovered from the key. These are the
# extension-less prefixes minted below; everything else is guessed from the filename.
_CONTENT_TYPE_BY_PREFIX = {
    "pdf/": "application/pdf",
    "thumbnails/": "image/png",
    "layout/": "application/json",
    "schemas/": "application/json",
}

_LOGGER = logging.getLogger(__name__)


def workspace_root(workspace_name: str) -> tuple[str, str]:
    """Resolve where a workspace's artifacts live, as `(bucket, key prefix)`.

    The single place that knows how a workspace maps onto storage: PDFs, thumbnails, layout JSON
    and the Lance datasets all address through it, so moving to one bucket with `{org}/{workspace}/`
    prefixes is a change here rather than at every call site. Today it is bucket-per-workspace,
    which is why the prefix is empty and `files` can still pass the workspace name as the bucket.
    """
    if not workspace_name:
        raise ValueError("workspace_name cannot be empty")

    return workspace_name, ""


class ObjectStorage:
    """Resolves a bucket name to an obstore store, caching one store per bucket.

    obstore binds a store to a single bucket at construction, so the per-call `bucket` argument
    every function in this module takes is a lookup here rather than a request parameter.
    """

    def __init__(self) -> None:
        self._stores: dict[str, S3Store | LocalStore] = {}
        self._remote = all([settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key])

    @property
    def signable(self) -> bool:
        """Only S3 can presign; `LocalStore` is not a `SignCapableStore`."""
        return self._remote

    def store_for(self, bucket: str) -> S3Store | LocalStore:
        store = self._stores.get(bucket)
        if store is None:
            store = self._build(bucket)
            self._stores[bucket] = store
        return store

    def _build(self, bucket: str) -> S3Store | LocalStore:
        if not self._remote:
            return LocalStore(prefix=Path(settings.home_path) / bucket, mkdir=True)

        endpoint = settings.s3_endpoint or ""
        return S3Store(
            bucket,
            endpoint=endpoint,
            access_key_id=settings.s3_access_key,
            secret_access_key=settings.s3_secret_key,
            region=settings.s3_region or "us-east-1",
            virtual_hosted_style_request=False,
            client_options={"allow_http": not endpoint.startswith("https://")},
        )

    async def aclose(self) -> None:
        self._stores.clear()


async def get_storage() -> ObjectStorage:
    """Dependency function to get the shared object storage."""
    storage = shared_resources.get("storage")
    if storage is None:
        storage = ObjectStorage()
        shared_resources["storage"] = storage

    return storage


def content_type_of(key: str, attributes: Any = None) -> str:
    declared = dict(attributes or {}).get("Content-Type")
    if declared:
        return declared

    for prefix, content_type in _CONTENT_TYPE_BY_PREFIX.items():
        if key.startswith(prefix):
            return content_type

    guessed, _ = mimetypes.guess_type(key)
    return guessed or "application/octet-stream"


def _user_metadata(attributes: Any = None) -> dict[str, str]:
    return {key: value for key, value in dict(attributes or {}).items() if key != "Content-Type"}


def _object_metadata(bucket: str, meta: Any, attributes: Any = None) -> ObjectMetadata:
    key = meta["path"]
    return ObjectMetadata(
        bucket_name=bucket,
        object_name=key,
        etag=(meta["e_tag"] or "").strip('"') or None,
        size=meta["size"],
        last_modified=meta["last_modified"],
        content_type=content_type_of(key, attributes),
        metadata=_user_metadata(attributes),
    )


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


def split_document_url(document_url: str) -> tuple[str, str]:
    """Split `/api/v1/file/{bucket}/{object}` back into its bucket and key."""
    prefix = "/api/v1/file/"
    if not document_url.startswith(prefix):
        raise ValueError(f"Invalid document URL format: {document_url}")

    parts = document_url[len(prefix) :].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid document URL format: {document_url}")

    return parts[0], parts[1]


async def get_presigned_url_from_document_url(storage: ObjectStorage, document_url: str, expires: int = 3600) -> str:
    """Presign a `/api/v1/file/{bucket}/{object}` URL, valid for `expires` seconds.

    Local storage cannot sign, so it keeps serving through the proxy route.
    """
    try:
        bucket, object_path = split_document_url(document_url)
    except ValueError:
        _LOGGER.warning(f"Invalid document URL format: {document_url}")
        return document_url

    if not storage.signable:
        return document_url

    try:
        return await obstore.sign_async(storage.store_for(bucket), "GET", object_path, timedelta(seconds=expires))
    except Exception as e:
        _LOGGER.error(f"Error generating presigned URL from document URL {document_url}: {e}")
        return document_url


async def list_objects(
    storage: ObjectStorage,
    bucket: str,
    prefix: str | None = None,
    recursive=True,
    start_after: str | None = None,
) -> ListObjectsResponse:
    """List objects in a bucket and return as ListObjectsResponse."""
    store = storage.store_for(bucket)
    try:
        if recursive:
            metas = []
            async for batch in store.list(prefix, offset=start_after):
                metas.extend(batch)
        else:
            result = await store.list_with_delimiter_async(prefix)
            metas = list(result["objects"])
            if start_after:
                metas = [meta for meta in metas if meta["path"] > start_after]

        # Attributes are not returned by listing APIs, so the content type is key-derived here.
        return ListObjectsResponse(objects=[_object_metadata(bucket, meta) for meta in metas])
    except FileNotFoundError:
        _LOGGER.error(f"Bucket '{bucket}' not found")
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket}' not found")
    except ObjectStoreError as e:
        _LOGGER.error(f"Error listing objects in bucket {bucket}: {e}")
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket}' not found")


async def get_object(storage: ObjectStorage, bucket: str, object: str) -> FileObjectResponse:
    """Get an object and return it as a FileObjectResponse whose `response` streams."""
    try:
        result = await storage.store_for(bucket).get_async(object)
        return FileObjectResponse(
            response=result,
            metadata=_object_metadata(bucket, result.meta, result.attributes),
        )
    except FileNotFoundError:
        _LOGGER.error(f"Object {object} not found in bucket {bucket}")
        raise HTTPException(status_code=404, detail=f"Object {object} not found in bucket {bucket}")
    except ObjectStoreError as e:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def _put(
    storage: ObjectStorage,
    bucket: str,
    key: str,
    data: bytes,
    content_type: str,
    metadata: dict[str, Any] | None = None,
):
    attributes = {"Content-Type": content_type, **{k: str(v) for k, v in (metadata or {}).items()}}
    store = storage.store_for(bucket)
    if isinstance(store, LocalStore):
        # LocalStore rejects attributes outright; the content type is recovered from the key.
        return await store.put_async(key, data)

    return await store.put_async(key, data, attributes=attributes)


async def put_object(
    storage: ObjectStorage,
    bucket: str,
    object: str,
    data: BinaryIO | bytes | str,
    content_type: str = "application/octet-stream",
    metadata: dict[str, Any] | None = None,
) -> ObjectMetadata:
    """Put an object and return its ObjectMetadata."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif hasattr(data, "read"):
        data = data.read()

    try:
        result = await _put(storage, bucket, object, data, content_type, metadata)

        return ObjectMetadata(
            bucket_name=bucket,
            object_name=object,
            etag=(result["e_tag"] or "").strip('"') or None,
            size=len(data),
            content_type=content_type,
            metadata=metadata or {},
        )
    except ObjectStoreError as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def delete_object(storage: ObjectStorage, bucket: str, object: str):
    """Delete an object. Deleting a key that is already gone is not an error."""
    try:
        await storage.store_for(bucket).delete_async(object)
    except FileNotFoundError:
        pass
    except ObjectStoreError as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def delete_document_artifacts(storage: ObjectStorage, workspace_name: str, document_id: UUID | str) -> None:
    """Remove every artifact of a document: PDF, thumbnail, layout JSON and layout rows.

    Best effort — the DB rows are already gone by the time this runs, so a storage hiccup leaves a
    leaked object rather than a document the caller cannot delete. A leak here is negligible and can
    be ignored: the objects are unreachable and layout rows only survive until the document is
    re-parsed or a sweeper runs.
    """
    from extralit_server.contexts.ocr import storage as layout_storage

    for object_path in (get_pdf_s3_object_path(document_id), get_thumbnail_s3_object_path(document_id)):
        try:
            await delete_object(storage, workspace_name, object_path)
        except Exception as e:
            _LOGGER.warning(f"Could not delete {object_path} for document {document_id}: {e}")

    try:
        await layout_storage.delete_layout(storage, workspace_name, document_id)
    except Exception as e:
        _LOGGER.warning(f"Could not delete layout artifacts for document {document_id}: {e}")


async def put_document_file(
    storage: ObjectStorage,
    workspace_name: str,
    document_id: UUID,
    file_data: bytes,
    filename: str,
    content_type: str = "application/pdf",
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """
    Upload a document file with deduplication.

    Returns:
        The proxy object URL if the file was uploaded, None if an identical file already exists.
    """
    object_path = get_pdf_s3_object_path(document_id)

    try:
        existing_files = await list_objects(storage, workspace_name, prefix=object_path, recursive=False)

        should_upload = True
        if existing_files.objects:
            new_file_hash = compute_hash(file_data)
            existing_hashes = [
                existing_file.etag for existing_file in existing_files.objects if existing_file.etag is not None
            ]

            if new_file_hash in existing_hashes:
                should_upload = False

        if should_upload:
            await _put(storage, workspace_name, object_path, file_data, content_type, metadata)

            return get_proxy_document_url(workspace_name, object_path)

        return None

    except Exception as e:
        _LOGGER.error(f"Error uploading document file {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {e!s}")


async def download_file_content(storage: ObjectStorage, document_url: str) -> bytes:
    """Download the whole body behind a `/api/v1/file/{bucket}/{object}` URL."""
    bucket_name, object_path = split_document_url(document_url)

    try:
        result = await storage.store_for(bucket_name).get_async(object_path)
        return bytes(await result.bytes_async())
    except FileNotFoundError:
        _LOGGER.error(f"File not found: {document_url}")
        raise HTTPException(status_code=404, detail=f"File not found: {document_url}")
    except ObjectStoreError as e:
        _LOGGER.error(f"Error downloading file content from {document_url}: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {document_url}")
