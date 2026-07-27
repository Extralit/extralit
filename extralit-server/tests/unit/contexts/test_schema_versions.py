from unittest.mock import AsyncMock

import pandera.pandas as pa
import pytest
from sqlalchemy import select

from extralit_server.contexts import schema_versions
from extralit_server.enums import DatasetStatus, FieldType
from extralit_server.models.database import Field
from tests.factories import DatasetFactory


def _body() -> str:
    return pa.DataFrameSchema(
        {
            "population": pa.Column(str, nullable=True),
            "n_arms": pa.Column(pa.Int64, nullable=False),
        }
    ).to_json()


def _empty_body() -> str:
    return pa.DataFrameSchema({}).to_json()


async def _fields_for(db, dataset_id) -> list[Field]:
    stmt = select(Field).where(Field.dataset_id == dataset_id)
    return list((await db.execute(stmt)).scalars().all())


def _s3_client() -> AsyncMock:
    """A stand-in S3 client good enough for `files_ctx.put_object`'s head_object round-trip.

    A bare `AsyncMock()` doesn't work here: every attribute of an unspecced AsyncMock is
    itself an AsyncMock, so `head_response.get(...)` inside `put_object` returns an
    un-awaited coroutine instead of a value. Stub `head_object` to return a plain dict.
    """
    client = AsyncMock()
    client.head_object.return_value = {
        "ETag": '"etag"',
        "ContentLength": 0,
        "LastModified": None,
        "ContentType": "application/json",
        "VersionId": "v1",
        "Metadata": {},
    }
    return client


class TestDeriveColumnFields:
    def test_one_field_per_pandera_column(self):
        fields = schema_versions.derive_column_fields(_body())
        assert {f["name"] for f in fields} == {"population", "n_arms"}

    def test_dtype_and_nullability_come_from_the_body(self):
        by_name = {f["name"]: f for f in schema_versions.derive_column_fields(_body())}
        assert by_name["n_arms"]["settings"]["dtype"] == "int64"
        assert by_name["n_arms"]["settings"]["nullable"] is False
        assert by_name["population"]["settings"]["nullable"] is True

    def test_every_derived_field_is_a_column_field(self):
        for field in schema_versions.derive_column_fields(_body()):
            assert field["settings"]["type"] == FieldType.column

    def test_review_widgets_land_on_the_matching_field(self):
        overlay = {"population": {"widget": "textarea"}}
        by_name = {f["name"]: f for f in schema_versions.derive_column_fields(_body(), overlay)}
        assert by_name["population"]["settings"]["review"] == {"widget": "textarea"}
        assert by_name["n_arms"]["settings"]["review"] is None

    def test_column_fields_are_never_required(self):
        # `required` gates annotator input; a column is an ingestion input, never required.
        for field in schema_versions.derive_column_fields(_body()):
            assert field["required"] is False

    def test_column_less_body_derives_no_fields(self):
        # A syntactically valid Pandera body with zero declared columns is a legal,
        # if degenerate, schema -- derivation returns an empty list rather than erroring.
        assert schema_versions.derive_column_fields(_empty_body()) == []


@pytest.mark.asyncio
class TestPublishVersion:
    async def test_publish_creates_version_one_and_marks_the_dataset_ready(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        version = await schema_versions.publish_version(
            db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws"
        )
        assert version.version == 1
        assert version.dataset_id == dataset.id
        assert dataset.current_schema_version_id == version.id
        assert dataset.status == DatasetStatus.ready

    async def test_publish_materializes_column_fields(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws")
        fields = await _fields_for(db, dataset.id)
        assert {f.name for f in fields} == {"population", "n_arms"}
        assert all(f.settings["type"] == FieldType.column for f in fields)

    async def test_republishing_is_idempotent_for_unchanged_columns(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws")
        v2 = await schema_versions.publish_version(
            db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws"
        )
        assert v2.version == 2
        fields = await _fields_for(db, dataset.id)
        assert len(fields) == 2  # upserted, not duplicated

    async def test_republishing_adds_newly_declared_columns(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws")
        wider = pa.DataFrameSchema(
            {
                "population": pa.Column(str, nullable=True),
                "n_arms": pa.Column(pa.Int64, nullable=False),
                "outcome": pa.Column(str, nullable=True),
            }
        ).to_json()
        await schema_versions.publish_version(db, mock_search_engine, _s3_client(), dataset, body=wider, bucket="ws")
        fields = await _fields_for(db, dataset.id)
        assert {f.name for f in fields} == {"population", "n_arms", "outcome"}

    async def test_second_version_links_the_first_as_parent(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        v1 = await schema_versions.publish_version(
            db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws"
        )
        v2 = await schema_versions.publish_version(
            db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws"
        )
        assert v2.parent_version_id == v1.id

    async def test_publish_creates_the_search_index(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws")
        mock_search_engine.create_index.assert_awaited()

    async def test_publish_uploads_the_body_under_a_versioned_key(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        s3 = _s3_client()
        version = await schema_versions.publish_version(db, mock_search_engine, s3, dataset, body=_body(), bucket="ws")
        assert version.object_key == f"schemas/{dataset.id}/v1.json"

    async def test_invalid_body_is_rejected_before_anything_is_written(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        with pytest.raises(Exception):
            await schema_versions.publish_version(
                db, mock_search_engine, _s3_client(), dataset, body="{not pandera}", bucket="ws"
            )
        assert dataset.current_schema_version_id is None
        assert await _fields_for(db, dataset.id) == []

    async def test_publish_of_a_column_less_body_still_creates_a_version(self, db, mock_search_engine):
        # `derive_column_fields` legally returns an empty list for a column-less body;
        # `Field.upsert_many` raises on an empty `objects` list, so publish_version must
        # skip the upsert call rather than blow up on a degenerate-but-valid schema.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        version = await schema_versions.publish_version(
            db, mock_search_engine, _s3_client(), dataset, body=_empty_body(), bucket="ws"
        )
        assert version.version == 1
        assert dataset.status == DatasetStatus.ready
        assert await _fields_for(db, dataset.id) == []


@pytest.mark.asyncio
class TestReadVersions:
    async def test_list_versions_is_ordered_by_version_number(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        for _ in range(3):
            await schema_versions.publish_version(
                db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws"
            )
        assert [v.version for v in await schema_versions.list_versions(db, dataset)] == [1, 2, 3]

    async def test_get_version_by_number(self, db, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, mock_search_engine, _s3_client(), dataset, body=_body(), bucket="ws")
        assert (await schema_versions.get_version_by_number(db, dataset.id, 1)).version == 1
        assert await schema_versions.get_version_by_number(db, dataset.id, 99) is None
