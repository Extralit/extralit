"""Best-effort synchronization between Postgres (truth) and the LanceDB index.

Sync hooks mirror v1's shape (ensure on publish, upsert after record commit, delete on
delete) but never fail the caller: any engine error is logged and swallowed, and the
`:rebuild-index` endpoint / reindex CLI is the recovery path (spec §15). Only
`rebuild_schema_index` raises, since the caller explicitly asked to rebuild.
"""

import logging
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.index.base import IndexEngine
from extralit_server.index.mapping import record_to_row, union_columns
from extralit_server.models.v2 import Schema, SchemaVersion, V2Record

_LOGGER = logging.getLogger("extralit_server.index")


async def table_columns(db: AsyncSession, schema: Schema) -> list[dict[str, Any]]:
    """The Lance table's column superset: union of every version's columns_cache.

    Ordered by version ascending so that the earliest-version dtype wins when
    the same column name appears in multiple versions with different types — making
    the result stable and consistent across successive calls.
    """
    caches = (
        (
            await db.execute(
                select(SchemaVersion.columns_cache)
                .where(SchemaVersion.schema_id == schema.id)
                .order_by(SchemaVersion.version.asc())
            )
        )
        .scalars()
        .all()
    )
    return union_columns([c or [] for c in caches])


async def sync_schema_table(engine: IndexEngine, db: AsyncSession, schema: Schema) -> None:
    try:
        columns = await table_columns(db, schema)
        await engine.ensure_table(schema.id, columns)
    except Exception as exc:  # best-effort; truth is in Postgres
        _LOGGER.warning("Index ensure_table failed for schema %s: %s", schema.id, exc)


async def sync_upserted_records(engine: IndexEngine, db: AsyncSession, schema: Schema, records: list[V2Record]) -> None:
    if not records:
        return
    try:
        columns = await table_columns(db, schema)
        await engine.ensure_table(schema.id, columns)
        rows = [record_to_row(record, columns) for record in records]
        await engine.upsert(schema.id, rows, columns)
    except Exception as exc:
        record_ids = [str(r.id) for r in records]
        _LOGGER.warning("Index upsert failed for schema %s records %s: %s", schema.id, record_ids, exc)


async def sync_deleted_records(engine: IndexEngine, schema: Schema, record_ids: Iterable[UUID]) -> None:
    ids = list(record_ids)
    if not ids:
        return
    try:
        await engine.delete(schema.id, ids)
    except Exception as exc:
        _LOGGER.warning("Index delete failed for schema %s records %s: %s", schema.id, ids, exc)


async def rebuild_schema_index(engine: IndexEngine, db: AsyncSession, schema: Schema, *, batch_size: int = 500) -> int:
    """Drop and repopulate the schema's Lance table from Postgres. Raises on failure.

    Upserts are batched with FTS optimization deferred to a single call at the end, so
    the index is not rebuilt O(batches) times during a large reindex.
    """
    columns = await table_columns(db, schema)
    await engine.drop_table(schema.id)
    await engine.ensure_table(schema.id, columns)

    total = 0
    offset = 0
    while True:
        records = (
            (
                await db.execute(
                    select(V2Record)
                    .where(V2Record.schema_id == schema.id)
                    .order_by(V2Record.inserted_at.asc(), V2Record.id.asc())
                    .offset(offset)
                    .limit(batch_size)
                )
            )
            .scalars()
            .all()
        )
        if not records:
            break
        rows = [record_to_row(record, columns) for record in records]
        await engine.upsert(schema.id, rows, columns, optimize=False)
        total += len(records)
        offset += batch_size

    # Single optimize pass after all batches — avoids O(batches) FTS rebuilds.
    if total:
        await engine.optimize_table(schema.id)
    return total
