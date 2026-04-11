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

Handles per-user OAuth device flow, token persistence with
cross-process file locking (filelock + atomic rename), and Redis-backed
ephemeral device code storage shared across workers.
"""

import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
from filelock import FileLock

from extralit_server.settings import settings

_LOGGER = logging.getLogger(__name__)

# ── GitHub OAuth constants ───────────────────────────────────────────
# Official VS Code OAuth App Client ID (public, required by Copilot)
GITHUB_CLIENT_ID = "01ab8ac9400c4e429b23"
GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_SCOPE = "read:user copilot"

# GitHub Copilot OAuth tokens don't carry an explicit TTL, but the
# access-token returned by the device-flow can be revoked at any time.
# We treat tokens older than 90 days as stale and force re-auth.
TOKEN_MAX_AGE = 90 * 24 * 3600

_FILELOCK_TIMEOUT = 10  # seconds

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


# ── Token persistence with filelock + atomic rename ──────────────────


def _get_token_dir(username: str) -> Path:
    """Return the per-user config directory, creating it if needed."""
    _validate_username(username)
    token_dir = Path(settings.home_path) / "data" / "users" / username / "config"
    token_dir.mkdir(parents=True, exist_ok=True)
    return token_dir


def _get_token_path(username: str) -> Path:
    return _get_token_dir(username) / "github_token.json"


def _get_lock_path(username: str) -> Path:
    return _get_token_dir(username) / "github_token.json.lock"


def save_token(username: str, token_data: dict[str, str]) -> None:
    """Persist token to disk atomically with cross-process locking.

    Uses filelock for mutual exclusion and tempfile + os.replace for
    POSIX-atomic writes so partial data is never visible.
    """
    _validate_username(username)
    payload = {**token_data, "saved_at": time.time()}
    token_path = _get_token_path(username)
    lock_path = _get_lock_path(username)
    token_dir = token_path.parent

    with FileLock(lock_path, timeout=_FILELOCK_TIMEOUT):
        fd, tmp_path = tempfile.mkstemp(dir=token_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(payload, f)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, token_path)
        except BaseException:
            # Clean up temp file on any failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    _LOGGER.info("Saved GitHub token for user %s", username)


def load_token(username: str) -> dict[str, str] | None:
    """Load a token from disk, returning ``None`` when missing or stale."""
    _validate_username(username)
    token_path = _get_token_path(username)
    lock_path = _get_lock_path(username)

    if not token_path.exists():
        return None

    with FileLock(lock_path, timeout=_FILELOCK_TIMEOUT):
        try:
            token_data: dict = json.loads(token_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            _LOGGER.error("Failed to load token for %s: %s", username, exc)
            return None

    # Expiry check
    saved_at = token_data.get("saved_at", 0)
    if time.time() - saved_at > TOKEN_MAX_AGE:
        _LOGGER.info("Token for %s has expired (age > 90 days), clearing", username)
        clear_token(username)
        return None

    if "access_token" not in token_data:
        return None
    return token_data


def is_authenticated(username: str) -> bool:
    return load_token(username) is not None


def clear_token(username: str) -> None:
    """Remove the persisted token file under lock."""
    _validate_username(username)
    token_path = _get_token_path(username)
    lock_path = _get_lock_path(username)

    with FileLock(lock_path, timeout=_FILELOCK_TIMEOUT):
        if token_path.exists():
            token_path.unlink()
            _LOGGER.info("Cleared GitHub token for user %s", username)


# ── Redis-backed device flow state ───────────────────────────────────

_REDIS_KEY_PREFIX = "extralit:device_flow:"


def _get_redis():
    """Lazy import to avoid circular imports and allow tests to mock."""
    from extralit_server.jobs.queues import REDIS_CONNECTION

    return REDIS_CONNECTION


def store_pending_flow(username: str, flow_data: dict[str, Any]) -> None:
    """Store the device flow data in Redis with TTL from expires_in."""
    _validate_username(username)
    payload = {**flow_data, "started_at": time.time()}
    ttl = int(flow_data.get("expires_in", 900))
    _get_redis().setex(
        f"{_REDIS_KEY_PREFIX}{username}",
        ttl,
        json.dumps(payload),
    )


def get_pending_flow(username: str) -> dict[str, Any] | None:
    """Retrieve a pending device flow from Redis (auto-expires via TTL)."""
    _validate_username(username)
    raw = _get_redis().get(f"{_REDIS_KEY_PREFIX}{username}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def clear_pending_flow(username: str) -> None:
    """Delete the pending device flow from Redis."""
    _validate_username(username)
    _get_redis().delete(f"{_REDIS_KEY_PREFIX}{username}")


# ── GitHub Device Flow HTTP helpers using authlib ────────────────────


async def initiate_device_flow() -> dict[str, Any]:
    """Start the GitHub device-code flow. Returns the full GitHub response."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_DEVICE_CODE_URL,
            data={"client_id": GITHUB_CLIENT_ID, "scope": GITHUB_SCOPE},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def poll_for_token(device_code: str) -> dict[str, str]:
    """Single-poll GitHub for the access token.

    The frontend drives the retry interval — this function makes exactly
    one request per call.

    Returns token data on success.

    Raises:
        TimeoutError: authorization_pending or slow_down (caller should retry).
        ValueError:   expired_token, access_denied, or unexpected error.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_ACCESS_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    if "access_token" in data:
        return {
            "access_token": data["access_token"],
            "token_type": data.get("token_type", "bearer"),
            "scope": data.get("scope", ""),
        }

    error = data.get("error", "")
    if error in ("authorization_pending", "slow_down"):
        raise TimeoutError(error)
    if error in ("expired_token", "access_denied"):
        raise ValueError(f"GitHub authorization {error}: {data.get('error_description', '')}")
    raise ValueError(f"Unexpected GitHub error: {error}")
