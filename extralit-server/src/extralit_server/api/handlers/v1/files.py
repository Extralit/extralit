import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Security, UploadFile
from fastapi.responses import Response, StreamingResponse

from extralit_server.api.policies.v1 import FilePolicy, authorize
from extralit_server.api.schemas.v1.files import ListObjectsResponse, ObjectMetadata
from extralit_server.contexts import files
from extralit_server.models import User
from extralit_server.security import auth

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["files"])


@router.get("/file/{bucket}/{object:path}")
async def get_file(
    *,
    bucket: str,
    object: str,
    range_header: str | None = Header(None, alias="range"),
    if_none_match: str | None = Header(None, alias="if-none-match"),
    storage=Depends(files.get_storage),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, FilePolicy.get(bucket))

    store = storage.store_for(bucket)

    try:
        head = await store.get_async(object, options={"head": True})
        content_length = head.meta["size"]
        etag = (head.meta["e_tag"] or "").strip('"')
        content_type = files.content_type_of(object, head.attributes)

        # Handle ETag for caching
        if if_none_match and etag and if_none_match.strip('"') == etag:
            return Response(status_code=304)

        # Prepare headers for caching and CORS
        headers = {
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "ETag": f'"{etag}"',
            "Access-Control-Allow-Origin": "*",  # Allow CORS for file access
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, If-None-Match",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range, ETag",
            "Accept-Ranges": "bytes",
        }

        # PDF-specific optimizations
        if content_type == "application/pdf":
            headers.update(
                {
                    "Content-Disposition": "inline",
                    "X-Content-Type-Options": "nosniff",
                }
            )

        # Handle range requests for partial content
        if range_header and content_length:
            try:
                # Parse range header (e.g., "bytes=0-1023")
                range_match = range_header.replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else content_length - 1

                # Validate range
                if start >= content_length or end >= content_length or start > end:
                    headers["Content-Range"] = f"bytes */{content_length}"
                    return Response(status_code=416, headers=headers)

                # An HTTP range is inclusive of `end`; obstore's is exclusive.
                result = await store.get_async(object, options={"range": (start, end + 1)})

                # Update headers for partial content
                headers["Content-Range"] = f"bytes {start}-{end}/{content_length}"
                headers["Content-Length"] = str(end - start + 1)

                return StreamingResponse(
                    result.stream(),
                    status_code=206,
                    media_type=content_type,
                    headers=headers,
                )
            except (ValueError, IndexError):
                # Invalid range header, serve full content
                pass

        result = await store.get_async(object)
        return StreamingResponse(result.stream(), media_type=content_type, headers=headers)

    except FileNotFoundError:
        _LOGGER.error(f"Object '{bucket}/{object}' not found")
        raise HTTPException(status_code=404, detail=f"No object at path '{object}' was found")
    except Exception as e:
        _LOGGER.error(f"Error getting object '{bucket}/{object}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.options("/file/{bucket}/{object:path}")
async def options_file(bucket: str, object: str):
    """Handle CORS preflight requests for file access"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, If-None-Match, Content-Type",
            "Access-Control-Max-Age": "3600",
            "Accept-Ranges": "bytes",
        }
    )


@router.post("/file/{bucket}/{object:path}", response_model=ObjectMetadata)
async def put_file(
    *,
    bucket: str,
    object: str,
    file: Annotated[UploadFile, File()],
    storage=Depends(files.get_storage),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, FilePolicy.put_object(bucket))

    try:
        file_data = await file.read()
        response = await files.put_object(
            storage,
            bucket,
            object,
            data=file_data,
            content_type=file.content_type or "application/octet-stream",
        )
        return response
    except Exception as e:
        _LOGGER.error(f"Error uploading file to {bucket}/{object}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e!s}")


@router.get("/files/{bucket}/{prefix:path}", response_model=ListObjectsResponse)
async def list_objects_endpoint(
    *,
    bucket: str,
    prefix: str,
    recursive: bool = True,
    start_after: str | None = None,
    storage=Depends(files.get_storage),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, FilePolicy.list(bucket))

    try:
        objects = await files.list_objects(
            storage,
            bucket,
            prefix=prefix,
            recursive=recursive,
            start_after=start_after,
        )
        return objects
    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error listing objects in '{bucket}/{prefix}': {e}")
        raise HTTPException(status_code=500, detail=f"Error listing objects: {e!s}")


@router.delete("/file/{bucket}/{object:path}")
async def delete_files(
    *,
    bucket: str,
    object: str,
    storage=Depends(files.get_storage),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, FilePolicy.delete(bucket))

    try:
        await files.delete_object(storage, bucket, object)
        return {"message": "File deleted"}
    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error deleting file {bucket}/{object}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e!s}")
