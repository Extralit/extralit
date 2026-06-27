import pytest

from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_schema_factory_creates_row(db):
    schema = await SchemaFactory.create(name="outcomes")
    assert isinstance(schema, Schema)
    assert schema.workspace_id is not None


async def test_schema_version_factory_links_schema(db):
    version = await SchemaVersionFactory.create()
    assert isinstance(version, SchemaVersion)
    assert version.schema_id is not None
    assert version.version >= 1
