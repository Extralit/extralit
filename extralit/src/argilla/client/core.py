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
from functools import cached_property
from typing import TYPE_CHECKING, Optional

from argilla import _api
from argilla._api._client import DEFAULT_HTTP_CONFIG
from argilla._helpers._deploy import SpacesDeploymentMixin
from argilla._helpers._resource_repr import NotebookHTMLReprMixin

if TYPE_CHECKING:
    from argilla.client.resources import Datasets, Users, Webhooks, Workspaces
    from argilla.users import User

__all__ = ["Argilla"]


class Argilla(_api.APIClient, SpacesDeploymentMixin, NotebookHTMLReprMixin):
    """Argilla API client. This is the main entry point to interact with the API.

    Attributes:
        workspaces: A collection of workspaces.
        datasets: A collection of datasets.
        users: A collection of users.
        me: The current user.
    """

    # Default instance of Argilla
    _default_client: Optional["Argilla"] = None

    def __init__(
        self,
        api_url: Optional[str] = DEFAULT_HTTP_CONFIG.api_url,
        api_key: Optional[str] = DEFAULT_HTTP_CONFIG.api_key,
        timeout: int = DEFAULT_HTTP_CONFIG.timeout,
        retries: int = DEFAULT_HTTP_CONFIG.retries,
        **http_client_args,
    ) -> None:
        """Inits the `Argilla` client.

        Args:
            api_url: the URL of the Argilla API. If not provided, then the value will try
                to be set from `ARGILLA_API_URL` environment variable. Defaults to
                `"http://localhost:6900"`.
            api_key: the key to be used to authenticate in the Argilla API. If not provided,
                then the value will try to be set from `ARGILLA_API_KEY` environment variable.
                Defaults to `None`.
            timeout: the maximum time in seconds to wait for a request to the Argilla API
                to be completed before raising an exception. Defaults to `60`.
            retries: the number of times to retry the HTTP connection to the Argilla API
                before raising an exception. Defaults to `5`.
        """
        super().__init__(api_url=api_url, api_key=api_key, timeout=timeout, retries=retries, **http_client_args)

        self._set_default(self)

    @classmethod
    def from_credentials(
        cls,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        workspace: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        **kwargs,
    ) -> "Argilla":
        """Create client from stored credentials.

        If api_url and api_key are not provided, they will be loaded from environment variables
        or from the credentials file.

        Args:
            api_url: The URL of the Argilla server.
            api_key: The API key for authentication.
            workspace: Optional default workspace.
            extra_headers: Optional extra headers for API requests.
            **kwargs: Additional keyword arguments to pass to the client.

        Returns:
            Argilla: An initialized Argilla client.
        """
        from argilla.client.login import ArgillaCredentials

        api_url = api_url or os.environ.get("ARGILLA_API_URL")
        api_key = api_key or os.environ.get("ARGILLA_API_KEY")
        workspace = workspace or os.environ.get("EXTRALIT_WORKSPACE")

        if (not api_url or not api_key) and ArgillaCredentials.exists():
            credentials = ArgillaCredentials.load()
            api_url = api_url or credentials.api_url
            api_key = api_key or credentials.api_key
            workspace = workspace or credentials.workspace
            extra_headers = extra_headers or credentials.extra_headers

        client = cls(api_url=api_url, api_key=api_key, **kwargs)

        if extra_headers:
            for header_name, header_value in extra_headers.items():
                client.api.headers[header_name] = header_value

        return client

    @property
    def workspaces(self) -> "Workspaces":
        """A collection of workspaces on the server."""
        from argilla.client.resources import Workspaces

        return Workspaces(client=self)

    @property
    def datasets(self) -> "Datasets":
        """A collection of datasets on the server."""
        from argilla.client.resources import Datasets

        return Datasets(client=self)

    @property
    def users(self) -> "Users":
        """A collection of users on the server."""
        from argilla.client.resources import Users

        return Users(client=self)

    @property
    def webhooks(self) -> "Webhooks":
        """A collection of webhooks on the server."""
        from argilla.client.resources import Webhooks

        return Webhooks(client=self)

    @cached_property
    def me(self) -> "User":
        from argilla.users import User

        return User(client=self, _model=self.api.users.get_me())

    ############################
    # Private methods
    ############################

    @classmethod
    def _set_default(cls, client: "Argilla") -> None:
        """Set the default instance of Argilla."""
        cls._default_client = client

    @classmethod
    def _get_default(cls) -> "Argilla":
        """Get the default instance of Argilla. If it doesn't exist, create a new one."""
        if cls._default_client is None:
            cls._default_client = Argilla()
        return cls._default_client
