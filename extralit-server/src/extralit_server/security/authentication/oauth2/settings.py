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

import yaml

from extralit_server.security.authentication.oauth2._backends import (
    get_supported_backend_by_name,
    load_supported_backends,
)
from extralit_server.security.authentication.oauth2.provider import OAuth2ClientProvider

__all__ = ["OAuth2Settings"]


class AllowedWorkspace:
    def __init__(self, name: str):
        self.name = name


class OAuth2Settings:
    """
    OAuth2 settings model.

    Args:
        allow_http_redirect:
            Whether to allow HTTP scheme on redirect urls (for tests purposes).
        providers:
            List of OAuth2 providers.
        allowed_workspaces:
            List of allowed workspace names (workspace must be created before).
    """

    ALLOWED_WORKSPACES_KEY = "allowed_workspaces"
    PROVIDERS_KEY = "providers"
    EXTRA_BACKENDS_KEY = "extra_backends"

    def __init__(
        self,
        allow_http_redirect: bool = False,
        extra_backends: list[str] | None = None,
        **settings,
    ):
        self.allow_http_redirect = allow_http_redirect
        self.extra_backends = extra_backends or []
        self.allowed_workspaces = self._build_workspaces(settings) or []
        self._providers = self._build_providers(settings, extra_backends) or []

        # Auto-configure Hub provider if running on HuggingFace Spaces
        self._auto_configure_hub_provider()

        if self.allow_http_redirect:
            # See https://stackoverflow.com/questions/27785375/testing-flask-oauthlib-locally-without-https
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    @property
    def providers(self) -> dict:
        return {provider.name: provider for provider in self._providers}

    @classmethod
    def from_yaml(cls, yaml_file: str) -> "OAuth2Settings":
        """Creates an instance of OAuth2Settings from a YAML file."""

        with open(yaml_file) as f:
            return cls(**yaml.safe_load(f))

    @classmethod
    def _build_workspaces(cls, settings: dict) -> list[AllowedWorkspace]:
        allowed_workspaces = settings.pop(cls.ALLOWED_WORKSPACES_KEY, None) or []
        return [AllowedWorkspace(**workspace) for workspace in allowed_workspaces]

    @classmethod
    def _build_providers(cls, settings: dict, extra_backends) -> list["OAuth2ClientProvider"]:
        providers = []

        load_supported_backends(extra_backends=extra_backends)

        for provider in settings.pop("providers", []):
            name = provider.pop("name")

            backend_class = get_supported_backend_by_name(name)
            providers.append(OAuth2ClientProvider.from_dict(provider, backend_class))

        return providers

    def _auto_configure_hub_provider(self) -> None:
        """Auto-configure Extralit Hub provider if appropriate."""
        try:
            # Check if Hub provider is already configured
            if "extralit_hub" in self.providers:
                return

            # Check if we have Hub credentials available
            hub_client_id = os.getenv("EXTRALIT_HUB_CLIENT_ID")
            hub_client_secret = os.getenv("EXTRALIT_HUB_CLIENT_SECRET")

            if not hub_client_id or not hub_client_secret:
                return

            # Load the Hub backend
            load_supported_backends(extra_backends=self.extra_backends)
            backend_class = get_supported_backend_by_name("extralit_hub")

            # Create Hub provider configuration
            hub_provider_config = {
                "client_id": hub_client_id,
                "client_secret": hub_client_secret,
                "sync_user": True,  # Sync user data from Hub
            }

            # Create and add the Hub provider
            hub_provider = OAuth2ClientProvider.from_dict(hub_provider_config, backend_class)
            hub_provider.name = "extralit_hub"  # Ensure name is set correctly
            self._providers.append(hub_provider)

        except Exception:
            # If auto-configuration fails, continue without Hub provider
            # This ensures the application still works even if Hub integration fails
            pass
