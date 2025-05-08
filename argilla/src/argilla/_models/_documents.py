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
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Document(BaseModel):
    """A document in a workspace."""

    id: Optional[UUID] = None
    workspace_id: UUID
    file_path: Optional[str] = None
    url: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_server_payload(self) -> dict:
        """Convert the document to a server payload."""
        return {
            "workspace_id": str(self.workspace_id),
            "url": self.url,
            "pmid": self.pmid,
            "doi": self.doi,
        }
