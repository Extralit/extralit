from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from minio.datatypes import Object
from argilla_server.pydantic_v1 import BaseModel, Field, validator
from urllib3 import HTTPResponse
from urllib3._collections import HTTPHeaderDict
from minio.helpers import ObjectWriteResult

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

    @validator('metadata', pre=True)
    def parse_metadata(cls, v):
        if v and isinstance(v, (HTTPHeaderDict, dict)):
            v = {
                key[11:]: value
                for key, value in v.items()
                if key.lower().startswith('x-amz-meta-')
            }
        else:
            v = None
        return v

    @classmethod
    def from_minio_object(cls, minio_object: Object):
        return cls(
            bucket_name=minio_object.bucket_name,
            object_name=minio_object.object_name,
            last_modified=minio_object.last_modified,
            is_latest=None if minio_object.is_latest is None else minio_object.is_latest.lower() == 'true',
            etag=minio_object.etag,
            size=minio_object.size,
            content_type=minio_object.content_type,
            version_id=minio_object.version_id,
            metadata=minio_object.metadata,
        )
    
    @classmethod
    def from_minio_write_response(cls, write_result: ObjectWriteResult):
        return cls(
            bucket_name=write_result.bucket_name,
            object_name=write_result.object_name,
            last_modified=write_result.last_modified,
            is_latest=True,
            etag=write_result.etag,
            size=None,
            content_type=write_result.http_headers.get('Content-Type'),
            version_id=write_result.version_id,
            metadata=write_result.http_headers,
        )

class ListObjectsResponse(BaseModel):
    objects: List[ObjectMetadata] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.objects)

    def __getitem__(self, index) -> ObjectMetadata:
        return self.objects[index]
    
    def __iter__(self):
        return iter(self.objects)

    @validator('objects', pre=True, each_item=True)
    def convert_objects(cls, v):
        if isinstance(v, Object):
            return ObjectMetadata.from_minio_object(v)
        return v
    
    @validator('objects', each_item=False)
    def assign_version_id(cls, objects: List[ObjectMetadata]) -> List[ObjectMetadata]:
        # Group objects by object_name
        grouped_objects = defaultdict(list)
        for obj in objects:
            grouped_objects[obj.object_name].append(obj)

        # Assign version_id based on last_modified
        for object_name, object_list in grouped_objects.items():
            sorted_objects = sorted(object_list, key=lambda o: o.last_modified)

            for i, obj in enumerate(sorted_objects):
                obj.version_tag = f"v{i + 1}"
                if obj.is_latest is None:
                    obj.is_latest = (i == len(sorted_objects) - 1)

        # Flatten the list of objects
        objects = [obj for object_list in grouped_objects.values() for obj in object_list]

        return objects
    

class FileObjectResponse(BaseModel):
    response: HTTPResponse
    metadata: Optional[ObjectMetadata]
    versions: Optional[ListObjectsResponse]

    class Config:
        arbitrary_types_allowed = True

    @property
    def version_tag(self) -> str:
        if not self.metadata or not self.versions:
            return ''
        else:
            for version in self.versions:
                if version.version_id == self.metadata.version_id:
                    return version.version_tag
        return ''
    
    @property
    def is_latest(self) -> Optional[bool]:
        if not self.metadata or not self.versions:
            return None
        else:
            for version in self.versions:
                if version.version_id == self.metadata.version_id:
                    return version.is_latest
        return None

    @property
    def http_headers(self) -> Dict[str, str]:
        if not self.metadata:
            return {}
        
        headers = {
            "Content-Type": str(self.metadata.content_type) if self.metadata.content_type else "",
            "ETag": str(self.metadata.etag) if self.metadata.etag else "",
            "Version-Id": str(self.metadata.version_id) if self.metadata.version_id else "",
            "Last-Modified": self.metadata.last_modified.strftime('%Y-%m-%dT%H:%M:%SZ') if self.metadata.last_modified else "",
            "Is-Latest": str(self.is_latest).lower() if self.is_latest is not None else "",
            "Version-Tag": self.version_tag,
        }
        headers = {key: value for key, value in headers.items() if value}
        return headers

    @validator('response')
    def validate_response(cls, v):
        if v is None:
            raise ValueError("Response cannot be None")
        return v

    @validator('metadata', 'versions', pre=True, each_item=True)
    def convert_minio_object(cls, v):
        if isinstance(v, Object):
            return ObjectMetadata.from_minio_object(v)
        return v




