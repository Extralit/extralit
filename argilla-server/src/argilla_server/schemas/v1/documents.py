from uuid import UUID, uuid4
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from argilla_server.pydantic_v1 import BaseModel, Field

class DocumentCreate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    reference: Optional[str]
    url: Optional[str]
    file_data: Optional[bytes] = Field(None, description='A serializable bytes string that needs to be base64 decoded', repr=False)  # Expect a base64 encoded string
    file_name: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]


class DocumentDelete(BaseModel):
    id: Optional[Union[UUID, str]] = None
    url: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None


class DocumentListItem(BaseModel):
    id: UUID
    reference: Optional[str]
    url: Optional[str]
    file_name: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    workspace_id: UUID

    class Config:
        orm_mode = True