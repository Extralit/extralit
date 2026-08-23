import hashlib
import logging
import mimetypes
import shutil
from datetime import timedelta
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


class ObjectStorage:
    """One obstore store per workspace, each scoped to `{root}/{workspace}/`.

    Every caller addresses objects by workspace name and a key under it; this is the only place that
    knows whether that lands on a bucket prefix or a directory.
    """

    def __init__(self) -> None:
        self.root = settings.storage_root
        self._stores: dict[str, S3Store | LocalStore] = {}

    @property
    def signable(self) -> bool:
        """Only S3 can presign; `LocalStore` is not a `SignCapableStore`."""
        return self.root.remote

    def for_workspace(self, workspace: str) -> S3Store | LocalStore:
        # `LocalStore` happily accepts `..` in a prefix where `S3Store` rejects it, and the
        # workspace arrives from a URL path segment, so the traversal guard has to be here.
        if not workspace or workspace in (".", "..") or "/" in workspace or "\\" in workspace:
            raise ValueError(f"Invalid workspace name: {workspace!r}")
        store = self._stores.get(workspace)
        if store is None:
            store = self._build(workspace)
            self._stores[workspace] = store
        return store

    def _prefix(self, workspace: str) -> str:
        return f"{self.root.prefix}/{workspace}".strip("/")

    def _build(self, workspace: str) -> S3Store | LocalStore:
        if not self.root.remote:
            return LocalStore(prefix=self.root.local_path / workspace, mkdir=True)

        return S3Store(self.root.bucket, prefix=self._prefix(workspace), **self._s3_config())

    def _s3_config(self) -> dict[str, Any]:
        # Without keys obstore resolves credentials itself: IMDS, IRSA, ECS, or AWS_* env vars.
        config: dict[str, Any] = {
            "region": settings.s3_region or "us-east-1",
            "virtual_hosted_style_request": False,
            "client_options": {"allow_http": self.root.scheme == "http"},
        }
        if self.root.endpoint:
            config["endpoint"] = self.root.endpoint
        if settings.s3_access_key:
            config["access_key_id"] = settings.s3_access_key
            config["secret_access_key"] = settings.s3_secret_key
        return config

    def lance_uri(self, workspace: str, subdir: str) -> str:
        """Where Lance datasets for a workspace live, addressed exactly like its objects."""
        if not self.root.remote:
            return str(self.root.local_path / workspace / subdir)
        return f"s3://{self.root.bucket}/{self._prefix(workspace)}/{subdir}"

    def lance_storage_options(self) -> dict[str, str] | None:
        if not self.root.remote:
            return None
        options = {
            "aws_region": settings.s3_region or "us-east-1",
            "allow_http": str(self.root.scheme == "http").lower(),
            "aws_virtual_hosted_style_request": "false",
        }
        if self.root.endpoint:
            options["aws_endpoint"] = self.root.endpoint
        if settings.s3_access_key:
            options["aws_access_key_id"] = settings.s3_access_key
            options["aws_secret_access_key"] = settings.s3_secret_key or ""
        return options

    async def healthy(self) -> bool:
        """The root is reachable with the configured credentials."""
        try:
            if not self.root.remote:
                # A local root is reachable if it can exist; nothing has created it until the
                # first workspace is written.
                self.root.local_path.mkdir(parents=True, exist_ok=True)
                return True
            store = S3Store(self.root.bucket, prefix=self.root.prefix or None, **self._s3_config())
            await store.list_with_delimiter_async()
            return True
        except Exception as e:
            _LOGGER.warning(f"Storage root {settings.storage_url} is unreachable: {e}")
            return False

    def forget(self, workspace: str) -> None:
        """Drop the cached store, so the next access rebuilds it (and remakes its directory)."""
        self._stores.pop(workspace, None)

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


def _object_metadata(workspace: str, meta: Any, attributes: Any = None) -> ObjectMetadata:
    key = meta["path"]
    return ObjectMetadata(
        workspace=workspace,
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


def get_proxy_document_url(workspace: str, object_path: str) -> str:
    return f"/api/v1/file/{workspace}/{object_path}"


def split_document_url(document_url: str) -> tuple[str, str]:
    """Split `/api/v1/file/{workspace}/{object}` back into workspace and key."""
    prefix = "/api/v1/file/"
    if not document_url.startswith(prefix):
        raise ValueError(f"Invalid document URL format: {document_url}")

    parts = document_url[len(prefix) :].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid document URL format: {document_url}")

    return parts[0], parts[1]


async def get_presigned_url_from_document_url(storage: ObjectStorage, document_url: str, expires: int = 3600) -> str:
    """Presign a `/api/v1/file/{workspace}/{object}` URL, valid for `expires` seconds.

    Local storage cannot sign, so it keeps serving through the proxy route.
    """
    try:
        workspace, object_path = split_document_url(document_url)
    except ValueError:
        _LOGGER.warning(f"Invalid document URL format: {document_url}")
        return document_url

    if not storage.signable:
        return document_url

    try:
        return await obstore.sign_async(
            storage.for_workspace(workspace), "GET", object_path, timedelta(seconds=expires)
        )
    except Exception as e:
        _LOGGER.error(f"Error generating presigned URL from document URL {document_url}: {e}")
        return document_url


async def list_objects(
    storage: ObjectStorage,
    workspace: str,
    prefix: str | None = None,
    recursive=True,
    start_after: str | None = None,
) -> ListObjectsResponse:
    """List objects in a workspace and return as ListObjectsResponse."""
    store = storage.for_workspace(workspace)
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
        return ListObjectsResponse(objects=[_object_metadata(workspace, meta) for meta in metas])
    except FileNotFoundError:
        _LOGGER.error(f"Workspace '{workspace}' not found")
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace}' not found")
    except ObjectStoreError as e:
        _LOGGER.error(f"Error listing objects in workspace {workspace}: {e}")
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace}' not found")


async def get_object(storage: ObjectStorage, workspace: str, object: str) -> FileObjectResponse:
    """Get an object and return it as a FileObjectResponse whose `response` streams."""
    try:
        result = await storage.for_workspace(workspace).get_async(object)
        return FileObjectResponse(
            response=result,
            metadata=_object_metadata(workspace, result.meta, result.attributes),
        )
    except FileNotFoundError:
        _LOGGER.error(f"Object {object} not found in workspace {workspace}")
        raise HTTPException(status_code=404, detail=f"Object {object} not found in workspace {workspace}")
    except ObjectStoreError as e:
        _LOGGER.error(f"Error getting object {object} from workspace {workspace}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def _put(
    storage: ObjectStorage,
    workspace: str,
    key: str,
    data: bytes,
    content_type: str,
    metadata: dict[str, Any] | None = None,
):
    attributes = {"Content-Type": content_type, **{k: str(v) for k, v in (metadata or {}).items()}}
    store = storage.for_workspace(workspace)
    if isinstance(store, LocalStore):
        # LocalStore rejects attributes outright; the content type is recovered from the key.
        return await store.put_async(key, data)

    return await store.put_async(key, data, attributes=attributes)


async def put_object(
    storage: ObjectStorage,
    workspace: str,
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
        result = await _put(storage, workspace, object, data, content_type, metadata)

        return ObjectMetadata(
            workspace=workspace,
            object_name=object,
            etag=(result["e_tag"] or "").strip('"') or None,
            size=len(data),
            content_type=content_type,
            metadata=metadata or {},
        )
    except ObjectStoreError as e:
        _LOGGER.error(f"Error putting object {object} in workspace {workspace}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error putting object {object} in workspace {workspace}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def delete_object(storage: ObjectStorage, workspace: str, object: str):
    """Delete an object. Deleting a key that is already gone is not an error."""
    try:
        await storage.for_workspace(workspace).delete_async(object)
    except FileNotFoundError:
        pass
    except ObjectStoreError as e:
        _LOGGER.error(f"Error deleting object {object} from workspace {workspace}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e!s}")
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from workspace {workspace}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


async def delete_workspace_objects(storage: ObjectStorage, workspace: str) -> None:
    """Remove everything under the workspace prefix."""
    store = storage.for_workspace(workspace)
    async for batch in store.list():
        await store.delete_async([meta["path"] for meta in batch])
    if isinstance(store, LocalStore):
        shutil.rmtree(store.prefix, ignore_errors=True)
        storage.forget(workspace)


async def delete_document_artifacts(storage: ObjectStorage, workspace: str, document_id: UUID | str) -> None:
    """Remove every artifact of a document: PDF, thumbnail, layout JSON and layout rows.

    Best effort — the DB rows are already gone by the time this runs, so a storage hiccup leaves a
    leaked object rather than a document the caller cannot delete. A leak here is negligible and can
    be ignored: the objects are unreachable and layout rows only survive until the document is
    re-parsed or a sweeper runs.
    """
    from extralit_server.contexts.ocr import storage as layout_storage

    for object_path in (get_pdf_s3_object_path(document_id), get_thumbnail_s3_object_path(document_id)):
        try:
            await delete_object(storage, workspace, object_path)
        except Exception as e:
            _LOGGER.warning(f"Could not delete {object_path} for document {document_id}: {e}")

    try:
        await layout_storage.delete_layout(storage, workspace, document_id)
    except Exception as e:
        _LOGGER.warning(f"Could not delete layout artifacts for document {document_id}: {e}")


async def put_document_file(
    storage: ObjectStorage,
    workspace: str,
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
        existing_files = await list_objects(storage, workspace, prefix=object_path, recursive=False)

        should_upload = True
        if existing_files.objects:
            new_file_hash = compute_hash(file_data)
            existing_hashes = [
                existing_file.etag for existing_file in existing_files.objects if existing_file.etag is not None
            ]

            if new_file_hash in existing_hashes:
                should_upload = False

        if should_upload:
            await _put(storage, workspace, object_path, file_data, content_type, metadata)

            return get_proxy_document_url(workspace, object_path)

        return None

    except Exception as e:
        _LOGGER.error(f"Error uploading document file {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {e!s}")


async def download_file_content(storage: ObjectStorage, document_url: str) -> bytes:
    """Download the whole body behind a `/api/v1/file/{workspace}/{object}` URL."""
    workspace, object_path = split_document_url(document_url)

    try:
        result = await storage.for_workspace(workspace).get_async(object_path)
        return bytes(await result.bytes_async())
    except FileNotFoundError:
        _LOGGER.error(f"File not found: {document_url}")
        raise HTTPException(status_code=404, detail=f"File not found: {document_url}")
    except ObjectStoreError as e:
        _LOGGER.error(f"Error downloading file content from {document_url}: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {document_url}")
