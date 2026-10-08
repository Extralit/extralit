from datetime import datetime
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ObjectMetadata(BaseModel):
    """Metadata for an object in a workspace."""

    model_config = ConfigDict(populate_by_name=True)

    # `bucket_name` is what servers older than the one-storage-root change send.
    workspace: str = Field(validation_alias=AliasChoices("workspace", "bucket_name"))
    object_name: str
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ListObjectsResponse(BaseModel):
    """Response for listing objects in a workspace."""

    objects: list[ObjectMetadata] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.objects)

    def __getitem__(self, index) -> ObjectMetadata:
        return self.objects[index]

    def __iter__(self):
        return iter(self.objects)


class FileObjectResponse(BaseModel):
    """Response for getting a file from a workspace."""

    content: bytes
    metadata: Optional[ObjectMetadata] = None
