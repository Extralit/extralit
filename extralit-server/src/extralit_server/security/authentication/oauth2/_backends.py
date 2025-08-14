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
from typing import Any

from social_core.backends.oauth import BaseOAuth2
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.backends.utils import load_backends
from social_core.strategy import BaseStrategy

from extralit_server.errors.future import NotFoundError
from extralit_server.models import UserRole


class Strategy(BaseStrategy):
    def request_data(self, merge=True) -> dict[str, Any]:
        return {}

    def absolute_uri(self, path=None) -> str:
        return path

    def get_setting(self, name):
        return os.environ[name]


class HuggingfaceOpenId(OpenIdConnectAuth):
    """Huggingface OpenID Connect authentication backend."""

    name = "huggingface"

    AUTHORIZATION_URL = "https://huggingface.co/oauth/authorize"
    ACCESS_TOKEN_URL = "https://huggingface.co/oauth/token"

    # OIDC configuration
    OIDC_ENDPOINT = "https://huggingface.co"

    DEFAULT_SCOPE = ["openid", "profile"]


class KeycloakOpenId(OpenIdConnectAuth):
    """Huggingface OpenID Connect authentication backend."""

    name = "keycloak"

    def oidc_endpoint(self) -> str:
        value = super().oidc_endpoint()

        if value is None:
            from social_core.utils import setting_name

            name = setting_name("OIDC_ENDPOINT")
            raise ValueError(
                "oidc_endpoint needs to be set in the Keycloak configuration. "
                f"Please set the {name} environment variable."
            )

        return value

    def get_user_details(self, response: dict[str, Any]) -> dict[str, Any]:
        user = super().get_user_details(response)

        if role := self._extract_role(response):
            user["role"] = role

        if available_workspaces := self._extract_available_workspaces(response):
            user["available_workspaces"] = available_workspaces

        return user

    def _extract_role(self, response: dict[str, Any]) -> str | None:
        roles = self._read_realm_roles(response)
        role_to_value = {UserRole.owner: 3, UserRole.admin: 2, UserRole.annotator: 1}
        role_list = [role.split(":")[1] for role in roles if role.startswith("argilla_role:")]
        if role_list:
            max_role = max(role_list, key=lambda s: role_to_value.get(s, 0))
            return max_role

    def _extract_available_workspaces(self, response: dict[str, Any]) -> list[str]:
        roles = self._read_realm_roles(response)

        workspaces = []
        for role in roles:
            if role.startswith("extralit_workspace:"):
                workspace = role.split(":")[1]
                workspaces.append(workspace)

        return workspaces

    @classmethod
    def _read_realm_roles(cls, response) -> list[str]:
        realm_access = response.get("realm_access") or {}
        return realm_access.get("roles") or []


_SUPPORTED_BACKENDS = {}


def load_supported_backends(extra_backends: list | None = None) -> dict[str, type[BaseOAuth2]]:
    global _SUPPORTED_BACKENDS

    backends = [
        "extralit_server.security.authentication.oauth2._backends.HuggingfaceOpenId",
        "extralit_server.security.authentication.oauth2._backends.KeycloakOpenId",
        "social_core.backends.github.GithubOAuth2",
        "social_core.backends.google.GoogleOAuth2",
    ]

    if extra_backends:
        backends.extend(extra_backends)

    _SUPPORTED_BACKENDS = load_backends(backends, force_load=True)

    for backend in _SUPPORTED_BACKENDS.values():
        if not issubclass(backend, BaseOAuth2):
            raise ValueError(
                f"Backend {backend} is not a supported OAuth2 backend. "
                "Please, make sure it is a subclass of BaseOAuth2."
            )

    return _SUPPORTED_BACKENDS


def get_supported_backend_by_name(name: str) -> type[BaseOAuth2]:
    """Get a registered oauth provider by name. Raise a ValueError if provided not found."""
    global _SUPPORTED_BACKENDS

    if not _SUPPORTED_BACKENDS:
        _SUPPORTED_BACKENDS = load_supported_backends()

    if provider := _SUPPORTED_BACKENDS.get(name):
        return provider
    else:
        raise NotFoundError(f"Unsupported provider {name}. Supported providers are {_SUPPORTED_BACKENDS.keys()}")
