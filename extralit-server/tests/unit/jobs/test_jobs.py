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

    @pytest.mark.skip()
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
