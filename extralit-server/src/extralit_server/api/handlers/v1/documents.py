import json
import logging
from typing import TYPE_CHECKING, Annotated
from uuid import UUID, uuid4

from docling_core.types.doc.document import CURRENT_VERSION
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Path, Query, Security, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import DocumentPolicy, authorize
from extralit_server.api.schemas.v1.document.layout import DocumentLayoutOut
from extralit_server.api.schemas.v1.documents import DocumentCreate, DocumentDelete, DocumentListItem, DocumentUpdate
from extralit_server.api.schemas.v1.imports import DocumentsBulkCreate, DocumentsBulkResponse
from extralit_server.contexts import files, imports
from extralit_server.contexts.ocr import storage
from extralit_server.contexts.ocr.projection import project_layout
from extralit_server.database import get_async_db
from extralit_server.models import User, Workspace
from extralit_server.models.database import Document
from extralit_server.security import auth
from extralit_server.workflows.documents import create_document_workflow

if TYPE_CHECKING:
    from extralit_server.models import Document

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=UUID)
async def add_document(
    *,
    document_create: Annotated[str, Form()],
    file_data: Annotated[UploadFile | None, File()] = None,
    db: AsyncSession = Depends(get_async_db),
    s3_client=Depends(files.get_s3_client),
    current_user: User = Security(auth.get_current_user),
):
    await authorize(current_user, DocumentPolicy.create())
    try:
        document_dict = json.loads(document_create)
        document_new: DocumentCreate = DocumentCreate.model_validate(document_dict)  # pyright: ignore[reportAssignmentType]
    except json.JSONDecodeError as e:
        _LOGGER.error(f"JSON decode error: {e}. \n Input: {document_create}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON in document_create",
        )

    workspace = await Workspace.get(db, document_new.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{document_new.workspace_id}` not found",
        )

    if not document_new.id:
        document_new.id = uuid4()

    existing_documents = await imports.query_documents(
        db=db,
        workspace_id=document_new.workspace_id,
        document_id=document_new.id,
        reference=document_new.reference,
        file_name=document_new.file_name,
        url=document_new.url,
        limit=1,
    )
    if existing_documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document already exists in workspace with: {existing_documents[0].model_dump(include=['id', 'reference', 'file_name', 'url', 'pmid', 'doi'], exclude_none=True)!s}",
        )

    if file_data is not None:
        if file_data.filename and not document_new.file_name:
            document_new.file_name = file_data.filename

        file_url = await files.put_document_file(
            s3_client=s3_client,
            workspace_name=workspace.name,
            document_id=document_new.id,  # type: ignore[arg-type]
            file_data=await file_data.read(),
            filename=file_data.filename or "",
            content_type=file_data.content_type or "application/octet-stream",
        )

        if file_url:
            document_new.url = file_url

    new_document = DocumentCreate(
        id=document_new.id,
        reference=document_new.reference,
        pmid=document_new.pmid,
        doi=document_new.doi,
        url=document_new.url,
        file_name=document_new.file_name,
        workspace_id=document_new.workspace_id,
        metadata=document_new.metadata,
    )

    document = await imports.create_document(db, new_document)

    try:
        if document_new.url:
            await create_document_workflow(
                document_id=document.id,
                s3_url=document.url,
                reference=document.reference,
                workspace_name=workspace.name,
                workspace_id=workspace.id,
            )
    except Exception as e:
        _LOGGER.error(f"Failed to start workflow for document {new_document.id}: {e}")

    return document.id


@router.get("/documents", description="Get documents by ID, PMID, DOI, or reference.")
async def get_document(
    *,
    workspace_id: Annotated[UUID, Query(description="Workspace ID")],
    id: Annotated[UUID | None, Query(description="Document ID")] = None,
    reference: Annotated[str | None, Query(description="Document reference")] = None,
    pmid: Annotated[str | None, Query(description="PubMed ID")] = None,
    doi: Annotated[str | None, Query(description="DOI")] = None,
    limit: Annotated[int | None, Query(description="Maximum number of documents to return")] = None,
    db: AsyncSession = Depends(get_async_db),
    s3_client=Depends(files.get_s3_client),
    current_user: User = Security(auth.get_current_user),
) -> list[DocumentListItem]:
    await authorize(current_user, DocumentPolicy.get())

    if not any([id, pmid, doi, reference]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of id, pmid, doi, or reference must be provided",
        )

    documents = await imports.query_documents(
        db=db,
        workspace_id=workspace_id,
        document_id=id,
        pmid=pmid,
        doi=doi,
        reference=reference,
        limit=limit,
    )

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No documents found with reference {reference}",
        )

    # TODO disable due to CORS restrictions from frontend
    # for document in documents:
    #     document.url = files.get_presigned_url_from_document_url(
    #         client=client,
    #         document_url=document.url,
    #         expires=3600,
    #     )

    return documents


@router.patch("/documents/{id}", response_model=DocumentListItem, description="Update a document by ID.")
async def update_document(
    *,
    id: Annotated[UUID, Path(title="The UUID of the document to update")],
    document_update: DocumentUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Security(auth.get_current_user),
):
    query = await db.execute(select(Document).where(Document.id == id))
    result = query.fetchone()

    if result is None or len(result) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )

    document: Document = result[0]
    await authorize(current_user, DocumentPolicy.get())

    update_data = document_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(document, field):
            setattr(document, field, value)

    await imports.update_document(db, document)

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
    document_delete: Annotated[DocumentDelete | None, Body()] = None,
    db: AsyncSession = Depends(get_async_db),
    s3_client=Depends(files.get_s3_client),
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

    documents = await imports.delete_documents(
        db,
        workspace_id,
        id=document_delete.id,
    )

    _LOGGER.info(f"Deleting {len(documents)} documents")
    for document in documents:
        object_path = files.get_pdf_s3_object_path(document.id)
        await files.delete_object(s3_client, workspace.name, object_path)

    return len(documents)


@router.get("/documents/workspace/{workspace_id}", status_code=status.HTTP_200_OK)
async def list_documents(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    workspace_id: Annotated[UUID, Path(title="The UUID of the workspace whose documents will be retrieved")],
    current_user: User = Security(auth.get_current_user),
) -> list[DocumentListItem]:
    await authorize(current_user, DocumentPolicy.list(workspace_id))

    documents = await imports.list_documents(db, workspace_id)

    return documents


@router.get(
    "/documents/{document_id}/layout",
    status_code=status.HTTP_200_OK,
    description="Get the extracted layout of a document, with per-item page regions.",
)
async def get_document_layout(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    document_id: Annotated[UUID, Path(title="The UUID of the document whose layout will be retrieved")],
    pages: Annotated[list[int] | None, Query(description="1-indexed pages to include")] = None,
    labels: Annotated[list[str] | None, Query(description="DocItemLabels to include, e.g. `table`")] = None,
    s3_client=Depends(files.get_s3_client),
    current_user: User = Security(auth.get_current_user),
) -> DocumentLayoutOut:
    await authorize(current_user, DocumentPolicy.get())

    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{document_id}` not found",
        )

    workspace = await Workspace.get(db, document.workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id `{document.workspace_id}` not found",
        )

    layout_metadata = (document.metadata_ or {}).get("layout_metadata")
    if not layout_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No layout has been extracted for document `{document_id}`",
        )

    try:
        doc = await storage.load_layout(
            s3_client,
            workspace.name,
            document_id,
            object_path=layout_metadata.get("layout_url"),
        )
    except ValidationError as e:
        # A layout written by a newer docling-core cannot be read back by this server.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stored layout is not readable by docling-core {CURRENT_VERSION}: {e}",
        ) from e
    except Exception as e:
        _LOGGER.error(f"Error loading layout for document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layout for document `{document_id}` could not be loaded",
        ) from e

    return project_layout(doc, document_id, pages=pages, labels=labels)


@router.post("/documents/bulk", status_code=status.HTTP_201_CREATED)
async def create_documents_bulk(
    *,
    documents_metadata: Annotated[str, Form(description="JSON string matching the DocumentsBulkCreate schema")],
    files: Annotated[list[UploadFile], File()],
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
    except json.JSONDecodeError as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON in documents_metadata",
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid metadata format: {e!s}",
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
