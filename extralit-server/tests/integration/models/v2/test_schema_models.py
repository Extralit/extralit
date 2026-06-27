import pytest
from sqlalchemy.exc import IntegrityError

from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import SchemaFactory, WorkspaceFactory

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


async def test_schema_and_version_apply_column_defaults(db):
    workspace = await WorkspaceFactory.create()
    # Schema created with only the required fields applies kind/status/settings defaults.
    schema = await Schema.create(db, name="defaults", workspace_id=workspace.id)
    assert schema.kind == SchemaKind.table
    assert schema.status == SchemaStatus.draft
    assert schema.settings == {}
    assert schema.current_version_id is None

    # SchemaVersion created without columns_cache/review_widgets applies []/{} defaults.
    version = await SchemaVersion.create(db, schema_id=schema.id, version=1, object_key="k", etag="e", checksum="c")
    assert version.columns_cache == []
    assert version.review_widgets == {}
    assert version.parent_version_id is None


async def test_duplicate_schema_name_in_workspace_raises(db):
    workspace = await WorkspaceFactory.create()
    db.add_all(
        [
            Schema(name="dup", workspace_id=workspace.id),
            Schema(name="dup", workspace_id=workspace.id),
        ]
    )
    with pytest.raises(IntegrityError, match="schema_workspace_id_name_uq|UNIQUE"):
        await db.commit()


async def test_duplicate_schema_version_raises(db):
    schema = await SchemaFactory.create()
    db.add_all(
        [
            SchemaVersion(schema_id=schema.id, version=1, object_key="a", etag="e", checksum="c"),
            SchemaVersion(schema_id=schema.id, version=1, object_key="b", etag="e", checksum="c"),
        ]
    )
    with pytest.raises(IntegrityError, match="schema_version_schema_id_version_uq|UNIQUE"):
        await db.commit()
