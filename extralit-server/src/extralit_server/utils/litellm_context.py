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
Context manager for LiteLLM environment isolation.

This ensures that each user's GitHub Copilot tokens are isolated
by temporarily setting XDG_CONFIG_HOME to user-specific directories.
"""

import os
from pathlib import Path
from typing import Any

from extralit_server.settings import settings


class LiteLLMContext:
    """
    Context manager for isolating LiteLLM environment per user.

    This temporarily sets XDG_CONFIG_HOME to point to a user-specific
    directory, ensuring that LiteLLM uses the correct GitHub token
    for each user without leakage.

    Example:
        with LiteLLMContext(username="alice"):
            # LiteLLM will use alice's GitHub token
            response = await litellm.acompletion(...)
    """

    def __init__(self, username: str):
        """
        Initialize the context manager.

        Args:
            username: The Extralit username for token isolation
        """
        self.username = username
        self.user_config_dir = str(Path(settings.home_path) / "data" / "users" / username / "config")
        self.original_xdg_config_home: str | None = None

    def __enter__(self) -> "LiteLLMContext":
        """
        Enter the context: set XDG_CONFIG_HOME to user-specific directory.
        """
        # Save original value
        self.original_xdg_config_home = os.environ.get("XDG_CONFIG_HOME")

        # Set to user-specific directory
        os.environ["XDG_CONFIG_HOME"] = self.user_config_dir

        # Ensure directory exists
        Path(self.user_config_dir).mkdir(parents=True, exist_ok=True)

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit the context: restore original XDG_CONFIG_HOME.
        """
        # Restore original value
        if self.original_xdg_config_home is not None:
            os.environ["XDG_CONFIG_HOME"] = self.original_xdg_config_home
        else:
            # Remove if it wasn't set before
            os.environ.pop("XDG_CONFIG_HOME", None)
