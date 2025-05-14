# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ObjectMetadata(BaseModel):
    """Metadata for an object in a workspace."""

    bucket_name: str
    object_name: str
    last_modified: Optional[datetime] = None
    is_latest: Optional[bool] = None
    etag: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    version_id: Optional[str] = None
    version_tag: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ListObjectsResponse(BaseModel):
    """Response for listing objects in a workspace."""

    objects: List[ObjectMetadata] = Field(default_factory=list)

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
    versions: Optional[ListObjectsResponse] = None
