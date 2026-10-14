from datetime import datetime

from rq.job import Job
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.models import Dataset, Record
from extralit_server.webhooks.v1.enums import RecordEvent
from extralit_server.webhooks.v1.event import Event
from extralit_server.webhooks.v1.schemas import RecordEventSchema


async def notify_record_event(db: AsyncSession, record_event: RecordEvent, record: Record) -> list[Job]:
    event = await build_record_event(db, record_event, record)

    return await event.notify(db)


async def build_record_event(db: AsyncSession, record_event: RecordEvent, record: Record) -> Event:
    # NOTE: Force loading required association resources required by the event schema
    (
        await db.execute(
            select(Dataset)
            .where(Dataset.id == record.dataset_id)
            .options(
                selectinload(Dataset.workspace),
                selectinload(Dataset.fields),
                selectinload(Dataset.questions),
                selectinload(Dataset.metadata_properties),
                selectinload(Dataset.vectors_settings),
            )
        )
    ).scalar_one()

    return Event(
        event=record_event,
        timestamp=datetime.utcnow(),
        data=RecordEventSchema.model_validate(record).model_dump(),
    )
