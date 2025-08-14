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
