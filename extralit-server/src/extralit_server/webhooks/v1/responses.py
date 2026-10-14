from datetime import datetime

from rq.job import Job
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.models import Dataset, Record, Response
from extralit_server.webhooks.v1.enums import ResponseEvent
from extralit_server.webhooks.v1.event import Event
from extralit_server.webhooks.v1.schemas import ResponseEventSchema


async def notify_response_event(db: AsyncSession, response_event: ResponseEvent, response: Response) -> list[Job]:
    event = await build_response_event(db, response_event, response)

    return await event.notify(db)


async def build_response_event(db: AsyncSession, response_event: ResponseEvent, response: Response) -> Event:
    # NOTE: Force loading required association resources required by the event schema
    (
        await db.execute(
            select(Response)
            .where(Response.id == response.id)
            .options(
                selectinload(Response.user),
                selectinload(Response.record).options(
                    selectinload(Record.dataset).options(
                        selectinload(Dataset.workspace),
                        selectinload(Dataset.questions),
                        selectinload(Dataset.fields),
                        selectinload(Dataset.metadata_properties),
                        selectinload(Dataset.vectors_settings),
                    ),
                ),
            ),
        )
    ).scalar_one()

    return Event(
        event=response_event,
        timestamp=datetime.utcnow(),
        data=ResponseEventSchema.model_validate(response).model_dump(),
    )
