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


from datetime import datetime
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from rq.decorators import job
from rq.job import Job, Retry
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.contexts import webhooks
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import HIGH_QUEUE, REDIS_CONNECTION
from extralit_server.models import Webhook
from extralit_server.webhooks.v1.commons import notify_event


async def enqueue_notify_events(db: AsyncSession, event: str, timestamp: datetime, data: dict) -> list[Job]:
    enabled_webhooks = await webhooks.list_enabled_webhooks(db)
    if len(enabled_webhooks) == 0:
        return []

    enqueued_jobs = []
    jsonable_data = jsonable_encoder(data)
    for enabled_webhook in enabled_webhooks:
        if event in enabled_webhook.events:
            enqueue_job = notify_event_job.delay(enabled_webhook.id, event, timestamp, jsonable_data)
            enqueued_jobs.append(enqueue_job)

    return enqueued_jobs


@job(HIGH_QUEUE, connection=REDIS_CONNECTION, retry=Retry(max=3, interval=[10, 60, 180]))
async def notify_event_job(webhook_id: UUID, event: str, timestamp: datetime, data: dict) -> None:
    async with AsyncSessionLocal() as db:
        webhook = await Webhook.get_or_raise(db, webhook_id)

    response = notify_event(webhook, event, timestamp, data)
    response.raise_for_status()
