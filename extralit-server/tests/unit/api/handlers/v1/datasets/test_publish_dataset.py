from uuid import UUID

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import HIGH_QUEUE
from extralit_server.webhooks.v1.datasets import build_dataset_event
from extralit_server.webhooks.v1.enums import DatasetEvent
from tests.factories import DatasetFactory, RatingQuestionFactory, TextFieldFactory, WebhookFactory


@pytest.mark.asyncio
class TestPublishDataset:
    def url(self, dataset_id: UUID) -> str:
        return f"/api/v1/datasets/{dataset_id}/publish"

    async def test_publish_dataset_enqueue_webhook_dataset_published_event(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        dataset = await DatasetFactory.create()
        await TextFieldFactory.create(dataset=dataset, required=True)
        await RatingQuestionFactory.create(dataset=dataset, required=True)

        webhook = await WebhookFactory.create(events=[DatasetEvent.published])

        response = await async_client.put(
            self.url(dataset.id),
            headers=owner_auth_header,
        )

        assert response.status_code == 200

        event = await build_dataset_event(db, DatasetEvent.published, dataset)

        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == DatasetEvent.published
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event.data)
