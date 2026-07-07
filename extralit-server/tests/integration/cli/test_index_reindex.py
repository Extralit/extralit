from unittest.mock import AsyncMock

import pytest

from extralit_server.cli.index.reindex import Reindexer
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_reindex_schema_rebuilds(db, monkeypatch):
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(schema=schema, version=1)
    await schema.update(db, current_version_id=version.id)

    rebuild = AsyncMock(return_value=0)
    monkeypatch.setattr("extralit_server.cli.index.reindex.rebuild_schema_index", rebuild)
    engine = AsyncMock()

    await Reindexer.reindex_schema(db, engine, schema.id)
    rebuild.assert_awaited_once()


async def test_reindex_all_iterates_schemas(db, monkeypatch):
    await SchemaFactory.create()
    await SchemaFactory.create()
    rebuild = AsyncMock(return_value=0)
    monkeypatch.setattr("extralit_server.cli.index.reindex.rebuild_schema_index", rebuild)
    engine = AsyncMock()

    count = await Reindexer.reindex_all(db, engine)
    assert count >= 2
    assert rebuild.await_count >= 2
