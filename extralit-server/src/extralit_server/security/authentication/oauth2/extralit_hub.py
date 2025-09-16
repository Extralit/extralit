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

import json
import logging
import os
from typing import Any, Optional

import requests
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.exceptions import AuthException

from extralit_server.integrations.huggingface.spaces import HUGGINGFACE_SETTINGS
from extralit_server.settings import settings

logger = logging.getLogger(__name__)


class HubRegistrationError(AuthException):
    """Exception raised when Hub registration fails."""

    pass


class ExtralitHubOpenId(OpenIdConnectAuth):
    """Extralit Hub OpenID Connect authentication backend."""

    name = "extralithub"

    # Will be set during initialization
    AUTHORIZATION_URL = f"{settings.hub_url.rstrip('/')}/api/auth/oauth2/authorize"
    ACCESS_TOKEN_URL = f"{settings.hub_url.rstrip('/')}/api/auth/oauth2/token"
    OIDC_ENDPOINT = settings.hub_url

    DEFAULT_SCOPE = ["openid", "profile", "extralit:llm_access"]

    # Client credentials (set during registration)
    _client_credentials: Optional[dict[str, str]] = None

    def __init__(self, *args, **kwargs):
        """Initialize and ensure Hub registration."""
        super().__init__(*args, **kwargs)

        if self._load_stored_credentials():
            logger.info("Found existing Hub OIDC credentials")
            return
        else:
            logger.error(
                "Failed to load Hub registration, ensure OAUTH2_EXTRALITHUB_CLIENT_ID and OAUTH2_EXTRALITHUB_CLIENT_SECRET are set"
            )

    def _load_stored_credentials(self) -> bool:
        """Load stored client credentials if they exist."""
        # Check OAuth2 environment variables first
        client_id = os.getenv("OAUTH2_EXTRALITHUB_CLIENT_ID")
        client_secret = os.getenv("OAUTH2_EXTRALITHUB_CLIENT_SECRET")

        if client_id and client_secret:
            self._client_credentials = {"client_id": client_id, "client_secret": client_secret}
            return True

        credentials_file = os.path.join(settings.home_path, ".extralit_hub_credentials.json")
        try:
            if os.path.exists(credentials_file):
                with open(credentials_file) as f:
                    credentials = json.load(f)
                    if credentials.get("client_id") and credentials.get("client_secret"):
                        self._client_credentials = {
                            "client_id": credentials["client_id"],
                            "client_secret": credentials["client_secret"],
                        }
                        return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load credentials file: {e}")

        return False

    def _register_with_hub(self) -> None:
        """Register this instance with the Extralit Hub."""
        registration_data = self._prepare_registration_data()

        try:
            response = requests.post(
                f"{self.OIDC_ENDPOINT.rstrip('/')}/api/oauth2/register",
                json=registration_data,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in {201, 409}:
                credentials = response.json()
                if response.status_code == 409:
                    logger.info(f"Instance already registered: {response.json().get('client_id')}")
                self._store_credentials(credentials)
                logger.info(f"Successfully registered with Hub: {credentials['client_id']}")

            else:
                error_data = response.json() if response.content else {}
                raise HubRegistrationError(
                    f"Hub registration failed: {response.status_code} - {error_data.get('error', 'Unknown error')}"
                )

        except requests.RequestException as e:
            raise HubRegistrationError(f"Failed to connect to Hub for registration: {e}")

    def _prepare_registration_data(self) -> dict[str, Any]:
        """Prepare registration data based on instance environment."""
        if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
            # HuggingFace Spaces registration
            return self._prepare_hf_spaces_registration()
        else:
            # Self-hosted or local development registration
            return self._prepare_self_hosted_registration()

    def _prepare_hf_spaces_registration(self) -> dict[str, Any]:
        """Prepare registration data for HuggingFace Spaces."""
        space_id = HUGGINGFACE_SETTINGS.space_id
        space_author = HUGGINGFACE_SETTINGS.space_author_name
        space_repo = HUGGINGFACE_SETTINGS.space_repo_name

        if not space_id:
            raise HubRegistrationError("Cannot register HF Space: SPACE_ID not found")

        instance_name = f"{space_author}-{space_repo}" if space_author and space_repo else space_id
        redirect_uri = f"https://{space_id}.hf.space/oauth/extralithub/callback"

        return {
            "instance_name": instance_name,
            "redirect_uris": [redirect_uri],
            "instance_type": "hf_space",
            "metadata": {
                "space_id": space_id,
                "space_author": space_author,
                "space_repo_name": space_repo,
                "space_title": HUGGINGFACE_SETTINGS.space_title,
                "space_host": HUGGINGFACE_SETTINGS.space_host,
                "space_subdomain": HUGGINGFACE_SETTINGS.space_subdomain,
                "persistent_storage": HUGGINGFACE_SETTINGS.space_persistent_storage_enabled,
                "version": getattr(settings, "VERSION", "unknown"),
            },
        }

    def _prepare_self_hosted_registration(self) -> dict[str, Any]:
        """Prepare registration data for self-hosted instances."""
        # Get base URL for self-hosted instance
        base_url = settings.base_url.rstrip("/") or "http://localhost:6900"
        instance_name = "extralit-self-hosted"

        redirect_uri = f"{base_url.rstrip('/')}/oauth/extralithub/callback"

        # Determine instance type
        instance_type = "self_hosted" if "localhost" in base_url or "127.0.0.1" in base_url else "custom"

        return {
            "instance_name": instance_name,
            "redirect_uris": [redirect_uri],
            "instance_type": instance_type,
            "metadata": {
                "base_url": base_url,
                "instance_name": instance_name,
                "environment": getattr(settings, "ENVIRONMENT", "development"),
                "version": getattr(settings, "VERSION", "unknown"),
            },
        }

    def _store_credentials(self, credentials: dict[str, str]) -> None:
        """Store client credentials securely."""
        self._client_credentials = {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
        }

        # Log credentials for manual environment variable setup
        logger.info("Store these credentials as environment variables:")
        logger.info(f"OAUTH2_EXTRALITHUB_CLIENT_ID={credentials['client_id']}")
        logger.info("OAUTH2_EXTRALITHUB_CLIENT_SECRET=[REDACTED]")

        try:
            credentials_file = os.path.join(settings.home_path, ".extralit_hub_credentials.json")
            with open(credentials_file, "w") as f:
                json.dump(credentials, f)
            os.chmod(credentials_file, 0o600)  # Read-only for owner
        except Exception as e:
            logger.warning(f"Could not store credentials file: {e}")

    def get_key_and_secret(self):
        """Return client credentials for OAuth2 flow."""
        if not self._client_credentials:
            raise AuthException("Hub client credentials not available")

        return (self._client_credentials["client_id"], self._client_credentials["client_secret"])

    def get_user_details(self, response: dict[str, Any]) -> dict[str, Any]:
        """Extract user details from OIDC response with Hub-specific claims."""
        user = super().get_user_details(response)

        # Extract Hub-specific claims
        if github_copilot_enabled := response.get("github_copilot_enabled"):
            user["github_copilot_enabled"] = github_copilot_enabled

        if llm_access_tier := response.get("llm_access_tier"):
            user["llm_access_tier"] = llm_access_tier

        if instance_permissions := response.get("instance_permissions"):
            user["instance_permissions"] = instance_permissions

        if usage_quota := response.get("usage_quota"):
            user["usage_quota"] = usage_quota

        # Extract feature flags
        if feature_flags := response.get("feature_flags"):
            user["feature_flags"] = feature_flags

        # Log user sync for audit
        logger.info(
            f"Hub OIDC user sync: {user.get('username', 'unknown')} "
            f"with copilot={user.get('github_copilot_enabled', False)} "
            f"tier={user.get('llm_access_tier', 'basic')}"
        )

        return user

    def auth_complete(self, *args, **kwargs):
        """Complete authentication and ensure we have valid credentials."""
        if not self._client_credentials:
            raise AuthException("Hub client credentials not configured")

        return super().auth_complete(*args, **kwargs)

    def get_redirect_uri(self, state=None):
        """Get the redirect URI for this instance."""
        if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
            space_id = HUGGINGFACE_SETTINGS.space_id
            return f"https://{space_id}.hf.space/oauth/extralithub/callback"
        else:
            return f"{(settings.base_url or 'localhost:6900').rstrip('/')}/oauth/extralithub/callback"
