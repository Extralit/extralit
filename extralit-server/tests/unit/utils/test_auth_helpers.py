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

"""Tests for GitHub Copilot auth helpers: username validation, token persistence, Redis device flow."""

import time
from unittest import mock

import pytest

# ── Username validation ──────────────────────────────────────────────


class TestValidateUsername:
    def test_valid_usernames(self):
        from extralit_server.utils.auth_helpers import _validate_username

        for name in ["alice", "bob_123", "user.name", "user-name", "user@domain"]:
            assert _validate_username(name) == name

    def test_rejects_empty(self):
        from extralit_server.utils.auth_helpers import _validate_username

        with pytest.raises(ValueError):
            _validate_username("")

    def test_rejects_path_traversal(self):
        from extralit_server.utils.auth_helpers import _validate_username

        with pytest.raises(ValueError):
            _validate_username("../etc/passwd")

    def test_rejects_slash(self):
        from extralit_server.utils.auth_helpers import _validate_username

        with pytest.raises(ValueError):
            _validate_username("user/name")

    def test_rejects_overlength(self):
        from extralit_server.utils.auth_helpers import _validate_username

        with pytest.raises(ValueError):
            _validate_username("a" * 129)

    def test_rejects_double_dot(self):
        from extralit_server.utils.auth_helpers import _validate_username

        with pytest.raises(ValueError):
            _validate_username("user..name")


# ── Token persistence (filelock + atomic rename) ─────────────────────


class TestTokenPersistence:
    @pytest.fixture(autouse=True)
    def _patch_home_path(self, tmp_path):
        with mock.patch("extralit_server.utils.auth_helpers.settings") as mock_settings:
            mock_settings.home_path = str(tmp_path)
            yield

    def test_save_and_load_roundtrip(self):
        from extralit_server.utils.auth_helpers import load_token, save_token

        token = {"access_token": "ghu_abc123", "token_type": "bearer", "scope": "read:user copilot"}
        save_token("testuser", token)
        loaded = load_token("testuser")

        assert loaded is not None
        assert loaded["access_token"] == "ghu_abc123"
        assert loaded["token_type"] == "bearer"
        assert "saved_at" in loaded

    def test_load_returns_none_when_missing(self):
        from extralit_server.utils.auth_helpers import load_token

        assert load_token("nonexistent") is None

    def test_expired_token_returns_none(self):
        from extralit_server.utils.auth_helpers import TOKEN_MAX_AGE, load_token, save_token

        token = {"access_token": "ghu_expired", "token_type": "bearer"}
        save_token("testuser", token)

        # Patch time to simulate expiry
        with mock.patch("extralit_server.utils.auth_helpers.time") as mock_time:
            mock_time.time.return_value = time.time() + TOKEN_MAX_AGE + 1
            result = load_token("testuser")

        assert result is None

    def test_clear_token(self):
        from extralit_server.utils.auth_helpers import clear_token, load_token, save_token

        save_token("testuser", {"access_token": "ghu_todelete", "token_type": "bearer"})
        clear_token("testuser")
        assert load_token("testuser") is None

    def test_token_file_permissions(self, tmp_path):
        import os

        from extralit_server.utils.auth_helpers import _get_token_path, save_token

        save_token("testuser", {"access_token": "ghu_perms", "token_type": "bearer"})
        token_path = _get_token_path("testuser")
        mode = os.stat(token_path).st_mode & 0o777
        assert mode == 0o600

    def test_is_authenticated(self):
        from extralit_server.utils.auth_helpers import is_authenticated, save_token

        assert not is_authenticated("testuser")
        save_token("testuser", {"access_token": "ghu_auth", "token_type": "bearer"})
        assert is_authenticated("testuser")


# ── Redis-backed device flow state ───────────────────────────────────


class TestRedisDeviceFlow:
    @pytest.fixture(autouse=True)
    def _mock_redis(self):
        """Use a dict to simulate Redis get/setex/delete."""
        self.store = {}

        def mock_setex(key, ttl, value):
            self.store[key] = value

        def mock_get(key):
            return self.store.get(key)

        def mock_delete(key):
            self.store.pop(key, None)

        self.mock_conn = mock.MagicMock()
        self.mock_conn.setex = mock_setex
        self.mock_conn.get = mock_get
        self.mock_conn.delete = mock_delete

        with mock.patch("extralit_server.utils.auth_helpers._get_redis", return_value=self.mock_conn):
            yield

    def test_store_and_get_roundtrip(self):
        from extralit_server.utils.auth_helpers import get_pending_flow, store_pending_flow

        flow_data = {
            "device_code": "dc_abc",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }
        store_pending_flow("testuser", flow_data)
        result = get_pending_flow("testuser")

        assert result is not None
        assert result["device_code"] == "dc_abc"
        assert result["user_code"] == "ABCD-1234"
        assert "started_at" in result

    def test_get_returns_none_when_missing(self):
        from extralit_server.utils.auth_helpers import get_pending_flow

        assert get_pending_flow("nobody") is None

    def test_clear_pending_flow(self):
        from extralit_server.utils.auth_helpers import clear_pending_flow, get_pending_flow, store_pending_flow

        store_pending_flow("testuser", {"device_code": "dc_x", "expires_in": 900})
        clear_pending_flow("testuser")
        assert get_pending_flow("testuser") is None

    def test_store_uses_ttl_from_expires_in(self):
        from extralit_server.utils.auth_helpers import store_pending_flow

        # Replace setex with a spy to check TTL
        calls = []

        def spy_setex(key, ttl, value):
            calls.append((key, ttl))
            self.store[key] = value

        self.mock_conn.setex = spy_setex

        store_pending_flow("testuser", {"device_code": "dc_ttl", "expires_in": 600})
        assert len(calls) == 1
        assert calls[0][1] == 600  # TTL matches expires_in
