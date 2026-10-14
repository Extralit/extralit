from uuid import UUID

from rq import Retry
from rq.decorators import job
from sqlalchemy import select

from extralit_server.contexts import distribution
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import DEFAULT_QUEUE, JOB_TIMEOUT_DISABLED, REDIS_CONNECTION
from extralit_server.models import Record, Response
from extralit_server.search_engine.base import SearchEngine
from extralit_server.settings import settings

JOB_RECORDS_YIELD_PER = 100


@job(DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=JOB_TIMEOUT_DISABLED, retry=Retry(max=3))
async def update_dataset_records_status_job(dataset_id: UUID) -> None:
    """This Job updates the status of all the records in the dataset when the distribution strategy changes."""

    record_ids = []

    async with AsyncSessionLocal() as db:
        stream = await db.stream(
            select(Record.id)
            .join(Response)
            .where(Record.dataset_id == dataset_id)
            .order_by(Record.inserted_at.asc())
            .execution_options(yield_per=JOB_RECORDS_YIELD_PER)
        )

        async for record_id in stream.scalars():
            record_ids.append(record_id)

    # NOTE: We are updating the records status outside the database transaction to avoid database locks with SQLite.
    async with SearchEngine.get_by_name(settings.search_engine) as search_engine:
        for record_id in record_ids:
            await distribution.update_record_status(search_engine, record_id)
