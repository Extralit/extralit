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
import os
from typing import Dict, Any, List, Tuple
from uuid import UUID, uuid4

from rq import Retry
from rq.decorators import job

from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs import DEFAULT_QUEUE, JOB_TIMEOUT_DISABLED
from extralit_server.api.schemas.v1.documents import DocumentCreate
from extralit_server.contexts import files, imports

_LOGGER = logging.getLogger(__name__)


@job(DEFAULT_QUEUE, timeout=JOB_TIMEOUT_DISABLED, retry=Retry(max=3, interval=[10, 30, 60]))
async def upload_reference_documents_job(
    reference: str,
    reference_data: Dict[str, Any],
    file_data_list: List[Tuple[str, bytes]],  # List of (filename, file_data) tuples
    user_id: UUID,
) -> Dict[str, Any]:
    """
    Asynchronous job to upload multiple documents for a single reference.

    This job processes multiple files for a single reference in one job,
    creating separate document records for each file while maintaining
    the reference relationship. It reuses existing document upload logic
    and provides detailed error reporting for each file.

    Args:
        reference: BibTeX reference key for tracking
        document_data: Dictionary containing DocumentCreate data (shared metadata)
        file_data_list: List of (filename, file_data) tuples for multiple files
        user_id: UUID of the user creating the documents

    Returns:
        Dictionary with upload results including document_ids or errors for each file
    """
    temp_files = []
    results = {
        "reference": reference,
        "success": True,
        "files": {},  # filename -> result mapping
        "total_files": len(file_data_list),
        "successful_files": 0,
        "failed_files": 0,
        "errors": [],
    }

    try:
        document_create = DocumentCreate.model_validate(reference_data)

        async with AsyncSessionLocal() as db:
            from extralit_server.models import Workspace

            workspace = await Workspace.get(db, document_create.workspace_id)
            if not workspace:
                error_msg = f"Workspace with id `{document_create.workspace_id}` not found"
                _LOGGER.error(error_msg)
                results["success"] = False
                results["errors"].append(error_msg)
                return results

            client = files.get_minio_client()
            if client is None:
                error_msg = "Failed to get minio client"
                _LOGGER.error(error_msg)
                results["success"] = False
                results["errors"].append(error_msg)
                return results

            # Process each file for this reference
            for filename, file_data in file_data_list:
                file_result = {
                    "filename": filename,
                    "success": False,
                    "document_id": None,
                    "status": None,
                    "error": None,
                }

                try:
                    # Create a unique document for each file
                    file_metadata = {"collections": (document_create.metadata or {}).get("collections", [])}

                    file_document_create = DocumentCreate(
                        id=uuid4(),
                        reference=document_create.reference,
                        pmid=document_create.pmid,
                        doi=document_create.doi,
                        url=None,  # Will be set after S3 upload
                        file_name=filename,
                        workspace_id=document_create.workspace_id,
                        metadata=file_metadata,
                    )

                    existing_documents = await imports.find_existing_documents(
                        db=db,
                        workspace_id=file_document_create.workspace_id,
                        document_id=file_document_create.id,
                        file_name=file_document_create.file_name,
                    )
                    if existing_documents:
                        existing_document_id = existing_documents[0].id
                        _LOGGER.info(f"Document already exists for file {filename} with ID {existing_document_id}")
                        file_result.update(
                            {"success": True, "document_id": str(existing_document_id), "status": "existing"}
                        )
                        results["successful_files"] += 1
                        results["files"][filename] = file_result
                        continue

                    try:
                        file_url = files.put_document_file(
                            client=client,
                            workspace_name=workspace.name,
                            document_id=file_document_create.id,  # type: ignore
                            file_data=file_data,
                            filename=filename,
                            # metadata=file_document_create.model_dump(
                            #     include={"file_name": True, "pmid": True, "doi": True}
                            # ),
                        )

                        if file_url:
                            file_document_create.url = file_url
                    except Exception as e:
                        error_msg = f"Error uploading file {filename} to S3: {str(e)}"
                        _LOGGER.error(error_msg)
                        file_result["error"] = error_msg
                        results["failed_files"] += 1
                        results["files"][filename] = file_result
                        continue

                    # Create document in database
                    try:
                        document = await imports.create_document(db, file_document_create)
                        _LOGGER.info(f"Document created successfully for file {filename} with ID {document.id}")
                        file_result.update({"success": True, "document_id": str(document.id), "status": "created"})
                        results["successful_files"] += 1
                    except Exception as e:
                        error_msg = f"Error creating document for file {filename} in database: {str(e)}"
                        _LOGGER.error(error_msg)
                        file_result["error"] = error_msg
                        results["failed_files"] += 1

                except Exception as e:
                    error_msg = f"Error processing file {filename}: {str(e)}"
                    _LOGGER.error(error_msg)
                    file_result["error"] = error_msg
                    results["failed_files"] += 1

                results["files"][filename] = file_result

            results["success"] = results["failed_files"] == 0

    except Exception as e:
        error_msg = f"Error in upload_reference_documents_job for reference {reference}: {str(e)}"
        _LOGGER.error(error_msg)
        results["success"] = False
        results["errors"].append(str(e))

    finally:
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                _LOGGER.warning(f"Failed to cleanup temporary file {temp_file}: {str(e)}")

    return results
