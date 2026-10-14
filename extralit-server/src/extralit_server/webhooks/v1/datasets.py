from datetime import datetime

from rq.job import Job
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.models import Dataset
from extralit_server.webhooks.v1.enums import DatasetEvent
from extralit_server.webhooks.v1.event import Event
from extralit_server.webhooks.v1.schemas import DatasetEventSchema


async def notify_dataset_event(db: AsyncSession, dataset_event: DatasetEvent, dataset: Dataset) -> list[Job]:
    event = await build_dataset_event(db, dataset_event, dataset)

    return await event.notify(db)


async def build_dataset_event(db: AsyncSession, dataset_event: DatasetEvent, dataset: Dataset) -> Event:
    # NOTE: Force loading required association resources required by the event schema
    (
        await db.execute(
            select(Dataset)
            .where(Dataset.id == dataset.id)
            .options(
                selectinload(Dataset.workspace),
                selectinload(Dataset.questions),
                selectinload(Dataset.fields),
                selectinload(Dataset.metadata_properties),
                selectinload(Dataset.vectors_settings),
            )
        )
    ).scalar_one()

    return Event(
        event=dataset_event,
        timestamp=datetime.utcnow(),
        data=DatasetEventSchema.model_validate(dataset).model_dump(),
    )
