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
from typing import TYPE_CHECKING
from uuid import UUID

from extralit._api._base import ResourceAPI
from extralit._exceptions._api import api_error_handler

if TYPE_CHECKING:
    from extralit._models._document import DocumentModel


class DocumentsAPI(ResourceAPI):
    """API client for document operations."""

    @api_error_handler
    def create(self, model: "DocumentModel") -> "DocumentModel":
        """Create a document.

        Args:
            model: The document model to create.

        Returns:
            The created document model.
        """

        url = "/api/v1/documents"
        document_payload = model.to_server_payload()

        if model.file_path:
            file_name = os.path.basename(model.file_path)
            with open(model.file_path, "rb") as file_data:
                files = {
                    "file_data": (file_name, file_data, "application/pdf"),
                }
                response = self.http_client.post(url=url, params=document_payload, files=files)
        else:
            response = self.http_client.post(url=url, params=document_payload)

        response.raise_for_status()
        document_id = UUID(response.json())

        model.id = document_id
        return model

    @api_error_handler
    def get(self, params: dict) -> list["DocumentModel"]:
        """Get documents using multiple search criteria.

        Args:
            params: Dictionary containing any combination of:
                - workspace_id: Workspace ID (required)
                - id: Document ID
                - pmid: PubMed ID
                - doi: DOI
                - reference: Document reference

        Returns:
            A list of document models matching the criteria.
        """
        from extralit._models._document import DocumentModel

        url = "/api/v1/documents"
        response = self.http_client.get(url=url, params=params)
        response.raise_for_status()

        doc_data_list = response.json()

        if not doc_data_list:
            return []

        documents = []
        for doc_data in doc_data_list:
            doc = DocumentModel(
                id=doc_data.get("id"),
                workspace_id=doc_data.get("workspace_id"),
                file_name=doc_data.get("file_name"),
                reference=doc_data.get("reference"),
                url=doc_data.get("url"),
                pmid=doc_data.get("pmid"),
                doi=doc_data.get("doi"),
                metadata=doc_data.get("metadata"),
                inserted_at=doc_data.get("inserted_at"),
                updated_at=doc_data.get("updated_at"),
                file_path=None,
            )
            documents.append(doc)

        return documents

    @api_error_handler
    def list(self, workspace_id: UUID) -> list["DocumentModel"]:
        """List documents in a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            A list of document models.
        """
        from extralit._models._document import DocumentModel

        url = f"/api/v1/documents/workspace/{workspace_id}"
        response = self.http_client.get(url=url)
        response.raise_for_status()

        documents = []
        for doc_data in response.json():
            doc = DocumentModel(
                id=doc_data.get("id"),
                workspace_id=doc_data.get("workspace_id"),
                file_name=doc_data.get("file_name"),
                reference=doc_data.get("reference"),
                url=doc_data.get("url"),
                pmid=doc_data.get("pmid"),
                doi=doc_data.get("doi"),
                inserted_at=doc_data.get("inserted_at"),
                updated_at=doc_data.get("updated_at"),
                file_path=None,
            )
            documents.append(doc)

        return documents

    @api_error_handler
    def delete(self, id: UUID, workspace_id: UUID) -> None:
        """Delete a document.

        Args:
            id: The document ID.
            workspace_id: The workspace ID.
        """
        url = f"/api/v1/documents/workspace/{workspace_id}"
        delete_data = {"id": str(id)}
        response = self.http_client.request("DELETE", url=url, json=delete_data)
        response.raise_for_status()

    @api_error_handler
    def update(self, model: "DocumentModel") -> "DocumentModel":
        """Update a document.

        Args:
            model: The document model to update.

        Returns:
            The updated document model.
        """
        from extralit._models._document import DocumentModel

        if not model.id:
            raise ValueError("Document ID is required for updates")

        url = f"/api/v1/documents/{model.id}"
        update_data = {
            "reference": model.reference,
            "pmid": model.pmid,
            "doi": model.doi,
            "file_name": model.file_name,
        }
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        response = self.http_client.patch(url=url, json=update_data)
        response.raise_for_status()

        doc_data = response.json()
        return DocumentModel(
            id=doc_data.get("id"),
            workspace_id=doc_data.get("workspace_id"),
            file_name=doc_data.get("file_name"),
            reference=doc_data.get("reference"),
            url=doc_data.get("url"),
            pmid=doc_data.get("pmid"),
            doi=doc_data.get("doi"),
            metadata=doc_data.get("metadata"),
            inserted_at=doc_data.get("inserted_at"),
            updated_at=doc_data.get("updated_at"),
            file_path=None,
        )
