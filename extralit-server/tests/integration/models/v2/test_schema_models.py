import pytest

from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import WorkspaceFactory

pytestmark = pytest.mark.asyncio


async def test_create_schema_and_version(db):
    workspace = await WorkspaceFactory.create()
    schema = await Schema.create(
        db,
        name="population",
        kind=SchemaKind.table,
        status=SchemaStatus.draft,
        workspace_id=workspace.id,
    )
    version = await SchemaVersion.create(
        db,
        schema_id=schema.id,
        version=1,
        object_key=f"schemas/{schema.id}/v1.json",
        etag="abc123",
        checksum="def456",
        columns_cache=[{"name": "n", "dtype": "str", "nullable": False, "review": None}],
    )
    assert schema.id is not None
    assert version.schema_id == schema.id
    assert version.version == 1

    loaded = await Schema.get(db, schema.id)
    assert loaded.name == "population"
    assert loaded.kind == SchemaKind.table
