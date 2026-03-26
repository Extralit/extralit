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
GitHub Device Flow authentication helpers for GitHub Copilot integration.

Handles per-user OAuth device flow, token persistence, and server-side
device code storage so that the device_code secret never leaves the server.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx

from extralit_server.settings import settings

_LOGGER = logging.getLogger(__name__)

# ── Username validation ──────────────────────────────────────────────
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-@]+$")
_MAX_USERNAME_LEN = 128


def _validate_username(username: str) -> str:
    """Validate username to prevent path-traversal attacks.

    Raises:
        ValueError: If the username contains illegal characters.
    """
    if not username or len(username) > _MAX_USERNAME_LEN or not _USERNAME_RE.match(username) or ".." in username:
        raise ValueError(f"Invalid username: {username!r}")
    return username


# ── In-memory device-code store (keyed by username) ──────────────────
# Keeps the device_code secret server-side so it is never sent to the client.
_pending_device_flows: dict[str, dict[str, Any]] = {}


def store_pending_flow(username: str, flow_data: dict[str, Any]) -> None:
    """Store the device flow data server-side for later polling."""
    _pending_device_flows[username] = {
        **flow_data,
        "started_at": time.time(),
    }


def get_pending_flow(username: str) -> dict[str, Any] | None:
    """Retrieve (and validate expiry of) a pending device flow."""
    flow = _pending_device_flows.get(username)
    if flow is None:
        return None
    elapsed = time.time() - flow["started_at"]
    if elapsed > flow.get("expires_in", 900):
        # Expired - clean up
        _pending_device_flows.pop(username, None)
        return None
    return flow


def clear_pending_flow(username: str) -> None:
    _pending_device_flows.pop(username, None)


# ── Token persistence ────────────────────────────────────────────────

# Official VS Code OAuth App Client ID (public, required by Copilot)
VSCODE_CLIENT_ID = "01ab8ac9400c4e429b23"

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
SCOPE = "read:user copilot"

# GitHub Copilot OAuth tokens don't carry an explicit TTL, but the
# access-token returned by the device-flow can be revoked at any time.
# We treat tokens older than 90 days as stale and force re-auth.
_TOKEN_MAX_AGE_SECONDS = 90 * 24 * 3600


def _get_token_dir(username: str) -> Path:
    """Return the per-user config directory, creating it if needed."""
    _validate_username(username)
    token_dir = Path(settings.home_path) / "data" / "users" / username / "config"
    token_dir.mkdir(parents=True, exist_ok=True)
    return token_dir


def _get_token_path(username: str) -> Path:
    return _get_token_dir(username) / "github_token.json"


def save_token(username: str, token_data: dict[str, str]) -> None:
    """Persist token to disk with a ``saved_at`` timestamp."""
    _validate_username(username)
    payload = {**token_data, "saved_at": time.time()}
    token_path = _get_token_path(username)
    token_path.write_text(json.dumps(payload))
    token_path.chmod(0o600)
    _LOGGER.info("Saved GitHub token for user %s", username)


def load_token(username: str) -> dict[str, str] | None:
    """Load a token from disk, returning ``None`` when missing or stale."""
    _validate_username(username)
    token_path = _get_token_path(username)
    if not token_path.exists():
        return None
    try:
        token_data: dict = json.loads(token_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _LOGGER.error("Failed to load token for %s: %s", username, exc)
        return None

    # Expiry check
    saved_at = token_data.get("saved_at", 0)
    if time.time() - saved_at > _TOKEN_MAX_AGE_SECONDS:
        _LOGGER.info("Token for %s has expired (age > 90 days), clearing", username)
        clear_token(username)
        return None

    if "access_token" not in token_data:
        return None
    return token_data


def is_authenticated(username: str) -> bool:
    return load_token(username) is not None


def clear_token(username: str) -> None:
    _validate_username(username)
    token_path = _get_token_path(username)
    if token_path.exists():
        token_path.unlink()
        _LOGGER.info("Cleared GitHub token for user %s", username)


# ── GitHub Device Flow HTTP helpers ──────────────────────────────────


async def initiate_device_flow() -> dict[str, Any]:
    """Start the GitHub device-code flow. Returns the full GitHub response."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            DEVICE_CODE_URL,
            data={"client_id": VSCODE_CLIENT_ID, "scope": SCOPE},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def poll_for_token(device_code: str, interval: int = 5, timeout: int = 10) -> dict[str, str]:
    """Poll GitHub once (or a few times within *timeout* seconds).

    Returns token data on success.

    Raises:
        TimeoutError: user hasn't authorised yet (still pending).
        ValueError:   authorisation denied / expired / unexpected error.
    """
    start = time.time()
    async with httpx.AsyncClient() as client:
        while True:
            if time.time() - start > timeout:
                raise TimeoutError("Authorization still pending")

            resp = await client.post(
                ACCESS_TOKEN_URL,
                data={
                    "client_id": VSCODE_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            data = resp.json()

            if "access_token" in data:
                return {
                    "access_token": data["access_token"],
                    "token_type": data.get("token_type", "bearer"),
                    "scope": data.get("scope", ""),
                }

            error = data.get("error", "")
            if error == "authorization_pending":
                import asyncio

                await asyncio.sleep(interval)
                continue
            if error == "slow_down":
                import asyncio

                interval += 5
                await asyncio.sleep(interval)
                continue
            if error in ("expired_token", "access_denied"):
                raise ValueError(f"GitHub authorization {error}: {data.get('error_description', '')}")
            raise ValueError(f"Unexpected GitHub error: {error}")
