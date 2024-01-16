import base64
from io import BytesIO
from uuid import UUID
from typing import TYPE_CHECKING, Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Path, status, Security
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, or_, select

from argilla.server.database import get_async_db
from argilla.server.models.database import Document
from argilla.server.security import auth
from argilla.server.policies import DocumentPolicy, authorize, is_authorized
from argilla.server.models import User
from argilla.server.contexts import accounts, datasets
from argilla.server.schemas.v1.documents import DocumentCreate, DocumentListItem

if TYPE_CHECKING:
    from argilla.server.models import Document

router = APIRouter(tags=["documents"])

async def check_existing_document(db: AsyncSession, document_create: DocumentCreate):
    # Add conditions for non-empty attributes
    conditions = []
    if document_create.pmid:
        conditions.append(Document.pmid == document_create.pmid)
    if document_create.url:
        conditions.append(Document.url == document_create.url)
    if document_create.doi:
        conditions.append(Document.doi == document_create.doi)
    if document_create.file_name:
        conditions.append(Document.file_name == document_create.file_name)

    if not conditions:
        return None

    # Check if a document with the same pmid, url, or doi already exists
    existing_document = await db.execute(
        select(Document).where(or_(*conditions))
    )
    existing_document = existing_document.scalars().first()

    return existing_document


@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=UUID)
async def upload_document(
    *,
    db: AsyncSession = Depends(get_async_db),
    document_create: DocumentCreate,
    current_user: User = Security(auth.get_current_user)
):
    await authorize(current_user, DocumentPolicy.get())

    if not await accounts.get_workspace_by_id(db, document_create.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workspace with id `{document_create.workspace_id}` not found",
        )
    
    existing_document = await check_existing_document(db, document_create)
    if existing_document is not None:
        print("Document already exists", existing_document.id)
        return existing_document.id
    
    # If a file is uploaded, use it. Otherwise, use the file_data from the DocumentCreate model
    document = None
    if document is not None:
        file_name = document.filename
        file_data_bytes = await document.read()
    else:
        if document_create.file_data is not None:
            file_data_bytes = base64.b64decode(document_create.file_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file was uploaded and no file_data was provided in the request body",
            )

    new_document = Document(pmid=document_create.pmid, 
                            doi=document_create.doi,
                            url=document_create.url,
                            file_name=document_create.file_name or file_name, 
                            file_data=file_data_bytes,
                            workspace_id=document_create.workspace_id)
    document = await datasets.create_document(db, new_document)
    
    return document.id

@router.get("/documents/by-pmid/{pmid}", responses={200: {"content": {"application/pdf": {}}}})
async def get_document_by_pmid(
    *,
    db: AsyncSession = Depends(get_async_db),
    pmid: str,
    current_user: User = Security(auth.get_current_user)
):
    if pmid is None or not isinstance(pmid, str) or not pmid.isnumeric():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with pmid `{pmid}` not found",
        )
    
    query = await db.execute(
        select(Document).where(Document.pmid == pmid)
    )
    await authorize(current_user, DocumentPolicy.get())

    documents = query.fetchone()
    if documents is None or len(documents) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with pmid `{pmid}` not found",
        )
    
    document: Document = documents[0]

    return StreamingResponse(
        BytesIO(document.file_data), 
        headers={
            "Content-Disposition": f'attachment; filename="{document.file_name}"',
            "X-Document-ID": str(document.id),
            "X-Document-File-Name": document.file_name,
        },
        media_type="application/pdf"
    )

@router.get("/documents/by-id/{id}", responses={200: {"content": {"application/pdf": {}}}})
async def get_document_by_id(
    *,
    db: AsyncSession = Depends(get_async_db),
    id: UUID = Path(..., title="The UUID of the document to get"),
    current_user: User = Security(auth.get_current_user)
):
    if id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )
    
    query = await db.execute(
        select(Document).where(Document.id == id)
    )
    await authorize(current_user, DocumentPolicy.get())

    documents = query.fetchone()
    if documents is None or len(documents) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )
    
    document: Document = documents[0]

    return StreamingResponse(
        BytesIO(document.file_data), 
        headers={
            "Content-Disposition": f'attachment; filename="{document.file_name}"',
            "X-Document-ID": str(document.id),
            "X-Document-File-Name": document.file_name,
        },
        media_type="application/pdf"
    )

@router.delete("/documents/workspace/{workspace_id}", status_code=status.HTTP_200_OK)
async def delete_documents_by_workspace_id(*,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID = Path(..., title="The UUID of the workspace whose documents will all be deleted"),
    current_user: User = Security(auth.get_current_user)
    ):
    await authorize(current_user, DocumentPolicy.delete())

    await datasets.delete_documents(db, workspace_id)


@router.get("/documents/workspace/{workspace_id}", status_code=status.HTTP_200_OK, 
            response_model=List[DocumentListItem])
async def list_documents(*,
    db: AsyncSession = Depends(get_async_db),
    workspace_id: UUID = Path(..., title="The UUID of the workspace whose documents will be retrieved"),
    current_user: User = Security(auth.get_current_user)
    ) -> List[Document]:
    await authorize(current_user, DocumentPolicy.list())

    documents = await datasets.list_documents(db, workspace_id)

    return documents