from uuid import UUID, uuid4
from typing import Optional, Union
from pydantic import BaseModel, Field, ConfigDict

class DocumentCreateRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID = Field(..., description='The workspace ID where the document will be uploaded.')
    reference: Optional[str] = Field(None, description='A reference to the document.')
    url: Optional[str] = Field(None, description='A URL to the PDF document if it is public available online. If the `file_data` is uploaded, this field should be left empty.', repr=False)
    file_name: Optional[str] = Field(None, description='The name of the file.')
    pmid: Optional[str] = Field(None, description='The PubMed ID of the document.')
    doi: Optional[str] = Field(None, description='The DOI of the document.')


class DocumentDeleteRequest(BaseModel):
    id: Optional[Union[UUID, str]] = None
    url: Optional[str] = None
    pmid: Optional[str] = Field(None, description='The PubMed ID of the document.')
    doi: Optional[str] = Field(None, description='The DOI of the document.')


class DocumentListItem(BaseModel):
    id: UUID
    reference: Optional[str]
    url: Optional[str]
    file_name: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    workspace_id: UUID

    model_config = ConfigDict(from_attributes=True)
