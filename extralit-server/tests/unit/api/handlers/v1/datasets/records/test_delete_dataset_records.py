from uuid import UUID

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import HIGH_QUEUE
from extralit_server.webhooks.v1.enums import RecordEvent
from extralit_server.webhooks.v1.records import build_record_event
from tests.factories import DatasetFactory, RecordFactory, WebhookFactory


@pytest.mark.asyncio
class TestDeleteDatasetRecords:
    def url(self, dataset_id: UUID) -> str:
        return f"/api/v1/datasets/{dataset_id}/records"

    async def test_delete_dataset_records_enqueue_webhook_record_deleted_events(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        dataset = await DatasetFactory.create()
        records = await RecordFactory.create_batch(2, dataset=dataset)
        webhook = await WebhookFactory.create(events=[RecordEvent.deleted])

        event_a = await build_record_event(db, RecordEvent.deleted, records[0])
        event_b = await build_record_event(db, RecordEvent.deleted, records[1])

        response = await async_client.delete(
            self.url(dataset.id),
            headers=owner_auth_header,
            params={"ids": f"{records[0].id},{records[1].id}"},
        )

        assert response.status_code == 204

        assert HIGH_QUEUE.count == 2

        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == RecordEvent.deleted
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event_a.data)

        assert HIGH_QUEUE.jobs[1].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[1].args[1] == RecordEvent.deleted
        assert HIGH_QUEUE.jobs[1].args[3] == jsonable_encoder(event_b.data)
