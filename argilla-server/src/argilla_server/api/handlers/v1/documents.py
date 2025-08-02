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

import json
import logging
from uuid import UUID, uuid4
from typing import TYPE_CHECKING, List

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, Path, status, Security
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from argilla_server.database import get_async_db
from argilla_server.models.database import Document
from argilla_server.security import auth
from argilla_server.models import User, Workspace
from argilla_server.contexts import datasets, files, imports
from argilla_server.api.policies.v1 import DocumentPolicy, authorize
from argilla_server.api.schemas.v1.documents import DocumentCreate, DocumentDelete, DocumentListItem, DocumentUpdate
from argilla_server.api.schemas.v1.imports import DocumentsBulkResponse, DocumentsBulkCreate

if TYPE_CHECKING:
    from argilla_server.models import Document

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=UUID)
async def add_document(
    *,
    document_create: DocumentCreate = Depends(),
    file_data: UploadFile = File(None),
    db: AsyncSession = Depends(get_async_db),
    client: Minio = Depends(files.get_minio_client),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, DocumentPolicy.create())

    workspace = await Workspace.get(db, document_create.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{document_create.workspace_id}` not found",
        )

    if not document_create.id:
        document_create.id = uuid4()

    if file_data is not None:
        object_path = files.get_pdf_s3_object_path(document_create.id)
        existing_files = files.list_objects(
            client, workspace.name, prefix=object_path, include_version=False, recursive=False
        )
        # file_data_bytes = base64.b64decode(file_data)
        file_data_bytes = await file_data.read()

        put_object = False

        if existing_files.objects:
            new_file_hash = files.compute_hash(file_data_bytes)
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
                data=file_data_bytes,
                size=len(file_data_bytes),
                content_type="application/pdf",
                metadata=document_create.dict(include={"file_name": True, "pmid": True, "doi": True}),
            )

            document_create.url = files.get_s3_object_url(response.bucket_name, response.object_name)
            if file_data.filename and not document_create.file_name:
                document_create.file_name = file_data.filename

    existing_document = await imports.check_existing_document(db, document_create)
    if existing_document is not None:
        return existing_document.id

    new_document = DocumentCreate(
        id=document_create.id,
        reference=document_create.reference,
        pmid=document_create.pmid,
        doi=document_create.doi,
        url=document_create.url,
        file_name=document_create.file_name,
        workspace_id=document_create.workspace_id,
        metadata=document_create.metadata,
    )

    document = await datasets.create_document(db, new_document)

    return document.id


@router.get("/documents/by-pmid/{pmid}", response_model=DocumentListItem)
async def get_document_by_pmid(
    *, db: AsyncSession = Depends(get_async_db), pmid: str, current_user: User = Security(auth.get_current_user)
):
    if pmid is None or not isinstance(pmid, str) or not pmid.isnumeric():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with pmid `{pmid}` not found",
        )

    query = await db.execute(select(Document).where(Document.pmid == pmid))
    await authorize(current_user, DocumentPolicy.get())

    documents = query.fetchone()
    if documents is None or len(documents) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with pmid `{pmid}` not found",
        )

    document: Document = documents[0]
    return DocumentListItem.model_validate(document)


@router.get("/documents/by-id/{id}", response_model=DocumentListItem)
async def get_document_by_id(
    *,
    id: UUID = Path(..., title="The UUID of the document to get"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
):
    if id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )

    query = await db.execute(select(Document).where(Document.id == id))
    await authorize(current_user, DocumentPolicy.get())

    documents = query.fetchone()
    if documents is None or len(documents) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )

    document: Document = documents[0]
    return DocumentListItem.model_validate(document)


@router.patch("/documents/{id}", response_model=DocumentListItem)
async def update_document(
    *,
    id: UUID = Path(..., title="The UUID of the document to update"),
    document_update: DocumentUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
):
    """Update a document by ID."""
    # First, get the document to ensure it exists and check permissions
    query = await db.execute(select(Document).where(Document.id == id))
    result = query.fetchone()

    if result is None or len(result) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )

    document: Document = result[0]
    await authorize(current_user, DocumentPolicy.get())

    # Update the document fields
    update_data = document_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(document, field):
            setattr(document, field, value)

    # Save the changes
    await datasets.update_document(db, document)

    return DocumentListItem.model_validate(document)


@router.delete(
    "/documents/workspace/{workspace_id}",
    status_code=status.HTTP_200_OK,
    response_model=int,
    description="Delete a specific document by id only",
)
async def delete_documents_by_workspace_id(
    *,
    workspace_id: UUID,
    document_delete: DocumentDelete = Body(None),
    db: AsyncSession = Depends(get_async_db),
    client: Minio = Depends(files.get_minio_client),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, DocumentPolicy.delete(workspace_id))

    if not document_delete or not document_delete.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document ID is required for deletion")

    workspace = await Workspace.get(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id `{workspace_id}` not found",
        )

    documents = await datasets.delete_documents(
        db,
        workspace_id,
        id=document_delete.id,
    )

    _LOGGER.info(f"Deleting {len(documents)} documents")
    for document in documents:
        object_path = files.get_pdf_s3_object_path(document.id)
        files.delete_object(client, workspace.name, object_path)

    return len(documents)


@router.get(
    "/documents/workspace/{workspace_id}", status_code=status.HTTP_200_OK, response_model=List[DocumentListItem]
)
async def list_documents(
    *, 
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID = Path(..., title="The UUID of the workspace whose documents will be retrieved"),
    current_user: User = Security(auth.get_current_user),
) -> List[DocumentListItem]:
    await authorize(current_user, DocumentPolicy.list(workspace_id))

    documents = await datasets.list_documents(db, workspace_id)

    return documents


@router.post("/documents/bulk", status_code=status.HTTP_201_CREATED, response_model=DocumentsBulkResponse)
async def create_documents_bulk(
    *,
    documents_metadata: str = Form(..., description="JSON string matching the DocumentsBulkCreate schema"),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
) -> DocumentsBulkResponse:
    """
    Bulk upload documents with associated PDF files.

        - `documents_metadata`: JSON string matching the DocumentsBulkCreate schema.
        Example:
        {
            "documents": [
                {
                    "reference": "ref1",
                    "document_create": { ... },
                    "associated_file": "file1.pdf"
                }
            ]
        }
        - `files`: List of PDF files to upload.

    It processes the documents in batches and returns job IDs for tracking.
    """
    try:
        metadata_dict = json.loads(documents_metadata)
        bulk_create = DocumentsBulkCreate.model_validate(metadata_dict)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON in documents_metadata",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid metadata format: {str(e)}",
        )

    if not bulk_create.documents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No documents provided for upload",
        )

    workspace_ids = {doc.document_create.workspace_id for doc in bulk_create.documents}
    for workspace_id in workspace_ids:
        workspace = await Workspace.get(db, workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Workspace with id `{workspace_id}` not found",
            )
        await authorize(current_user, DocumentPolicy.bulk_create(workspace_id))

    return await imports.process_bulk_upload(bulk_create=bulk_create, files=files, user_id=str(current_user.id))
