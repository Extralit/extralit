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

import pytest
from httpx import AsyncClient

from tests.factories import UserFactory


@pytest.mark.asyncio
class TestsCreateToken:
    def url(self) -> str:
        return "/api/v1/token"

    async def test_create_token(self, async_client: AsyncClient):
        user = await UserFactory.create()

        response = await async_client.post(
            self.url(),
            data={
                "username": user.username,
                "password": "1234",
            },
        )

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["access_token"]
        assert response_data["token_type"] == "bearer"
        assert response_data["refresh_token"]

    async def test_create_token_with_invalid_username(self, async_client: AsyncClient):
        await UserFactory.create()

        response = await async_client.post(
            self.url(),
            data={
                "username": "invalid-username",
                "password": "1234",
            },
        )

        assert response.status_code == 401

    async def test_create_token_with_invalid_password(self, async_client: AsyncClient):
        user = await UserFactory.create()

        response = await async_client.post(
            self.url(),
            data={
                "username": user.username,
                "password": "invalid-password",
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestsRefreshToken:
    def url(self) -> str:
        return "/api/v1/token/refresh"

    async def test_refresh_with_valid_token(self, async_client: AsyncClient):
        # Create user and get initial tokens
        user = await UserFactory.create()
        login_response = await async_client.post(
            "/api/v1/token",
            data={
                "username": user.username,
                "password": "1234",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = await async_client.post(self.url(), json={"refresh_token": refresh_token})

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["access_token"]
        assert response_data["token_type"] == "bearer"
        # Refresh endpoint should not return a new refresh token
        assert response_data.get("refresh_token") is None

    async def test_refresh_with_invalid_token(self, async_client: AsyncClient):
        response = await async_client.post(self.url(), json={"refresh_token": "invalid.token.here"})

        assert response.status_code == 401

    async def test_refresh_with_access_token_should_fail(self, async_client: AsyncClient):
        # Create user and get initial tokens
        user = await UserFactory.create()
        login_response = await async_client.post(
            "/api/v1/token",
            data={
                "username": user.username,
                "password": "1234",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token (should fail)
        response = await async_client.post(self.url(), json={"refresh_token": access_token})

        assert response.status_code == 401

    async def test_refresh_with_malformed_token(self, async_client: AsyncClient):
        response = await async_client.post(self.url(), json={"refresh_token": "not.a.valid.jwt"})

        assert response.status_code == 401

    async def test_refresh_without_token(self, async_client: AsyncClient):
        response = await async_client.post(self.url(), json={})

        assert response.status_code == 422
