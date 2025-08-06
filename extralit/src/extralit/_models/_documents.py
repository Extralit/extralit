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
from typing import Any, Dict, Optional, Union
from urllib.parse import unquote, urlparse
from uuid import UUID

from pydantic import Field

from extralit._models._base import ResourceModel


class DocumentModel(ResourceModel):
    """Schema for the `Document` model.

    Args:
        url: The URL of the document. Optional.
        file_data: The file data of the document. Required.
        file_name: The file name of the document. Required.
        pmid: The PMID of the document. Optional.
        doi: The DOI of the document. Optional.
        workspace_id: The workspace ID of the document. Required.
    """

    id: Optional[UUID] = None
    reference: str = Field(..., description="A reference to the document, e.g., an identifier.")
    workspace_id: UUID = Field(..., description="The workspace ID to which the document belongs to")
    file_name: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None, description="Local file path")
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_file(
        cls,
        file_path_or_url: str,
        *,
        reference: str,
        workspace_id: Union[UUID, str],
        id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> "DocumentModel":
        url = None

        if os.path.exists(file_path_or_url):
            file_name = file_path_or_url.split("/")[-1]

        elif urlparse(file_path_or_url).scheme:
            url = file_path_or_url
            file_path_or_url = None
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

    def to_server_payload(self) -> Dict[str, Any]:
        """Method that will be used to create the payload that will be sent to Extralit
        to create a field in the `FeedbackDataset`.
        """
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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(file_name={self.file_name!r}, url={self.url!r}, pmid={self.pmid!r}, doi={self.doi!r}, workspace_id={self.workspace_id!r})"


# Backwards compatibility alias
Document = DocumentModel
