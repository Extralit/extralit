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

import builtins
import warnings
from abc import abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional, Union, overload
from uuid import UUID

from extralit._api._base import ResourceAPI
from extralit._api._client import DEFAULT_HTTP_CONFIG  # noqa: F401
from extralit._api._webhooks import WebhookModel
from extralit._exceptions import ExtralitError, NotFoundError
from extralit._helpers import GenericIterator
from extralit._helpers._resource_repr import ResourceHTMLReprMixin
from extralit._models import DatasetModel, DocumentModel, ResourceModel, UserModel, WorkspaceModel

if TYPE_CHECKING:
    from extralit import Dataset, Document, User, Webhook, Workspace
    from extralit.client.core import Extralit

__all__ = ["Datasets", "Documents", "Users", "Webhooks", "Workspaces"]


class Users(Sequence["User"], ResourceHTMLReprMixin):
    """A collection of users. It can be used to create a new user or to get an existing one."""

    class _Iterator(GenericIterator["User"]):
        pass

    def __init__(self, client: "Extralit") -> None:
        self._client = client
        self._api = client.api.users

    @overload
    def __call__(self, username: str) -> Optional["User"]:
        """Get a user by username if exists. Otherwise, returns `None`"""
        ...

    @overload
    def __call__(self, id: Union[UUID, str]) -> Optional["User"]:
        """Get a user by id if exists. Otherwise, returns `None`"""
        ...

    def __call__(self, username: Optional[str] = None, id: Optional[Union[str, UUID]] = None) -> Optional["User"]:
        if not (username or id):
            raise ExtralitError("One of 'username' or 'id' must be provided")
        if username and id:
            warnings.warn("Only one of 'username' or 'id' must be provided. Using 'id'", stacklevel=2)
            username = None

        if id is not None:
            model = _get_model_by_id(self._api, id)
            if model:
                return self._from_model(model)
            warnings.warn(f"User with id {id!r} not found.", stacklevel=2)
        else:
            for model in self._api.list():
                if model.username == username:
                    return self._from_model(model)
            warnings.warn(f"User with username {username!r} not found.", stacklevel=2)

    def __iter__(self):
        return self._Iterator(self.list())

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> "User": ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> Sequence["User"]: ...

    def __getitem__(self, index):
        model = self._api.list()[index]
        return self._from_model(model)

    def __len__(self) -> int:
        return len(self._api.list())

    def add(self, user: "User") -> "User":
        """Add a new user to Extralit.

        Args:
            user: User object.

        Returns:
            User: The created user.
        """
        user._client = self._client
        return user.create()

    @overload
    def list(self) -> list["User"]: ...

    @overload
    def list(self, workspace: "Workspace") -> builtins.list["User"]: ...

    def list(self, workspace: Optional["Workspace"] = None) -> builtins.list["User"]:
        """List all users."""
        if workspace is not None:
            models = self._api.list_by_workspace_id(workspace.id)
        else:
            models = self._api.list()

        return [self._from_model(model) for model in models]

    ############################
    # Private methods
    ############################

    def _repr_html_(self) -> str:
        return self._represent_as_html(resources=self.list())

    def _from_model(self, model: UserModel) -> "User":
        from extralit.users import User

        return User(client=self._client, _model=model)


class Workspaces(Sequence["Workspace"], ResourceHTMLReprMixin):
    """A collection of workspaces. It can be used to create a new workspace or to get an existing one."""

    class _Iterator(GenericIterator["Workspace"]):
        pass

    def __init__(self, client: "Extralit") -> None:
        self._client = client
        self._api = client.api.workspaces

    @overload
    def __call__(self, name: str) -> Optional["Workspace"]:
        """Get a workspace by name if exists. Otherwise, returns `None`"""
        ...

    @overload
    def __call__(self, id: Union[UUID, str]) -> Optional["Workspace"]:
        """Get a workspace by id if exists. Otherwise, returns `None`"""
        ...

    def __call__(self, name: Optional[str] = None, id: Optional[Union[UUID, str]] = None) -> Optional["Workspace"]:
        if not (name or id):
            raise ExtralitError("One of 'name' or 'id' must be provided")

        if name and id:
            warnings.warn("Only one of 'name' or 'id' must be provided. Using 'id'", stacklevel=2)
            name = None

        if id is not None:
            model = _get_model_by_id(self._api, id)
            if model:
                return self._from_model(model)
            warnings.warn(f"Workspace with id {id!r} not found", stacklevel=2)
        else:
            for model in self._api.list():
                if model.name == name:
                    return self._from_model(model)
            warnings.warn(f"Workspace with name {name!r} not found.", stacklevel=2)

    def __iter__(self):
        return self._Iterator(self.list())

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> "Workspace": ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> Sequence["Workspace"]: ...

    def __getitem__(self, index) -> "Workspace":
        model = self._api.list()[index]
        return self._from_model(model)

    def __len__(self) -> int:
        return len(self._api.list())

    def add(self, workspace: "Workspace") -> "Workspace":
        """Add a new workspace to the Extralit platform.
        Args:
            workspace: Workspace object.

        Returns:
            Workspace: The created workspace.
        """
        workspace._client = self._client
        return workspace.create()

    def list(self) -> list["Workspace"]:
        return [self._from_model(model) for model in self._api.list()]

    ############################
    # Properties
    ############################

    @property
    def default(self) -> "Workspace":
        """The default workspace."""
        if len(self) == 0:
            raise ExtralitError("There are no workspaces created. Please create a new workspace first")
        return self[0]

    ############################
    # Private methods
    ############################

    def _repr_html_(self) -> str:
        return self._represent_as_html(resources=self.list())

    def _from_model(self, model: WorkspaceModel) -> "Workspace":
        from extralit.workspaces import Workspace

        return Workspace.from_model(client=self._client, model=model)


class Datasets(Sequence["Dataset"], ResourceHTMLReprMixin):
    """A collection of datasets. It can be used to create a new dataset or to get an existing one."""

    class _Iterator(GenericIterator["Dataset"]):
        def __next__(self):
            dataset = super().__next__()
            return dataset.get()

    def __init__(self, client: "Extralit") -> None:
        self._client = client
        self._api = client.api.datasets

    @overload
    def __call__(self, name: str, workspace: Optional[Union["Workspace", str]] = None) -> Optional["Dataset"]:
        """Get a dataset by name and workspace if exists. Otherwise, returns `None`"""
        ...

    @overload
    def __call__(self, id: Union[UUID, str]) -> Optional["Dataset"]:
        """Get a dataset by id if exists. Otherwise, returns `None`"""
        ...

    @overload
    def __call__(self, workspace: Union["Workspace", str]) -> list["Dataset"]:
        """Get all datasets for a given workspace."""
        ...

    def __call__(
        self,
        name: Optional[str] = None,
        workspace: Optional[Union["Workspace", str]] = None,
        id: Optional[Union[UUID, str]] = None,
    ) -> Union[Optional["Dataset"], list["Dataset"]]:
        """
        Get a dataset by name and workspace, by id, or all datasets for a workspace.
        """
        if id is not None and name is None and workspace is None:
            model = _get_model_by_id(self._api, id)
            if model:
                return self._from_model(model)
            warnings.warn(f"Dataset with id {id!r} not found", stacklevel=2)
            return None

        elif name is not None and id is None:
            workspace_obj = workspace or self._client.workspaces.default
            if isinstance(workspace_obj, str):
                workspace_obj = self._client.workspaces(workspace_obj)

            if workspace_obj is None:
                raise ExtralitError("Workspace not found. Please provide a valid workspace name or id.")

            for dataset in workspace_obj.datasets:
                if dataset.name == name:
                    return dataset.get()
            warnings.warn(f"Dataset with name {name!r} not found in workspace {workspace_obj.name!r}", stacklevel=2)
            return None

        elif name is None and id is None and workspace is not None:
            workspace_obj = workspace
            if isinstance(workspace_obj, str):
                workspace_obj = self._client.workspaces(workspace_obj)
            return list(workspace_obj.datasets)

        elif name is not None and id is not None:
            warnings.warn("Only one of 'name' or 'id' must be provided. Using 'id'", stacklevel=2)
            model = _get_model_by_id(self._api, id)
            if model:
                return self._from_model(model)
            warnings.warn(f"Dataset with id {id!r} not found", stacklevel=2)
            return None

        else:
            raise ExtralitError("One of 'name', 'id', or 'workspace' must be provided")

    def __iter__(self):
        return self._Iterator([self._from_model(model) for model in self._api.list()])

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> "Dataset": ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> Sequence["Dataset"]: ...

    def __getitem__(self, index) -> "Dataset":
        model = self._api.list()[index]
        return self._from_model(model).get()

    def __len__(self) -> int:
        return len(self._api.list())

    def add(self, dataset: "Dataset") -> "Dataset":
        """
        Add a new dataset to the Extralit platform

        Args:
            dataset: Dataset object.

        Returns:
            Dataset: The created dataset.
        """
        dataset._client = self._client
        dataset.create()

        return dataset

    def list(self) -> list["Dataset"]:
        return list(self)

    ############################
    # Private methods
    ############################

    def _repr_html_(self) -> str:
        return self._represent_as_html(resources=self.list())

    def _from_model(self, model: DatasetModel) -> "Dataset":
        from extralit.datasets import Dataset

        return Dataset.from_model(model=model, client=self._client)


class Documents(Sequence["Document"], ResourceHTMLReprMixin):
    """A collection of documents within a workspace. It can be used to get existing documents."""

    class _Iterator(GenericIterator["Document"]):
        pass

    def __init__(self, client: "Extralit", workspace: "Workspace") -> None:
        self._client = client
        self._workspace = workspace
        self._api = client.api.documents

    @overload
    def __call__(self) -> list["Document"]:
        """List all documents in the workspace (lightweight, no metadata)."""
        ...

    @overload
    def __call__(
        self,
        *,
        id: Optional[Union[UUID, str]] = None,
        reference: Optional[str] = None,
        pmid: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> list["Document"]:
        """Get documents by id, reference, pmid, or doi. Returns a list of matching documents."""
        ...

    def __call__(
        self,
        *,
        id: Optional[Union[UUID, str]] = None,
        reference: Optional[str] = None,
        pmid: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> list["Document"]:
        """Get documents by id, reference, pmid, or doi, or list all documents if no parameters provided."""
        # If no parameters provided, return list of all documents (lightweight)
        if not any([id, reference, pmid, doi]):
            return self.list()

        # Build parameters for the API call to get specific documents
        params = {"workspace_id": str(self._workspace.id)}
        if id is not None:
            params["id"] = str(id)
        if reference is not None:
            params["reference"] = reference
        if pmid is not None:
            params["pmid"] = pmid
        if doi is not None:
            params["doi"] = doi

        try:
            models = self._api.get(params)
            return [self._from_model(model) for model in models]
        except Exception:
            # No documents found or error occurred
            return []

    def __iter__(self):
        return self._Iterator(self.list())

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> "Document": ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> Sequence["Document"]: ...

    def __getitem__(self, index) -> "Document":
        documents = self.list()
        return documents[index]

    def __len__(self) -> int:
        return len(self.list())

    def list(self) -> list["Document"]:
        """List all documents in the workspace."""
        models = self._api.list(self._workspace.id)
        return [self._from_model(model) for model in models]

    ############################
    # Private methods
    ############################

    def _repr_html_(self) -> str:
        return self._represent_as_html(resources=self.list())

    def _from_model(self, model: DocumentModel) -> "Document":
        from extralit.documents import Document

        return Document.from_model(model=model, client=self._client)


class Webhooks(Sequence["Webhook"], ResourceHTMLReprMixin):
    """A webhooks class. It can be used to create a new webhook or to get an existing one."""

    class _Iterator(GenericIterator["Webhook"]):
        pass

    def __init__(self, client: "Extralit") -> None:
        self._client = client
        self._api = client.api.webhooks

    def __call__(self, id: Union[UUID, str]) -> Optional["Webhook"]:
        """Get a webhook by id if exists. Otherwise, returns `None`"""

        model = _get_model_by_id(self._api, id)
        if model:
            return self._from_model(model)
        warnings.warn(f"Webhook with id {id!r} not found", stacklevel=2)

    def __iter__(self):
        return self._Iterator(self.list())

    @overload
    @abstractmethod
    def __getitem__(self, index: int) -> "Webhook": ...

    @overload
    @abstractmethod
    def __getitem__(self, index: slice) -> Sequence["Webhook"]: ...

    def __getitem__(self, index) -> "Webhook":
        model = self._api.list()[index]
        return self._from_model(model)

    def __len__(self) -> int:
        return len(self._api.list())

    def add(self, webhook: "Webhook") -> "Webhook":
        """Add a new webhook to the Extralit platform.
        Args:
            webhook: Webhook object.

        Returns:
            Webhook: The created webhook.
        """
        webhook._client = self._client
        return webhook.create()

    def list(self) -> list["Webhook"]:
        return [self._from_model(model) for model in self._api.list()]

    ############################
    # Private methods
    ############################

    def _repr_html_(self) -> str:
        return self._represent_as_html(resources=self.list())

    def _from_model(self, model: WebhookModel) -> "Webhook":
        from extralit.webhooks import Webhook

        return Webhook.from_model(client=self._client, model=model)


def _get_model_by_id(api: ResourceAPI, resource_id: Union[UUID, str]) -> Optional[ResourceModel]:
    """Get a resource model by id if found. Otherwise, `None`."""
    try:
        if not isinstance(resource_id, UUID):
            resource_id = UUID(resource_id)
        return api.get(resource_id)
    except NotFoundError:
        pass
