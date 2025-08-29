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
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union
from urllib.parse import unquote, urlparse
from uuid import UUID

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from extralit._api._documents import DocumentsAPI
from extralit._models._document import DocumentModel
from extralit._resource import Resource
from extralit.client import Extralit

if TYPE_CHECKING:
    pass

__all__ = ["Document"]


class Document(Resource):
    """Class for interacting with Extralit documents.

    Attributes:
        workspace_id (UUID): The ID of the workspace that contains this document.
        file_name (str): The name of the uploaded file.
        reference (str): A reference identifier for the document.
        url (str): The URL of the document if created from URL.
        pmid (str): The PubMed ID of the document.
        doi (str): The DOI of the document.
        file_path (str): The local file path (used during creation).
    """

    _api: "DocumentsAPI"

    def __init__(
        self,
        workspace_id: UUID,
        reference: str,
        file_name: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
        url: Optional[str] = None,
        pmid: Optional[str] = None,
        doi: Optional[str] = None,
        id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
        client: Optional["Extralit"] = None,
    ) -> None:
        """Initializes a Document object.

        Parameters:
            workspace_id (UUID): The workspace ID to which this document belongs (required).
            reference (str): A reference identifier for the document (required).
            file_name (str): The name of the document file.
            file_path (Union[str, Path]): Local path to the document file.
            url (str): The URL of the document.
            pmid (str): The PubMed ID of the document.
            doi (str): The DOI of the document.
            id (UUID): The document ID. If provided, the document will be created with this ID.
            client (Extralit): The client used to interact with Extralit.

        Returns:
            Document: The initialized document object.
        """
        client = client or Extralit._get_default()
        super().__init__(client=client, api=client.api.documents)

        self._model: DocumentModel = DocumentModel(
            id=id,
            workspace_id=workspace_id,
            file_name=file_name,
            file_path=str(file_path) if file_path else None,
            reference=reference,
            url=url,
            pmid=pmid,
            doi=doi,
            metadata=metadata,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(reference={self.reference!r}, file_name={self.file_name!r}, url={self.url!r}, pmid={self.pmid!r}, doi={self.doi!r}, metadata={(self.metadata or {}).keys()!r})"

    @classmethod
    def from_file(
        cls,
        file_path_or_url: Union[str, Path],
        *,
        reference: str,
        workspace_id: UUID,
        pmid: Optional[str] = None,
        doi: Optional[str] = None,
        client: Optional["Extralit"] = None,
    ) -> "Document":
        """Create a Document from a file path or URL.

        Args:
            file_path_or_url: Local file path or URL to the document.
            reference: A reference identifier for the document.
            workspace_id: The workspace ID to which this document belongs.
            pmid: The PubMed ID of the document.
            doi: The DOI of the document.
            client: The client used to interact with Extralit.

        Returns:
            Document: The created document object.

        Raises:
            ValueError: If the file path does not exist or URL is invalid, or if required parameters are missing.
        """
        if not workspace_id:
            raise ValueError("workspace_id is required")

        if not reference:
            raise ValueError("reference is required")

        if isinstance(file_path_or_url, Path):
            file_path_or_url = str(file_path_or_url)

        url = None
        file_path = None

        if os.path.exists(file_path_or_url):
            file_path = file_path_or_url
            file_name = os.path.basename(file_path_or_url)
        elif urlparse(file_path_or_url).scheme:
            url = file_path_or_url
            parsed_url = urlparse(url)
            path = parsed_url.path
            file_name = unquote(path).split("/")[-1]
        else:
            raise ValueError(f"File path {file_path_or_url} does not exist")

        return cls(
            workspace_id=workspace_id,
            reference=reference,
            file_name=file_name,
            file_path=file_path,
            url=url,
            pmid=pmid,
            doi=doi,
            client=client,
        )

    @classmethod
    def from_model(cls, model: DocumentModel, client: "Extralit") -> "Document":
        """Create a Document from a DocumentModel.

        Args:
            model: The document model.
            client: The client used to interact with Extralit.

        Returns:
            Document: The created document object.
        """
        instance = cls(
            workspace_id=model.workspace_id,
            file_name=model.file_name,
            file_path=model.file_path,
            reference=model.reference,
            url=model.url,
            pmid=model.pmid,
            doi=model.doi,
            id=model.id,
            metadata=model.metadata,
            client=client,
        )
        instance._model = model
        return instance

    @classmethod
    def get(
        cls,
        workspace_id: UUID,
        id: Optional[UUID] = None,
        client: Optional["Extralit"] = None,
    ) -> "Document":
        """Get a document by ID, PMID, DOI, reference, or workspace_id.

        Args:
            workspace_id: The workspace ID (required).
            id: The document ID (expects exactly one match).
            pmid: The PubMed ID (returns first match if multiple exist).
            doi: The DOI (returns first match if multiple exist).
            reference: The document reference (returns first match if multiple exist).
            client: The client used to interact with Extralit.

        Returns:
            Document: The document object. For ID searches, ensures exactly one match.
                     For other criteria, returns the first match.

        Raises:
            ValueError: If workspace_id is not provided, if none of id, pmid, doi, or reference is provided,
                       if no documents are found, or if multiple documents found when searching by ID.

        Note:
            If you need all documents matching non-ID criteria, use workspace.documents() instead.
        """
        if not workspace_id:
            raise ValueError("workspace_id is required")

        client = client or Extralit._get_default()

        # Build parameters object
        params = {"workspace_id": str(workspace_id)}
        if id:
            params["id"] = str(id)

        if len(params) <= 1:  # Only workspace_id is provided
            raise ValueError("At least `id` must be provided in addition to `workspace_id`")

        models: list[DocumentModel] = client.api.documents.get(params)
        if not models:
            raise ValueError("No documents found with the provided criteria")

        return cls.from_model(models[0], client)

    ############################
    # Properties
    ############################

    @property
    def workspace_id(self) -> Optional[UUID]:
        return self._model.workspace_id

    @workspace_id.setter
    def workspace_id(self, value: UUID) -> None:
        self._model.workspace_id = value

    @property
    def file_name(self) -> Optional[str]:
        return self._model.file_name

    @file_name.setter
    def file_name(self, value: str) -> None:
        self._model.file_name = value

    @property
    def file_path(self) -> Optional[str]:
        return self._model.file_path

    @file_path.setter
    def file_path(self, value: str) -> None:
        self._model.file_path = value

    @property
    def reference(self) -> Optional[str]:
        return self._model.reference

    @reference.setter
    def reference(self, value: str) -> None:
        self._model.reference = value

    @property
    def url(self) -> Optional[str]:
        return self._model.url

    @url.setter
    def url(self, value: str) -> None:
        self._model.url = value

    @property
    def pmid(self) -> Optional[str]:
        return self._model.pmid

    @pmid.setter
    def pmid(self, value: str) -> None:
        self._model.pmid = value

    @property
    def doi(self) -> Optional[str]:
        return self._model.doi

    @doi.setter
    def doi(self, value: str) -> None:
        self._model.doi = value

    @property
    def metadata(self) -> Optional[dict]:
        return self._model.metadata

    @metadata.setter
    def metadata(self, value: dict) -> None:
        self._model.metadata = value

    ############################
    # Resource overrides
    ############################

    def delete(self) -> None:
        """Delete this document from the server.

        Raises:
            ValueError: If the document doesn't have an ID or workspace_id.
        """
        if not self.id:
            raise ValueError("Cannot delete document without an ID")
        if not self.workspace_id:
            raise ValueError("Cannot delete document without a workspace_id")

        self._api.delete(self.id, self.workspace_id)
        self._update_last_api_call()
        self._log_message(f"Document deleted: {self}")

    def _with_client(self, client: "Extralit") -> "Self":
        return Document.from_model(self._model, client)  # type: ignore[return-value]
