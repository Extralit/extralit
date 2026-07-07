from unittest.mock import AsyncMock

import pytest

from extralit_server.contexts.v2 import index_sync
from tests.factories import SchemaFactory, SchemaVersionFactory, V2RecordFactory

pytestmark = pytest.mark.asyncio


async def _published(db):
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(
        schema=schema,
        version=1,
        columns_cache=[{"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None}],
    )
    await schema.update(db, current_version_id=version.id)
    return schema, version


async def test_table_columns_unions_versions(db):
    schema, v1 = await _published(db)
    await SchemaVersionFactory.create(
        schema=schema,
        version=2,
        columns_cache=[
            {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
            {"name": "year", "dtype": "int64", "nullable": True, "review": None},
        ],
    )
    columns = await index_sync.table_columns(db, schema)
    assert {c["name"] for c in columns} == {"title", "year"}


async def test_sync_schema_table_calls_ensure(db):
    schema, _ = await _published(db)
    engine = AsyncMock()
    await index_sync.sync_schema_table(engine, db, schema)
    engine.ensure_table.assert_awaited_once()


async def test_sync_upserted_records_builds_rows(db):
    schema, version = await _published(db)
    record = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Hi"})
    engine = AsyncMock()
    await index_sync.sync_upserted_records(engine, db, schema, [record])
    engine.upsert.assert_awaited_once()
    args, kwargs = engine.upsert.call_args
    rows = args[1]
    assert rows[0]["title"] == "Hi"


async def test_sync_swallows_engine_errors(db):
    schema, version = await _published(db)
    record = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Hi"})
    engine = AsyncMock()
    engine.upsert.side_effect = RuntimeError("lance down")
    # Must NOT raise — best-effort.
    await index_sync.sync_upserted_records(engine, db, schema, [record])


async def test_rebuild_raises_on_failure(db):
    schema, _ = await _published(db)
    engine = AsyncMock()
    engine.drop_table.side_effect = RuntimeError("lance down")
    with pytest.raises(RuntimeError):
        await index_sync.rebuild_schema_index(engine, db, schema)
