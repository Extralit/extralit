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

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestJobsAPI:
    """Test jobs API endpoints with RQ Groups integration."""

    async def test_get_jobs_requires_filter(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test that GET /jobs/ requires at least one filter parameter."""
        response = await async_client.get("/api/v1/jobs/", headers=owner_auth_header)

        assert response.status_code == 400
        assert "Must provide at least one filter" in response.json()["detail"]

    async def test_get_jobs_by_document_id_not_found(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test GET /jobs/ with non-existent document_id returns empty list."""
        non_existent_id = uuid4()
        response = await async_client.get(f"/api/v1/jobs/?document_id={non_existent_id}", headers=owner_auth_header)

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_jobs_by_reference_not_found(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test GET /jobs/ with non-existent reference returns empty list."""
        response = await async_client.get("/api/v1/jobs/?reference=non_existent_reference", headers=owner_auth_header)

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_jobs_by_group_id_not_found(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test GET /jobs/ with non-existent group_id returns 404."""
        response = await async_client.get("/api/v1/jobs/?group_id=non_existent_group", headers=owner_auth_header)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_jobs_api_schema_validation(self, async_client: AsyncClient, owner_auth_header: dict):
        """Test that the API validates query parameters correctly."""
        # Test with invalid UUID format for document_id
        response = await async_client.get("/api/v1/jobs/?document_id=invalid_uuid", headers=owner_auth_header)

        assert response.status_code == 422  # Validation error
