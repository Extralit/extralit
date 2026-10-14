from datetime import datetime

from rq.job import Job
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.jobs.webhook_jobs import enqueue_notify_events


class Event:
    def __init__(self, event: str, timestamp: datetime, data: dict):
        self.event = event
        self.timestamp = timestamp
        self.data = data

    async def notify(self, db: AsyncSession) -> list[Job]:
        return await enqueue_notify_events(
            db,
            event=self.event,
            timestamp=self.timestamp,
            data=self.data,
        )
