from uuid import UUID
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Path, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, or_, select

from argilla.server.database import get_async_db
from argilla.server.models.database import Document
from argilla.server.schemas.v1.documents import DocumentCreate, DocumentResponse

if TYPE_CHECKING:
    from argilla.server.models import Document

router = APIRouter(tags=["documents"])

@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=UUID)
async def upload_document(
    *,
    db: AsyncSession = Depends(get_async_db),
    document: UploadFile,
    pmid: str,
):
    # Assuming file_name is derived from the uploaded file
    file_name = document.filename
    file_data = await document.read()
    new_document = Document(pmid=pmid, file_name=file_name, file_data=file_data)
    db.add(new_document)
    await db.commit()
    
    return new_document.id

@router.get("/documents/by-pmid/{pmid}", response_model=DocumentResponse)
async def get_document_by_pmid(
    *,
    db: AsyncSession = Depends(get_async_db),
    pmid: str
):
    document = await db.execute(
        select(Document).where(Document.pmid == pmid)
    )
    document: Document = await document.fetchone()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with pmid `{pmid}` not found",
        )

    return DocumentResponse(id=document.id, pmid=pmid, file_data=document.file_data)

@router.get("/documents/by-id/{id}", response_model=DocumentResponse)
async def get_document_by_id(
    *,
    db: AsyncSession = Depends(get_async_db),
    id: UUID = Path(..., title="The UUID of the document to get")
):
    document = await db.execute(
        select(Document).where(Document.id == id)
    )
    document: Document = await document.fetchone()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id `{id}` not found",
        )

    return DocumentResponse(id=document.id, pmid=document.pmid, file_data=document.file_data)