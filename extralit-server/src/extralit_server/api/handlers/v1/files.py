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

import logging
from typing import Annotated

from botocore.exceptions import ClientError
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
    version_id: str | None = None,
    range_header: str | None = Header(None, alias="range"),
    if_none_match: str | None = Header(None, alias="if-none-match"),
    s3_client=Depends(files.get_s3_client),
    current_user: User | None = Security(auth.get_optional_current_user),
):
    if current_user is not None:
        await authorize(current_user, FilePolicy.get(bucket))

    try:
        # Get object metadata first
        head_response = await s3_client.head_object(Bucket=bucket, Key=object)
        content_length = head_response["ContentLength"]
        etag = head_response["ETag"].strip('"')
        content_type = head_response.get("ContentType", "application/octet-stream")

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

                # Get object with range
                response = await s3_client.get_object(Bucket=bucket, Key=object, Range=f"bytes={start}-{end}")

                # Update headers for partial content
                headers["Content-Range"] = f"bytes {start}-{end}/{content_length}"
                headers["Content-Length"] = str(end - start + 1)

                return StreamingResponse(
                    response["Body"],
                    status_code=206,
                    media_type=content_type,
                    headers=headers,
                )
            except (ValueError, IndexError):
                # Invalid range header, serve full content
                pass

        # Get full object
        response = await s3_client.get_object(Bucket=bucket, Key=object)

        # Use chunked streaming for large files
        if content_length > files.CHUNK_LENGTH_MB:
            file_chunks = files.get_file_chunk(s3_client, bucket, object, files.CHUNK_LENGTH_MB)
            return StreamingResponse(file_chunks, media_type=content_type, headers=headers)

        return StreamingResponse(response["Body"], media_type=content_type, headers=headers)

    except ClientError as e:
        if e.response["Error"]["Code"] in {"NoSuchKey", "404"}:
            _LOGGER.error(f"Object '{bucket}/{object}' not found")
            raise HTTPException(status_code=404, detail=f"No object at path '{object}' was found")
        else:
            _LOGGER.error(f"Error getting object '{bucket}/{object}': {e.response['Error']}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
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
    s3_client=Depends(files.get_s3_client),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, FilePolicy.put_object(bucket))

    try:
        file_data = await file.read()
        response = await files.put_object(
            s3_client,
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
    include_version=True,
    recursive=True,
    start_after: str | None = None,
    s3_client=Depends(files.get_s3_client),
    current_user: User = Security(auth.get_optional_current_user),
):
    await authorize(current_user, FilePolicy.list(bucket))

    try:
        objects = await files.list_objects(
            s3_client,
            bucket,
            prefix=prefix,
            include_version=include_version,
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
    version_id: str | None = None,
    s3_client=Depends(files.get_s3_client),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, FilePolicy.delete(bucket))

    try:
        await files.delete_object(s3_client, bucket, object, version_id=version_id)
        return {"message": "File deleted"}
    except HTTPException:
        raise
    except Exception as e:
        _LOGGER.error(f"Error deleting file {bucket}/{object}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e!s}")
