from uuid import UUID
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from pydantic import BaseModel

class DocumentCreate(BaseModel):
    url: Optional[str]
    file_data: Optional[bytes]  # Expect a base64 encoded string
    file_name: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    workspace_id: UUID  # The workspace ID to which the document belongs to
    id: Optional[UUID]

class DocumentListItem(BaseModel):
    id: UUID
    url: Optional[str]
    file_name: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    workspace_id: UUID