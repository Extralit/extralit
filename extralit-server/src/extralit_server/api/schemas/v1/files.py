from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from urllib3._collections import HTTPHeaderDict


class ObjectMetadata(BaseModel):
    bucket_name: str
    object_name: str
    last_modified: datetime | None = None
    etag: str | None = None
    size: int | None = None
    content_type: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", mode="before")
    def parse_metadata(cls, v):
        if v and isinstance(v, HTTPHeaderDict | dict):
            v = {key[11:]: value for key, value in v.items() if key.lower().startswith("x-amz-meta-")}
        else:
            v = None
        return v


class ListObjectsResponse(BaseModel):
    objects: list[ObjectMetadata] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.objects)

    def __getitem__(self, index) -> ObjectMetadata:
        return self.objects[index]

    def __iter__(self):
        return iter(self.objects)


class FileObjectResponse(BaseModel):
    # The S3 body is a streaming object whose concrete type varies by client/version
    # (urllib3 HTTPResponse via minio; StreamingBody / StreamingChecksumBody via
    # aiobotocore). Consumers only stream it (`await .response.read()`), so keep the
    # annotation permissive — a strict type triggers pydantic is_instance_of 422s.
    response: Any
    metadata: ObjectMetadata

    class Config:
        arbitrary_types_allowed = True

    @property
    def http_headers(self) -> dict[str, str]:
        if not self.metadata:
            return {}

        headers = {
            "Content-Type": str(self.metadata.content_type) if self.metadata.content_type else "",
            "ETag": str(self.metadata.etag) if self.metadata.etag else "",
            "Last-Modified": self.metadata.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")
            if self.metadata.last_modified
            else "",
        }
        headers = {key: value for key, value in headers.items() if value}
        return headers

    @field_validator("response")
    def validate_response(cls, v):
        if v is None:
            raise ValueError("Response cannot be None")
        return v
