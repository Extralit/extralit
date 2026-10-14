from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from tenacity import retry, stop_after_delay, wait_exponential

from extralit_server.database import _get_async_db
from extralit_server.enums import DatasetDistributionStrategy, RecordStatus
from extralit_server.models import Record
from extralit_server.search_engine.base import SearchEngine
from extralit_server.webhooks.v1.enums import RecordEvent
from extralit_server.webhooks.v1.records import notify_record_event as notify_record_event_v1

MAX_TIME_RETRY_SQLALCHEMY_ERROR = 15


async def unsafe_update_records_status(db: AsyncSession, records: list[Record]):
    await db.execute(
        select(Record)
        .where(Record.id.in_([record.id for record in records]))
        .options(selectinload(Record.dataset), selectinload(Record.responses_submitted))
    )

    for record in records:
        await _update_record_status(db, record)


@retry(stop=stop_after_delay(MAX_TIME_RETRY_SQLALCHEMY_ERROR), wait=wait_exponential(multiplier=1, min=1, max=15))
async def update_record_status(search_engine: SearchEngine, record_id: UUID) -> Record:
    async for db in _get_async_db(isolation_level="SERIALIZABLE"):
        record = await Record.get_or_raise(
            db,
            record_id,
            options=[
                selectinload(Record.dataset),
                selectinload(Record.responses_submitted),
            ],
        )

        await _update_record_status(db, record)
        await db.commit()

        await search_engine.partial_record_update(record, status=record.status)

        await notify_record_event_v1(db, RecordEvent.updated, record)

        if record.is_completed():
            await notify_record_event_v1(db, RecordEvent.completed, record)

        return record


async def _update_record_status(db: AsyncSession, record: Record) -> Record:
    if record.dataset.distribution_strategy == DatasetDistributionStrategy.overlap:
        return await _update_record_status_with_overlap_strategy(db, record)

    raise NotImplementedError(f"unsupported distribution strategy `{record.dataset.distribution_strategy}`")


async def _update_record_status_with_overlap_strategy(db: AsyncSession, record: Record) -> Record:
    if len(record.responses_submitted) >= record.dataset.distribution["min_submitted"]:
        record.status = RecordStatus.completed
    else:
        record.status = RecordStatus.pending

    return await record.save(db, autocommit=False)
