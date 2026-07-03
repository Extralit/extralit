import pytest
from sqlalchemy.exc import IntegrityError

from extralit_server.enums import V2RecordStatus
from extralit_server.models.v2 import Record
from tests.factories import SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_create_record_with_defaults(db):
    version = await SchemaVersionFactory.create()
    record = await Record.create(
        db,
        schema_id=version.schema_id,
        schema_version_id=version.id,
        reference="pmid:12345",
        fields={"name": "Anopheles", "age": 3},
    )
    assert record.id is not None
    assert record.status == V2RecordStatus.pending
    assert record.external_id is None
    assert record.metadata_ is None

    loaded = await Record.get(db, record.id)
    assert loaded.reference == "pmid:12345"
    assert loaded.fields == {"name": "Anopheles", "age": 3}


async def test_duplicate_external_id_in_schema_raises(db):
    version = await SchemaVersionFactory.create()
    db.add_all(
        [
            Record(
                schema_id=version.schema_id,
                schema_version_id=version.id,
                reference="r",
                external_id="x",
                fields={},
            ),
            Record(
                schema_id=version.schema_id,
                schema_version_id=version.id,
                reference="r",
                external_id="x",
                fields={},
            ),
        ]
    )
    with pytest.raises(IntegrityError, match=r"v2_record_schema_id_external_id_uq|UNIQUE"):
        await db.commit()


async def test_v2_record_factory_builds_valid_row(db):
    from tests.factories import V2RecordFactory

    record = await V2RecordFactory.create()
    assert record.id is not None
    assert record.schema_version_id is not None
    assert record.schema_id is not None
    assert record.status == V2RecordStatus.pending

    version = await record.awaitable_attrs.version
    assert record.schema_id == version.schema_id  # factory wires the record to the version's schema


async def test_null_external_ids_do_not_collide(db):
    version = await SchemaVersionFactory.create()
    db.add_all(
        [
            Record(schema_id=version.schema_id, schema_version_id=version.id, reference="r", fields={}),
            Record(schema_id=version.schema_id, schema_version_id=version.id, reference="r", fields={}),
        ]
    )
    await db.commit()  # nullable uniq: multiple NULLs allowed
