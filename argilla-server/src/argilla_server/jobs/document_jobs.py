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

"""Document upload job functions."""

import logging
from typing import Dict, Any

from rq import Retry

from argilla_server.jobs import job, DEFAULT_QUEUE, JOB_TIMEOUT_DISABLED
from argilla_server.api.schemas.v1.documents import DocumentCreate
from argilla_server.models.database import Document
from argilla_server.contexts import datasets, files, imports
from argilla_server.database import get_async_db

_LOGGER = logging.getLogger(__name__)


@job(DEFAULT_QUEUE, timeout=JOB_TIMEOUT_DISABLED, retry=Retry(max=3))
async def upload_document_job(document_data: Dict[str, Any], file_data: bytes, user_id: str) -> Dict[str, Any]:
    """
    Asynchronous job to upload a document with its associated file.

    This job reuses the existing document upload logic from the POST /documents endpoint
    but runs asynchronously in the job queue.

    Args:
        document_data: Dictionary containing DocumentCreate data
        file_data: Binary content of the PDF file
        user_id: ID of the user who initiated the upload

    Returns:
        Dictionary with upload result (document_id or error)
    """
    try:
        # Convert document_data to DocumentCreate
        document_create = DocumentCreate.model_validate(document_data)

        # Get database session
        async with get_async_db() as db:
            # Check if document already exists
            existing_document = await imports.check_existing_document(db, document_create)
            if existing_document is not None:
                return {
                    "success": True,
                    "document_id": str(existing_document.id),
                    "status": "existing",
                    "message": "Document already exists",
                }

            # Get minio client
            client = files.get_minio_client()

            # Get workspace
            from argilla_server.models import Workspace

            workspace = await Workspace.get(db, document_create.workspace_id)
            if not workspace:
                return {"success": False, "error": f"Workspace with id `{document_create.workspace_id}` not found"}

            # Upload file to S3
            object_path = files.get_pdf_s3_object_path(document_create.id)

            # Check if file already exists with same hash
            existing_files = files.list_objects(
                client, workspace.name, prefix=object_path, include_version=False, recursive=False
            )

            put_object = False

            if existing_files.objects:
                new_file_hash = files.compute_hash(file_data)
                existing_hashes = [
                    existing_file.etag.strip('"')
                    for existing_file in existing_files.objects
                    if existing_file.etag is not None
                ]

                if new_file_hash not in existing_hashes:
                    put_object = True
            else:
                put_object = True

            if put_object:
                response = files.put_object(
                    client,
                    bucket=workspace.name,
                    object=object_path,
                    data=file_data,
                    size=len(file_data),
                    content_type="application/pdf",
                    metadata=document_create.model_dump(include={"file_name": True, "pmid": True, "doi": True}),
                )

                document_create.url = files.get_s3_object_url(response.bucket_name, response.object_name)

            # Create document in database
            new_document = Document(
                id=document_create.id,
                reference=document_create.reference,
                pmid=document_create.pmid,
                doi=document_create.doi,
                url=document_create.url,
                file_name=document_create.file_name,
                workspace_id=document_create.workspace_id,
            )

            document = await datasets.create_document(db, new_document)

            return {
                "success": True,
                "document_id": str(document.id),
                "status": "created",
                "message": "Document created successfully",
            }

    except Exception as e:
        _LOGGER.error(f"Error in upload_document_job: {str(e)}")
        return {"success": False, "error": str(e)}
