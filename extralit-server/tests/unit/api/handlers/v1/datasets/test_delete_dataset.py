from uuid import UUID

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import HIGH_QUEUE
from extralit_server.webhooks.v1.datasets import build_dataset_event
from extralit_server.webhooks.v1.enums import DatasetEvent
from tests.factories import DatasetFactory, WebhookFactory


@pytest.mark.asyncio
class TestDeleteDataset:
    def url(self, dataset_id: UUID) -> str:
        return f"/api/v1/datasets/{dataset_id}"

    async def test_delete_dataset_enqueue_webhook_dataset_deleted_event(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        dataset = await DatasetFactory.create()
        webhook = await WebhookFactory.create(events=[DatasetEvent.deleted])

        event = await build_dataset_event(db, DatasetEvent.deleted, dataset)

        response = await async_client.delete(
            self.url(dataset.id),
            headers=owner_auth_header,
        )

        assert response.status_code == 200

        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == DatasetEvent.deleted
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event.data)
