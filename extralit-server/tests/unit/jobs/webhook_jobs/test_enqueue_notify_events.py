import pytest
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.queues import HIGH_QUEUE
from extralit_server.jobs.webhook_jobs import enqueue_notify_events
from extralit_server.webhooks.v1.enums import ResponseEvent
from extralit_server.webhooks.v1.responses import build_response_event
from tests.factories import ResponseFactory, WebhookFactory


@pytest.mark.asyncio
class TestEnqueueNotifyEvents:
    async def test_enqueue_notify_events(self, db: AsyncSession):
        response = await ResponseFactory.create()

        webhooks = await WebhookFactory.create_batch(2, events=[ResponseEvent.created])
        await WebhookFactory.create_batch(2, events=[ResponseEvent.created], enabled=False)
        await WebhookFactory.create_batch(2, events=[ResponseEvent.deleted])

        event = await build_response_event(db, ResponseEvent.created, response)
        jsonable_data = jsonable_encoder(event.data)

        await enqueue_notify_events(
            db=db,
            event=ResponseEvent.created,
            timestamp=event.timestamp,
            data=jsonable_data,
        )

        assert HIGH_QUEUE.count == 2

        assert HIGH_QUEUE.jobs[0].args[0] == webhooks[0].id
        assert HIGH_QUEUE.jobs[0].args[1] == ResponseEvent.created
        assert HIGH_QUEUE.jobs[0].args[2] == event.timestamp
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_data

        assert HIGH_QUEUE.jobs[1].args[0] == webhooks[1].id
        assert HIGH_QUEUE.jobs[1].args[1] == ResponseEvent.created
        assert HIGH_QUEUE.jobs[1].args[2] == event.timestamp
        assert HIGH_QUEUE.jobs[1].args[3] == jsonable_data
