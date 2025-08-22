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
class TestDeleteRecord:
    def url(self, record_id: UUID) -> str:
        return f"/api/v1/records/{record_id}"

    async def test_delete_record_enqueue_webhook_record_deleted_event(
        self, db: AsyncSession, async_client: AsyncClient, owner_auth_header: dict
    ):
        record = await RecordFactory.create()
        webhook = await WebhookFactory.create(events=[RecordEvent.deleted])

        event = await build_record_event(db, RecordEvent.deleted, record)

        response = await async_client.delete(
            self.url(record.id),
            headers=owner_auth_header,
        )

        assert response.status_code == 200

        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == RecordEvent.deleted
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event.data)
