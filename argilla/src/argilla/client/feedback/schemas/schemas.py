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


class FileObject(BaseModel):
    """Schema for the `FileObject` model.

    Args:
        file_data: The file data of the document. Required.
        metadata: The metadata of the file. Required.
    """

    file_data: Optional[bytes] = Field(None, description="Base64 encoded file data", repr=False)
    metadata: ObjectMetadata
    versions: List[ObjectMetadata]

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