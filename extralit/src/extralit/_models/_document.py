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

import os
from typing import Any, Optional
from urllib.parse import unquote, urlparse
from uuid import UUID

from pydantic import Field, field_serializer

from extralit._models._base import ResourceModel


class DocumentModel(ResourceModel):
    """Schema for the `Document` model.

    Args:
        id: The unique identifier of the document. Optional.
        workspace_id: The workspace ID to which the document belongs. Required.
        reference: A reference to the document, e.g., an identifier. Required.
        url: The URL of the document. Optional.
        file_name: The file name of the document. Optional.
        file_path: The local file path of the document. Optional.
        doi: The DOI of the document. Optional.
        pmid: The PMID of the document. Optional.
        metadata: Additional metadata for the document. Optional.
    """

    workspace_id: UUID = Field(..., description="The workspace ID to which the document belongs to")
    reference: str = Field(..., description="A reference to the document, e.g., an identifier.")
    url: Optional[str] = None
    file_name: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None, description="Local file path")
    doi: Optional[str] = None
    pmid: Optional[str] = None
    metadata: Optional[dict] = None

    @classmethod
    def from_file(
        cls,
        file_path_or_url: str,
        *,
        reference: str,
        workspace_id: UUID,
        id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> "DocumentModel":
        url = None

        if os.path.exists(file_path_or_url):
            file_name = file_path_or_url.split("/")[-1]

        elif urlparse(file_path_or_url).scheme:
            url = file_path_or_url
            file_path_or_url = None  # type: ignore[assignment]
            parsed_url = urlparse(url)
            path = parsed_url.path
            file_name = unquote(path).split("/")[-1]

        else:
            raise ValueError(f"File path {file_path_or_url} does not exist")

        return cls(
            id=id,
            workspace_id=workspace_id,
            file_name=file_name if isinstance(file_name, str) else None,
            file_path=file_path_or_url,
            reference=reference,
            url=url if isinstance(url, str) else None,
            **kwargs,
        )

    @field_serializer("workspace_id", when_used="unless-none")
    def serialize_workspace_id(self, value: UUID) -> str:
        return str(value)

    def to_server_payload(self) -> dict[str, Any]:
        json = {
            "file_name": self.file_name,
            "reference": self.reference,
            "url": self.url,
            "workspace_id": str(self.workspace_id),
            "pmid": self.pmid,
            "doi": self.doi,
        }
        if self.id is not None:
            json["id"] = str(self.id)

        return json


# Backwards compatibility alias
Document = DocumentModel
