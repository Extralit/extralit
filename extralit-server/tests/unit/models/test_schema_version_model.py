import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.enums import FieldType
from extralit_server.models.database import Field, SchemaVersion
from tests.factories import DatasetFactory, RecordFactory, SchemaVersionFactory


@pytest.mark.asyncio
class TestSchemaVersionModel:
    async def test_field_type_column_exists(self):
        assert FieldType.column == "column"

    async def test_schema_version_belongs_to_dataset(self, db: AsyncSession):
        dataset = await DatasetFactory.create()
        version = await SchemaVersion.create(
            db,
            dataset_id=dataset.id,
            version=1,
            object_key=f"schemas/{dataset.id}/v1.json",
            etag="etag-1",
            checksum="checksum-1",
        )
        assert version.dataset_id == dataset.id
        assert version.version == 1
        assert version.parent_version_id is None

    async def test_dataset_points_at_current_schema_version(self, db: AsyncSession):
        dataset = await DatasetFactory.create()
        version = await SchemaVersion.create(
            db, dataset_id=dataset.id, version=1, object_key="k", etag="e", checksum="c"
        )
        await dataset.update(db, current_schema_version_id=version.id)
        await db.refresh(dataset, attribute_names=["schema_versions"])
        assert dataset.current_schema_version_id == version.id
        assert [v.id for v in dataset.schema_versions] == [version.id]

    async def test_schema_version_number_is_unique_per_dataset(self, db: AsyncSession):
        dataset = await DatasetFactory.create()
        await SchemaVersion.create(db, dataset_id=dataset.id, version=1, object_key="k", etag="e", checksum="c")
        with pytest.raises(IntegrityError, match=r"schema_version_dataset_id_version_uq|UNIQUE"):
            await SchemaVersion.create(db, dataset_id=dataset.id, version=1, object_key="k2", etag="e", checksum="c")

    async def test_schema_version_factory_builds_a_row(self, db: AsyncSession):
        # Pins the async-SubFactory constraint: a LazyAttribute that dereferences
        # `dataset` sees an un-awaited coroutine, so object_key must not touch it.
        version = await SchemaVersionFactory.create()
        assert version.dataset_id is not None
        assert version.object_key == "schemas/v1.json"

    async def test_record_carries_a_reference(self, db: AsyncSession):
        record = await RecordFactory.create(reference="10.1000/j.foo.2020.01")
        assert record.reference == "10.1000/j.foo.2020.01"

    async def test_record_reference_defaults_to_none(self, db: AsyncSession):
        record = await RecordFactory.create()
        assert record.reference is None

    async def test_field_is_upsertable(self):
        assert Field.__upsertable_columns__ == {"title", "required", "settings"}

    async def test_deleting_dataset_deletes_its_schema_versions(self, db: AsyncSession):
        dataset = await DatasetFactory.create()
        await SchemaVersion.create(db, dataset_id=dataset.id, version=1, object_key="k", etag="e", checksum="c")
        await dataset.delete(db)
        assert (await SchemaVersion.get_by(db, dataset_id=dataset.id)) is None
