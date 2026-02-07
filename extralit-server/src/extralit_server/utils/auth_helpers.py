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

"""
GitHub Device Flow authentication utilities for GitHub Copilot integration.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from extralit_server.settings import settings

_LOGGER = logging.getLogger(__name__)


class GitHubDeviceFlowAuth:
    """
    Helper class for GitHub Device Flow authentication.

    This implements the OAuth Device Flow for authenticating with GitHub
    to obtain tokens for GitHub Copilot access.

    Uses the official VS Code OAuth app credentials to ensure compatibility
    with GitHub Copilot.
    """

    # Official VS Code OAuth App Client ID (public, safe to hardcode)
    # This is the ONLY client ID that GitHub Copilot accepts
    VSCODE_CLIENT_ID = "01ab8ac9400c4e429b23"

    DEVICE_CODE_URL = "https://github.com/login/device/code"
    ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

    # Scopes required for GitHub Copilot access
    SCOPE = "read:user copilot"

    def __init__(self, username: str):
        """
        Initialize the GitHub Device Flow helper.

        Args:
            username: The Extralit username (used for token storage path)
        """
        self.username = username

    def _get_config_dir(self) -> Path:
        """Get the user-specific config directory for token storage."""
        config_path = Path(settings.home_path) / "data" / "users" / self.username / "config"
        config_path.mkdir(parents=True, exist_ok=True)
        return config_path

    def _get_token_path(self) -> Path:
        """Get the full path to the token file."""
        return self._get_config_dir() / "github_token.json"

    async def initiate_flow(self) -> dict[str, Any]:
        """
        Initiate the GitHub Device Flow.

        Returns:
            dict containing:
                - device_code: Code for polling
                - user_code: Code for user to enter
                - verification_uri: URL for user to visit
                - expires_in: Seconds until codes expire
                - interval: Recommended polling interval in seconds

        Raises:
            httpx.HTTPError: If the request to GitHub fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.DEVICE_CODE_URL,
                data={
                    "client_id": self.VSCODE_CLIENT_ID,
                    "scope": self.SCOPE,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

        _LOGGER.info(f"Initiated GitHub Device Flow for user {self.username}")
        return {
            "device_code": data["device_code"],
            "user_code": data["user_code"],
            "verification_uri": data["verification_uri"],
            "expires_in": data["expires_in"],
            "interval": data["interval"],
        }

    async def poll_for_token(self, device_code: str, interval: int = 5, timeout: int = 900) -> dict[str, str]:
        """
        Poll GitHub for the access token after user authorization.

        Args:
            device_code: The device code from initiate_flow()
            interval: Seconds to wait between polling attempts
            timeout: Maximum seconds to wait for authorization

        Returns:
            dict containing:
                - access_token: The GitHub access token
                - token_type: Type of token (usually "bearer")
                - scope: Granted scopes

        Raises:
            TimeoutError: If user doesn't authorize within timeout
            ValueError: If authorization is denied or expires
            httpx.HTTPError: If the request to GitHub fails
        """
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while True:
                if time.time() - start_time > timeout:
                    raise TimeoutError("GitHub Device Flow timed out waiting for user authorization")

                response = await client.post(
                    self.ACCESS_TOKEN_URL,
                    data={
                        "client_id": self.VSCODE_CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    headers={"Accept": "application/json"},
                )

                data = response.json()

                if "access_token" in data:
                    _LOGGER.info(f"Successfully obtained GitHub token for user {self.username}")
                    return {
                        "access_token": data["access_token"],
                        "token_type": data.get("token_type", "bearer"),
                        "scope": data.get("scope", ""),
                    }
                elif data.get("error") == "authorization_pending":
                    # User hasn't authorized yet, keep polling
                    await asyncio.sleep(interval)
                elif data.get("error") == "slow_down":
                    # We're polling too fast, increase interval
                    interval += 5
                    await asyncio.sleep(interval)
                elif data.get("error") in ("expired_token", "access_denied"):
                    raise ValueError(f"GitHub authorization {data['error']}: {data.get('error_description', '')}")
                else:
                    raise ValueError(f"Unexpected error from GitHub: {data}")

    def save_token(self, token_data: dict[str, str]) -> None:
        """
        Save the GitHub token to disk.

        Args:
            token_data: Token data containing access_token, token_type, scope
        """
        token_path = self._get_token_path()
        with open(token_path, "w") as f:
            json.dump(token_data, f)

        # Set restrictive permissions (read/write for owner only)
        token_path.chmod(0o600)

        _LOGGER.info(f"Saved GitHub token for user {self.username} to {token_path}")

    def load_token(self) -> dict[str, str] | None:
        """
        Load the GitHub token from disk.

        Returns:
            Token data dict if exists, None otherwise
        """
        token_path = self._get_token_path()
        if not token_path.exists():
            return None

        try:
            with open(token_path) as f:
                token_data = json.load(f)
            _LOGGER.debug(f"Loaded GitHub token for user {self.username}")
            return token_data
        except (json.JSONDecodeError, OSError) as e:
            _LOGGER.error(f"Failed to load token for user {self.username}: {e}")
            return None

    def is_authenticated(self) -> bool:
        """
        Check if a valid GitHub token exists for this user.

        Returns:
            True if token file exists and is readable, False otherwise
        """
        token_data = self.load_token()
        return token_data is not None and "access_token" in token_data

    def clear_token(self) -> None:
        """
        Remove the stored GitHub token.
        """
        token_path = self._get_token_path()
        if token_path.exists():
            token_path.unlink()
            _LOGGER.info(f"Cleared GitHub token for user {self.username}")
