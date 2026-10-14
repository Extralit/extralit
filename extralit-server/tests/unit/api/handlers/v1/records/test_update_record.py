from uuid import UUID

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import HIGH_QUEUE
from extralit_server.webhooks.v1.enums import RecordEvent
from extralit_server.webhooks.v1.records import build_record_event
from tests.factories import RecordFactory, WebhookFactory


@pytest.mark.asyncio
class TestUpdateRecord:
    def url(self, record_id: UUID) -> str:
        return f"/api/v1/records/{record_id}"

    async def test_update_record_enqueue_webhook_record_updated_event(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        record = await RecordFactory.create()
        webhook = await WebhookFactory.create(events=[RecordEvent.updated])

        response = await async_client.patch(
            self.url(record.id),
            headers=owner_auth_header,
            json={"metadata": {"new": "value"}},
        )

        assert response.status_code == 200

        event = await build_record_event(db, RecordEvent.updated, record)

        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == RecordEvent.updated
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event.data)
