from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from urllib3._collections import HTTPHeaderDict


class ObjectMetadata(BaseModel):
    bucket_name: str
    object_name: str
    last_modified: datetime | None = None
    is_latest: bool | None = None
    etag: str | None = None
    size: int | None = None
    content_type: str | None = None
    version_id: str | None = None
    version_tag: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", mode="before")
    def parse_metadata(cls, v):
        if v and isinstance(v, HTTPHeaderDict | dict):
            v = {key[11:]: value for key, value in v.items() if key.lower().startswith("x-amz-meta-")}
        else:
            v = None
        return v


class ListObjectsResponse(BaseModel):
    objects: Iterable[ObjectMetadata] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.objects)  # type: ignore

    def __getitem__(self, index) -> ObjectMetadata:
        return self.objects[index]  # type: ignore

    def __iter__(self):
        return iter(self.objects)

    @field_validator("objects")
    def assign_version_id(cls, objects: list[ObjectMetadata]) -> list[ObjectMetadata]:
        # Group objects by object_name
        grouped_objects = defaultdict(list)
        for obj in objects:
            grouped_objects[obj.object_name].append(obj)

        # Assign version_id based on last_modified
        for _object_name, object_list in grouped_objects.items():
            sorted_objects = sorted(object_list, key=lambda o: o.last_modified or datetime.min)

            for i, obj in enumerate(sorted_objects):
                obj.version_tag = f"v{i + 1}"
                if obj.is_latest is None:
                    obj.is_latest = i == len(sorted_objects) - 1

        # Flatten the list of objects
        objects = [obj for object_list in grouped_objects.values() for obj in object_list]

        return objects


class FileObjectResponse(BaseModel):
    # The S3 body is a streaming object whose concrete type varies by client/version
    # (urllib3 HTTPResponse via minio; StreamingBody / StreamingChecksumBody via
    # aiobotocore). Consumers only stream it (`await .response.read()`), so keep the
    # annotation permissive — a strict type triggers pydantic is_instance_of 422s.
    response: Any
    metadata: ObjectMetadata
    versions: ListObjectsResponse | None

    class Config:
        arbitrary_types_allowed = True

    @property
    def version_tag(self) -> str | None:
        if not self.metadata or not self.versions:
            return ""
        else:
            for version in self.versions:
                if version.version_id == self.metadata.version_id:
                    return version.version_tag
        return ""

    @property
    def is_latest(self) -> bool | None:
        if not self.metadata or not self.versions:
            return None
        else:
            for version in self.versions:
                if version.version_id == self.metadata.version_id:
                    return version.is_latest
        return None

    @property
    def http_headers(self) -> dict[str, str]:
        if not self.metadata:
            return {}

        headers = {
            "Content-Type": str(self.metadata.content_type) if self.metadata.content_type else "",
            "ETag": str(self.metadata.etag) if self.metadata.etag else "",
            "Version-Id": str(self.metadata.version_id) if self.metadata.version_id else "",
            "Last-Modified": self.metadata.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")
            if self.metadata.last_modified
            else "",
            "Is-Latest": str(self.is_latest).lower() if self.is_latest is not None else "",
            "Version-Tag": self.version_tag,
        }
        headers = {key: value for key, value in headers.items() if value}
        return headers

    @field_validator("response")
    def validate_response(cls, v):
        if v is None:
            raise ValueError("Response cannot be None")
        return v
