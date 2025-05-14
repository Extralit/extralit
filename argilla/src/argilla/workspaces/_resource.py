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

from pathlib import Path
from typing import List, TYPE_CHECKING, Optional, overload, Union, Sequence, Any

from argilla._api._workspaces import WorkspacesAPI, DEFAULT_SCHEMA_S3_PATH
from argilla._helpers import GenericIterator
from argilla._helpers import LoggingMixin
from argilla._models import WorkspaceModel
from argilla._resource import Resource
from argilla.client import Argilla

if TYPE_CHECKING:
    from uuid import UUID
    from argilla.users._resource import User
    from argilla.datasets._resource import Dataset
    from argilla._models._files import ListObjectsResponse, ObjectMetadata, FileObjectResponse
    from argilla._models._documents import Document
    from extralit.extraction.models.schema import SchemaStructure


class Workspace(Resource):
    """Class for interacting with Argilla workspaces. Workspaces are used to organize datasets in the Argilla server.

    Attributes:
        name (str): The name of the workspace.
        id (UUID): The ID of the workspace. This is a unique identifier for the workspace in the server.
        datasets (List[Dataset]): A list of all datasets in the workspace.
        users (WorkspaceUsers): A list of all users in the workspace.
    """

    name: Optional[str]

    _api: "WorkspacesAPI"

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional["UUID"] = None,
        client: Optional["Argilla"] = None,
    ) -> None:
        """Initializes a Workspace object with a client and a name or id

        Parameters:
            client (Argilla): The client used to interact with Argilla
            name (str): The name of the workspace
            id (UUID): The id of the workspace

        Returns:
            Workspace: The initialized workspace object
        """
        client = client or Argilla._get_default()
        super().__init__(client=client, api=client.api.workspaces)

        self._model = WorkspaceModel(name=name, id=id)

    def add_user(self, user: Union["User", str]) -> "User":
        """Adds a user to the workspace. After adding a user to the workspace, it will have access to the datasets
        in the workspace.

        Args:
            user (Union[User, str]): The user to add to the workspace. Can be a User object or a username.

        Returns:
            User: The user that was added to the workspace
        """
        return self.users.add(user)

    def remove_user(self, user: Union["User", str]) -> "User":
        """Removes a user from the workspace. After removing a user from the workspace, it will no longer have access

        Args:
            user (Union[User, str]): The user to remove from the workspace. Can be a User object or a username.

        Returns:
            User: The user that was removed from the workspace.
        """
        return self.users.delete(user)

    # TODO: Make this method private
    def list_datasets(self) -> List["Dataset"]:
        from argilla.datasets import Dataset

        datasets = self._client.api.datasets.list(self.id)
        self._log_message(f"Got {len(datasets)} datasets for workspace {self.id}")
        return [Dataset.from_model(model=dataset, client=self._client) for dataset in datasets]

    ####################
    # File methods #
    ####################

    def list_files(self, path: str, recursive: bool = True, include_version: bool = True) -> "ListObjectsResponse":
        """List files in the workspace.

        Args:
            path: The path to list files from.
            recursive: Whether to list files recursively.
            include_version: Whether to include version information.

        Returns:
            A list of files.
        """
        return self._api.list_files(self.name, path, recursive, include_version)

    def get_file(self, path: str, version_id: Optional[str] = None) -> "FileObjectResponse":
        """Get a file from the workspace.

        Args:
            path: The path of the file.
            version_id: The version ID of the file.

        Returns:
            The file content and metadata.
        """
        return self._api.get_file(self.name, path, version_id)

    def put_file(self, path: str, file_path: Union[str, Path]) -> "ObjectMetadata":
        """Upload a file to the workspace.

        Args:
            path: The path to store the file.
            file_path: The local path of the file to upload.

        Returns:
            The metadata of the uploaded file.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        return self._api.put_file(self.name, path, file_path)

    def delete_file(self, path: str, version_id: Optional[str] = None) -> None:
        """Delete a file from the workspace.

        Args:
            path: The path of the file to delete.
            version_id: The version ID of the file.
        """
        self._api.delete_file(self.name, path, version_id)

    ####################
    # Document methods #
    ####################

    def add_document(
        self,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        pmid: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> "UUID":
        """Add a document to the workspace.

        Args:
            file_path: The local path of the file to upload.
            url: The URL of the document.
            pmid: The PMID of the document.
            doi: The DOI of the document.

        Returns:
            The ID of the added document.
        """
        from argilla._models._documents import Document

        document = Document(workspace_id=self.id, file_path=file_path, url=url, pmid=pmid, doi=doi)
        return self._api.add_document(document)

    def get_documents(self) -> List["Document"]:
        """Get documents from the workspace.

        Returns:
            A list of documents.
        """
        return self._api.get_documents(self.id)

    ####################
    # Schema methods #
    ####################

    def list_schemas(
        self, prefix: str = DEFAULT_SCHEMA_S3_PATH, exclude: Optional[List[str]] = None
    ) -> "SchemaStructure":
        """Get schemas from the workspace.

        Args:
            prefix: The prefix to filter schemas.
            exclude: List of schema names to exclude.

        Returns:
            A SchemaStructure containing the schemas.
        """
        return self._api.list_schemas(self.name, prefix, exclude)

    def add_schema(self, schema: Any, prefix: str = DEFAULT_SCHEMA_S3_PATH) -> None:
        """Add a schema to the workspace.

        Args:
            schema: The schema to add.
            prefix: The prefix to store the schema.
        """
        return self._api.add_schema(self.name, schema, prefix)

    def update_schemas(
        self, schemas: Any, check_existing: bool = True, prefix: str = DEFAULT_SCHEMA_S3_PATH
    ) -> "ListObjectsResponse":
        """Update schemas in the workspace.

        Args:
            schemas: The schemas to update.
            check_existing: Whether to check if the schema already exists.
            prefix: The prefix to store the schemas.

        Returns:
            A list of updated schema files.
        """
        return self._api.update_schemas(self.name, schemas, check_existing, prefix)

    @classmethod
    def from_model(cls, model: WorkspaceModel, client: Argilla) -> "Workspace":
        instance = cls(name=model.name, id=model.id, client=client)
        instance._model = model

        return instance

    ############################
    # Properties
    ############################

    @property
    def name(self) -> Optional[str]:
        return self._model.name

    @name.setter
    def name(self, value: str) -> None:
        self._model.name = value

    @property
    def datasets(self) -> List["Dataset"]:
        """List all datasets in the workspace

        Returns:
            List[Dataset]: A list of all datasets in the workspace
        """
        return self.list_datasets()

    @property
    def users(self) -> "WorkspaceUsers":
        """List all users in the workspace

        Returns:
            WorkspaceUsers: A list of all users in the workspace
        """
        return WorkspaceUsers(workspace=self)

    ############################
    # Private methods
    ############################


class WorkspaceUsers(Sequence["User"], LoggingMixin):
    class _Iterator(GenericIterator["User"]):
        pass

    def __init__(self, workspace: "Workspace") -> None:
        self._workspace = workspace

    @overload
    def add(self, user: "User") -> "User": ...

    @overload
    def add(self, user: str) -> "User": ...

    def add(self, user: Union["User", str]) -> "User":
        if isinstance(user, str):
            return self._add_user_by_username(username=user)
        return user.add_to_workspace(workspace=self._workspace)

    @overload
    def delete(self, user: "User") -> "User": ...

    @overload
    def delete(self, user: str) -> "User": ...

    def delete(self, user: Union["User", str]) -> "User":
        if isinstance(user, str):
            return self._delete_user_by_username(username=user)
        return user.remove_from_workspace(workspace=self._workspace)

    def __iter__(self):
        return self._Iterator(self._list_users())

    def __getitem__(self, index: int) -> "User":
        return self._list_users()[index]

    def __len__(self) -> int:
        return len(self._list_users())

    ####################
    # Private methods
    ####################

    def _list_users(self) -> List["User"]:
        users = self._workspace._client.users.list(workspace=self._workspace)
        self._log_message(f"Got {len(users)} users for workspace {self._workspace.id}")
        return users

    def _delete_user_by_username(self, username: str) -> "User":
        user = self._workspace._client.users(username=username)
        if user is None:
            raise ValueError(f"User {username} does not exist")
        return user.remove_from_workspace(workspace=self._workspace)

    def _add_user_by_username(self, username: str) -> "User":
        user = self._workspace._client.users(username=username)
        if user is None:
            raise ValueError(f"User {username} does not exist")
        return user.add_to_workspace(workspace=self._workspace)
