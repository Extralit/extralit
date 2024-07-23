from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic.v1 import BaseModel, Field, Extra


class ObjectMetadata(BaseModel):
    bucket_name: str
    object_name: str
    last_modified: Optional[datetime]
    is_latest: Optional[bool]
    etag: Optional[str]
    size: Optional[int]
    content_type: Optional[str]
    version_id: Optional[str]
    version_tag: Optional[str]
    metadata: Optional[Dict[str, Any]]


class ListObjectsResponse(BaseModel):
    objects: List[ObjectMetadata] = Field(default_factory=list)


class FileObject(BaseModel):
    """Schema for the `FileObject` model.

    Args:
        file_data: The file data of the document. Required.
        metadata: The metadata of the current file. Optional.
        versions: The metadata of other file versions. Optional.
    """

    file_data: Optional[bytes] = Field(None, description="Base64 encoded file data", repr=False)
    metadata: Optional[ObjectMetadata]
    versions: Optional[ListObjectsResponse]

    class Config:
        validate_assignment = True
        json_encoders = {
            UUID: str
        }

    def to_server_payload(self) -> Dict[str, Any]:
        """Method that will be used to create the payload that will be sent to the server."""
        return {
            "file_data": self.file_data,
            "metadata": self.metadata.dict(),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(metadata={self.metadata!r})"