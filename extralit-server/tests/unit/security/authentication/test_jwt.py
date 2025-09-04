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

from datetime import datetime, timedelta

import pytest
from jose import jwt

from extralit_server.errors import UnauthorizedError
from extralit_server.security.authentication.jwt import JWT
from extralit_server.security.authentication.userinfo import UserInfo


class TestJWT:
    def test_create_access_token(self):
        user_info = UserInfo({"identity": "123", "username": "test_user", "name": "Test User", "role": "annotator"})

        token = JWT.create_access_token(user_info)

        # Decode without verification to check payload
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload["type"] == "access"
        assert payload["identity"] == "123"
        assert payload["username"] == "test_user"
        assert payload["name"] == "Test User"
        assert payload["role"] == "annotator"
        assert "exp" in payload

        # Check expiration is ~30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(seconds=JWT.access_token_expires)
        assert abs((exp_time - expected_exp).total_seconds()) < 10  # Allow 10s tolerance

    def test_create_refresh_token(self):
        user_info = UserInfo({"identity": "123", "username": "test_user", "name": "Test User", "role": "annotator"})

        token = JWT.create_refresh_token(user_info)

        # Decode without verification to check payload
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload["type"] == "refresh"
        assert payload["identity"] == "123"
        assert payload["username"] == "test_user"
        # Refresh tokens should have minimal payload
        assert "name" not in payload
        assert "role" not in payload
        assert "exp" in payload

        # Check expiration is ~30 days from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(seconds=JWT.refresh_token_expires)
        assert abs((exp_time - expected_exp).total_seconds()) < 10  # Allow 10s tolerance

    def test_create_token_pair(self):
        user_info = UserInfo({"identity": "123", "username": "test_user", "name": "Test User", "role": "annotator"})

        access_token, refresh_token = JWT.create_token_pair(user_info)

        # Verify both tokens are different
        assert access_token != refresh_token

        # Verify token types
        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        refresh_payload = jwt.decode(refresh_token, options={"verify_signature": False})

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_validate_refresh_token_success(self):
        user_info = UserInfo({"identity": "123", "username": "test_user"})

        refresh_token = JWT.create_refresh_token(user_info)
        payload = JWT.validate_refresh_token(refresh_token)

        assert payload["type"] == "refresh"
        assert payload["identity"] == "123"
        assert payload["username"] == "test_user"

    def test_validate_refresh_token_with_access_token_fails(self):
        user_info = UserInfo({"identity": "123", "username": "test_user", "name": "Test User", "role": "annotator"})

        access_token = JWT.create_access_token(user_info)

        with pytest.raises(UnauthorizedError, match="Invalid token type"):
            JWT.validate_refresh_token(access_token)

    def test_validate_refresh_token_with_invalid_token_fails(self):
        with pytest.raises(UnauthorizedError):
            JWT.validate_refresh_token("invalid.token.here")

    def test_legacy_create_method_backward_compatibility(self):
        """Ensure the legacy create method still works for existing code"""
        user_info = UserInfo({"identity": "123", "username": "test_user", "name": "Test User", "role": "annotator"})

        # Legacy method should create access token
        token = JWT.create(user_info)
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload["type"] == "access"
        assert payload["identity"] == "123"

    def test_token_expiration_differences(self):
        """Verify access and refresh tokens have different expiration times"""
        user_info = UserInfo({"identity": "123", "username": "test_user", "name": "Test User", "role": "annotator"})

        access_token, refresh_token = JWT.create_token_pair(user_info)

        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        refresh_payload = jwt.decode(refresh_token, options={"verify_signature": False})

        access_exp = datetime.fromtimestamp(access_payload["exp"])
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"])

        # Refresh token should expire much later than access token
        time_diff = refresh_exp - access_exp
        # Should be approximately 30 days - 30 minutes
        expected_diff = timedelta(days=30) - timedelta(minutes=30)
        assert abs((time_diff - expected_diff).total_seconds()) < 60  # Allow 1 minute tolerance
