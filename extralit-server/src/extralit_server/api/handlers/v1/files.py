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

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, Security, UploadFile
from fastapi.responses import Response, StreamingResponse
from minio import Minio, S3Error

from extralit_server.api.policies.v1 import FilePolicy, authorize
from extralit_server.api.schemas.v1.files import ListObjectsResponse, ObjectMetadata
from extralit_server.contexts import files
from extralit_server.contexts.files import LocalFileStorage
from extralit_server.models import User
from extralit_server.security import auth

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["files"])


@router.get("/file/{bucket}/{object:path}")
async def get_file(
    *,
    bucket: str,
    object: str,
    request: Request,
    version_id: str | None = None,
    range_header: str | None = Header(None, alias="range"),
    if_none_match: str | None = Header(None, alias="if-none-match"),
    client: Minio | LocalFileStorage = Depends(files.get_minio_client),
    current_user: User | None = Security(auth.get_optional_current_user),
):
    # TODO LocalFileStorage currently needs to disable authorization checks since clients cannot access the bucket directly.
    if current_user is not None and isinstance(client, Minio):
        await authorize(current_user, FilePolicy.get(bucket))

    try:
        file_response = files.get_object(client, bucket, object, version_id=version_id, include_versions=True)

        # Handle ETag for caching
        etag = file_response.metadata.etag
        if if_none_match and etag and if_none_match.strip('"') == etag.strip('"'):
            return Response(status_code=304)

        # Prepare headers for caching and CORS
        headers = {
            **file_response.http_headers,
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "ETag": f'"{etag}"' if etag else None,
            "Access-Control-Allow-Origin": "*",  # Allow CORS for file access
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, If-None-Match",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range, ETag",
            "Accept-Ranges": "bytes",
        }

        # PDF-specific optimizations
        if file_response.metadata.content_type == "application/pdf":
            headers.update(
                {
                    "Content-Disposition": "inline",
                    "X-Content-Type-Options": "nosniff",
                    "Cache-Control": "public, max-age=3600",
                }
            )

        # Remove None values
        headers = {k: v for k, v in headers.items() if v is not None}

        # Handle range requests for partial content
        content_length = file_response.metadata.size
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

                # Update headers for partial content
                headers["Content-Range"] = f"bytes {start}-{end}/{content_length}"
                headers["Content-Length"] = str(end - start + 1)

                return StreamingResponse(
                    file_response.response,
                    status_code=206,
                    media_type=file_response.metadata.content_type,
                    headers=headers,
                )
            except (ValueError, IndexError):
                # Invalid range header, serve full content
                pass

        return StreamingResponse(
            file_response.response, media_type=file_response.metadata.content_type, headers=headers
        )
    except S3Error as se:
        _LOGGER.error(f"Error getting object '{bucket}/{object}': {se}")
        raise HTTPException(status_code=404, detail=f"No object at path '{object}' was found") from se

    except Exception as e:
        _LOGGER.error(f"Error getting object '{bucket}/{object}': {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    client: Minio | LocalFileStorage = Depends(files.get_minio_client),
    current_user: User = Security(auth.get_current_user),
):
    # Check if the current user is in the workspace to have access to the s3 bucket of the same name
    await authorize(current_user, FilePolicy.put_object(bucket))

    try:
        response = files.put_object(
            client,
            bucket,
            object,
            data=file.file,
            size=file.size,  # type: ignore
            content_type=file.content_type,  # type: ignore
        )
        return response
    except S3Error as se:
        raise HTTPException(status_code=500, detail=f"Internal server error: {se.message}") from se


@router.get("/files/{bucket}/{prefix:path}", response_model=ListObjectsResponse)
async def list_objects(
    *,
    bucket: str,
    prefix: str,
    include_version=True,
    recursive=True,
    start_after: str | None = None,
    client: Minio | LocalFileStorage = Depends(files.get_minio_client),
    current_user: User = Security(auth.get_optional_current_user),
):
    # Check if the current user is in the workspace to have access to the s3 bucket of the same name
    await authorize(current_user, FilePolicy.list(bucket))

    try:
        objects = files.list_objects(
            client, bucket, prefix=prefix, include_version=include_version, recursive=recursive, start_after=start_after
        )
        return objects
    except S3Error as se:
        _LOGGER.error(f"Error listing objects in '{bucket}/{prefix}': {se}")
        if se.code == "NoSuchBucket":
            raise HTTPException(
                status_code=404,
                detail=f"Bucket '{bucket}' not found, please run `ex.Workspace.create('{bucket}')` to create the S3 bucket.",
            ) from se
        else:
            raise HTTPException(
                status_code=404, detail=f"Cannot list objects as '{bucket}/{prefix}' is not found"
            ) from se
    except Exception as e:
        raise e


@router.delete("/file/{bucket}/{object:path}")
async def delete_files(
    *,
    bucket: str,
    object: str,
    version_id: str | None = None,
    client: Minio | files.LocalFileStorage = Depends(files.get_minio_client),
    current_user: User = Security(auth.get_current_user),
):
    # Check if the current user is in the workspace to have access to the s3 bucket of the same name
    await authorize(current_user, FilePolicy.delete(bucket))

    try:
        files.delete_object(client, bucket, object, version_id=version_id)
        return {"message": "File deleted"}
    except S3Error as se:
        raise HTTPException(status_code=500, detail="Internal server error") from se
    except Exception as e:
        raise e
