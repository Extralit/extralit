from uuid import UUID

import pytest
from httpx import AsyncClient

from extralit_server.contexts.datasets import CREATE_DATASET_VECTOR_SETTINGS_MAX_COUNT
from tests.factories import DatasetFactory, VectorSettingsFactory


@pytest.mark.asyncio
class TestCreateDatasetVectorSettings:
    def url(self, dataset_id: UUID) -> str:
        return f"/api/v1/datasets/{dataset_id}/vectors-settings"

    async def test_with_maximum_number_of_vector_settings_reached(
        self, async_client: AsyncClient, owner_auth_header: dict
    ):
        dataset = await DatasetFactory.create()

        await VectorSettingsFactory.create_batch(CREATE_DATASET_VECTOR_SETTINGS_MAX_COUNT, dataset=dataset)

        response = await async_client.post(
            self.url(dataset.id),
            headers=owner_auth_header,
            json={
                "name": "name",
                "title": "title",
                "dimensions": 3,
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": f"The maximum number of vector settings has been reached for dataset with id `{dataset.id}`"
        }
