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
import json
from pathlib import Path
from typing import Dict, Optional

# Define the cache directory for storing credentials
cache_dir_env = os.environ.get("EXTRALIT_CACHE_DIR")
if cache_dir_env:
    EXTRALIT_CACHE_DIR = Path(cache_dir_env)
else:
    EXTRALIT_CACHE_DIR = Path.home() / ".extralit"

EXTRALIT_CREDENTIALS_FILE = EXTRALIT_CACHE_DIR / "credentials.json"


class ArgillaCredentials:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        workspace: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize credentials.

        Args:
            api_url: The URL of the Extralit server.
            api_key: The API key for authentication.
            workspace: Optional default workspace.
            extra_headers: Optional extra headers for API requests.
        """
        self.api_url = api_url
        self.api_key = api_key
        self.workspace = workspace
        self.extra_headers = extra_headers or {}

    def save(self) -> None:
        """Save credentials to file."""
        if not EXTRALIT_CACHE_DIR.exists():
            EXTRALIT_CACHE_DIR.mkdir(parents=True)

        with open(EXTRALIT_CREDENTIALS_FILE, "w") as f:
            json.dump(
                {
                    "api_url": self.api_url,
                    "api_key": self.api_key,
                    "workspace": self.workspace,
                    "extra_headers": self.extra_headers,
                },
                f,
            )

    @classmethod
    def load(cls) -> "ArgillaCredentials":
        """Load credentials from file.

        Returns:
            ArgillaCredentials: The loaded credentials.

        Raises:
            FileNotFoundError: If credentials file doesn't exist.
        """
        if not cls.exists():
            raise FileNotFoundError(f"'{EXTRALIT_CREDENTIALS_FILE}' does not exist.")

        with open(EXTRALIT_CREDENTIALS_FILE, "r") as f:
            data = json.load(f)
            return cls(
                api_url=data["api_url"],
                api_key=data["api_key"],
                workspace=data.get("workspace"),
                extra_headers=data.get("extra_headers"),
            )

    @classmethod
    def remove(cls) -> None:
        """Remove credentials file.

        Raises:
            FileNotFoundError: If credentials file doesn't exist.
        """
        if not cls.exists():
            raise FileNotFoundError(f"'{EXTRALIT_CREDENTIALS_FILE}' does not exist.")

        EXTRALIT_CREDENTIALS_FILE.unlink()

    @classmethod
    def exists(cls) -> bool:
        """Check if credentials file exists.

        Returns:
            bool: True if credentials file exists, False otherwise.
        """
        return EXTRALIT_CREDENTIALS_FILE.exists()


def login(
    api_url: str, api_key: str, workspace: Optional[str] = None, extra_headers: Optional[Dict[str, str]] = None
) -> None:
    """Login to an Extralit server using the provided URL and API key.

    If the login is successful, the credentials will be stored in the Extralit cache directory.

    Args:
        api_url: The URL of the Extralit server.
        api_key: The API key to use when communicating with the Extralit server.
        workspace: The default workspace where the datasets will be created.
        extra_headers: A dictionary containing extra headers that will be sent to the Extralit server.

    Raises:
        ValueError: If the login fails.
    """
    # Validate credentials by creating a client and making a test API call
    from argilla.client import Argilla

    try:
        # Create client with the provided credentials
        client = Argilla(api_url=api_url, api_key=api_key)

        # Try to get user info - this will raise an exception if authentication fails
        client.me

        # If we get here, the credentials are valid
        # Save credentials
        ArgillaCredentials(api_url=api_url, api_key=api_key, workspace=workspace, extra_headers=extra_headers).save()
    except Exception as e:
        # Authentication failed
        raise ValueError(f"Failed to authenticate with the provided credentials: {str(e)}")
