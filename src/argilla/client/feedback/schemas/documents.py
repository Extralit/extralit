import os
import base64
from urllib.parse import urlparse, unquote
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, Extra
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

    doi: Optional[str] = None
    pmid: Optional[str] = None
    file_name: str = Field(...)
    url: Optional[str] = None
    file_data: Optional[str] = Field(None, description="Base64 encoded file data")
    workspace_id: Optional[UUID] = Field(None, description="The workspace ID to which the document belongs to")
    id: Optional[UUID] = Field(None, description="The ID of the document, which gets assigned after databse insertion")

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        json_encoders = {
            UUID: str
        }

    @classmethod
    def from_file(cls, file_path: str, id: Optional[str] = None, pmid: Optional[str] = None, doi: Optional[str] = None, workspace_id: Optional[UUID] = None) -> "Document":
        assert doi or id or pmid, "Either `pmid`, `doi`, or `id` must be provided"
        url = None

        if os.path.exists(file_path):
            with open(file_path, "rb") as file:
                file_data = base64.b64encode(file.read()).decode()
            file_name = file_path.split("/")[-1]

        elif urlparse(file_path).scheme:
            file_data = None
            url = file_path
            parsed_url = urlparse(file_path)
            path = parsed_url.path
            file_name = unquote(path).split('/')[-1]
        else:
            raise ValueError(f"File path {file_path} does not exist")

        return cls(
            file_data=file_data,
            file_name=file_name if isinstance(file_name, str) else None,
            url=url if isinstance(url, str) else None,
            id=UUID(id) if isinstance(id, str) else None,
            pmid=str(pmid) if isinstance(pmid, int) or isinstance(pmid, str) and len(pmid)>3 else None,
            doi=doi if isinstance(doi, str) else None,
            workspace_id=workspace_id,
        )

    def to_server_payload(self) -> Dict[str, Any]:
        """Method that will be used to create the payload that will be sent to Argilla
        to create a field in the `FeedbackDataset`.
        """
        json = {
            "file_data": self.file_data,
            "url": self.url,
            "file_name": self.file_name,
            "pmid": self.pmid,
            "doi": self.doi,
            "workspace_id": str(self.workspace_id),
        }
        if self.id:
            json["id"] = str(self.id)

        return json

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, file_name={self.file_name!r}, pmid={self.pmid!r}, doi={self.doi!r}, workspace_id={self.workspace_id!r})"