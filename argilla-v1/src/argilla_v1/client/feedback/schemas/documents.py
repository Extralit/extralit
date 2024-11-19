import os
import base64
from urllib.parse import urlparse, unquote
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, Union
import uuid

from argilla.pydantic_v1 import BaseModel, Field, Extra
from uuid import UUID

class Document(BaseModel, ABC):
    """Schema for the `Document` model.

    Args:
        url: The URL of the document. Optional.
        file_data: The file data of the document. Required.
        file_name: The file name of the document. Required.
        pmid: The PMID of the document. Optional.
        doi: The DOI of the document. Optional.
        workspace_id: The workspace ID of the document. Required.
    """

    id: Union[UUID, str] = Field(default_factory=uuid.uuid4(), description="The ID of the document, which gets assigned randomly if not provided.")
    file_name: str = Field(...)
    reference: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = Field(None, description="Local file path")
    workspace_id: Optional[UUID] = Field(None, description="The workspace ID to which the document belongs to")

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        json_encoders = {
            UUID: str
        }

    @classmethod
    def from_file(cls, file_path: str, *, reference: str, id: Optional[str] = None, pmid: Optional[str] = None, doi: Optional[str] = None, workspace_id: Optional[UUID] = None) -> "Document":
        url = None

        if os.path.exists(file_path):
            file_name = file_path.split("/")[-1]

        elif urlparse(file_path).scheme:
            file_path = None
            url = file_path
            parsed_url = urlparse(file_path)
            path = parsed_url.path
            file_name = unquote(path).split('/')[-1]
        else:
            raise ValueError(f"File path {file_path} does not exist")

        return cls(
            file_path=file_path,
            reference=reference,
            file_name=file_name if isinstance(file_name, str) else None,
            url=url if isinstance(url, str) else None,
            id=id or uuid.uuid4(),
            pmid=str(pmid) if isinstance(pmid, int) or isinstance(pmid, str) and len(pmid)>3 else None,
            doi=doi if isinstance(doi, str) else None,
            workspace_id=workspace_id,
        )

    def to_server_payload(self) -> Dict[str, Any]:
        """Method that will be used to create the payload that will be sent to Argilla
        to create a field in the `FeedbackDataset`.
        """
        json = {
            "url": self.url,
            "file_name": self.file_name,
            "pmid": self.pmid,
            "doi": self.doi,
            "reference": self.reference,
            "workspace_id": str(self.workspace_id),
        }
        if self.id:
            json["id"] = str(self.id)

        return json

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, file_name={self.file_name!r}, pmid={self.pmid!r}, doi={self.doi!r}, workspace_id={self.workspace_id!r})"