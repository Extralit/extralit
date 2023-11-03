from io import BytesIO
from uuid import UUID
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Path, status, Security
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, or_, select

from argilla.server.database import get_async_db
from argilla.server.models.database import Document
from argilla.server.security import auth
from argilla.server.policies import DocumentPolicy, authorize, is_authorized
from argilla.server.models import User

if TYPE_CHECKING:
    from argilla.server.models import Document

router = APIRouter(tags=["documents"])

@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=UUID)
async def upload_document(
    *,
    db: AsyncSession = Depends(get_async_db),
    document: UploadFile,
    pmid: str,
    current_user: User = Security(auth.get_current_user)
):
    await authorize(current_user, DocumentPolicy.get())
    
    # Assuming file_name is derived from the uploaded file
    file_name = document.filename
    file_data = await document.read()
    new_document = Document(pmid=pmid, file_name=file_name, file_data=file_data)
    db.add(new_document)
    await db.commit()
    
    return new_document.id

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