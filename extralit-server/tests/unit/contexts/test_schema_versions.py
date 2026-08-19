from unittest.mock import AsyncMock, patch

import pandas as pd
import pandera.pandas as pa
import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from extralit_server.contexts import schema_versions
from extralit_server.enums import DatasetStatus, FieldType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.database import Dataset, Field
from extralit_server.webhooks.v1.enums import DatasetEvent
from tests.factories import DatasetFactory, TextFieldFactory


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

    def test_a_pandas_extension_dtype_keeps_its_capitalized_spelling(self):
        # A column declared with a pandas extension dtype (`pd.Int64Dtype()`, the ordinary
        # way to get a nullable integer column) reports "Int64", not "int64", and that
        # spelling survives to_json/from_json into `Field.settings["dtype"]`. Folding it back
        # onto the numpy spelling is what `search_engine.commons.normalize_column_dtype`
        # exists for -- without it the column indexes as text and loses range queries.
        # Pinned here so the two halves cannot drift apart.
        body = pa.DataFrameSchema({"n": pa.Column(pd.Int64Dtype(), nullable=True)}).to_json()
        derived = schema_versions.derive_column_fields(body)
        assert derived[0]["settings"]["dtype"] == "Int64"

    def test_the_numpy_dtype_spelling_is_unaffected_by_nullability(self):
        # The counterpart: `nullable=True` on a plain numpy dtype does NOT change the
        # spelling, so the two are genuinely distinct declarations rather than one implying
        # the other.
        body = pa.DataFrameSchema({"n": pa.Column(pa.Int64, nullable=True)}).to_json()
        assert schema_versions.derive_column_fields(body)[0]["settings"]["dtype"] == "int64"

    def test_column_less_body_derives_no_fields(self):
        # A syntactically valid Pandera body with zero declared columns is a legal,
        # if degenerate, schema -- derivation returns an empty list rather than erroring.
        assert schema_versions.derive_column_fields(_empty_body()) == []


def _wider_body() -> str:
    return pa.DataFrameSchema(
        {
            "population": pa.Column(str, nullable=True),
            "n_arms": pa.Column(pa.Int64, nullable=False),
            "outcome": pa.Column(str, nullable=True),
        }
    ).to_json()


@pytest.mark.asyncio
class TestPublishVersion:
    async def test_publish_creates_version_one_and_leaves_the_dataset_a_draft(self, db):
        # Publishing a schema version is not publishing the dataset: `PUT /datasets/{id}/publish`
        # stays the sole draft -> ready transition, so a schema-backed dataset gets the same
        # DatasetPublishValidator checks as an annotation one and stays configurable until then.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        version = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert version.version == 1
        assert version.dataset_id == dataset.id
        assert dataset.current_schema_version_id == version.id
        assert dataset.status == DatasetStatus.draft

    async def test_publish_materializes_column_fields(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        fields = await _fields_for(db, dataset.id)
        assert {f.name for f in fields} == {"population", "n_arms"}
        assert all(f.settings["type"] == FieldType.column for f in fields)

    async def test_republishing_is_idempotent_for_unchanged_columns(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        v2 = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert v2.version == 2
        fields = await _fields_for(db, dataset.id)
        assert len(fields) == 2  # upserted, not duplicated

    async def test_republishing_adds_newly_declared_columns_while_still_a_draft(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_wider_body(), bucket="ws")
        fields = await _fields_for(db, dataset.id)
        assert {f.name for f in fields} == {"population", "n_arms", "outcome"}

    async def test_second_version_links_the_first_as_parent(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        v1 = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        v2 = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert v2.parent_version_id == v1.id

    async def test_publish_uploads_the_body_under_a_versioned_key(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        version = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert version.object_key == f"schemas/{dataset.id}/v1.json"

    async def test_invalid_body_is_rejected_before_anything_is_written(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        with pytest.raises(UnprocessableEntityError, match="not a valid Pandera DataFrameSchema"):
            await schema_versions.publish_version(db, _s3_client(), dataset, body="{not pandera}", bucket="ws")
        assert dataset.current_schema_version_id is None
        assert await _fields_for(db, dataset.id) == []

    async def test_a_first_schema_version_on_an_already_published_dataset_is_rejected(self, db):
        # Corollary of the rule above, and the reason the schema version must be published
        # while the dataset is still a draft: every column of a first version is a new column,
        # so an annotation dataset already published via PUT /datasets/{id}/publish (index
        # created, mapping strict) cannot retroactively become schema-backed.
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        with pytest.raises(UnprocessableEntityError, match="cannot be added to a published dataset"):
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")

        assert dataset.current_schema_version_id is None

    async def test_republishing_with_a_changed_column_dtype_is_rejected(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")

        changed_body = pa.DataFrameSchema(
            {
                "population": pa.Column(pa.Int64, nullable=True),  # was string
                "n_arms": pa.Column(pa.Int64, nullable=False),
            }
        ).to_json()

        with pytest.raises(UnprocessableEntityError, match="cannot change dtype"):
            await schema_versions.publish_version(db, _s3_client(), dataset, body=changed_body, bucket="ws")

        # Rejected before any write: no second version, no dtype mutation on the existing field.
        assert [v.version for v in await schema_versions.list_versions(db, dataset)] == [1]
        fields_by_name = {f.name: f for f in await _fields_for(db, dataset.id)}
        assert fields_by_name["population"].settings["dtype"] in {"string", "string[pyarrow]", "object"}

    async def test_republishing_with_an_unchanged_column_dtype_is_allowed(self, db):
        # Unchanged existing columns are always legal. Only a *changed* dtype is rejected.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        v2 = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert v2.version == 2

    async def test_adding_a_column_to_a_published_dataset_is_rejected(self, db):
        # The search index mapping is built with `"dynamic": "strict"` on the draft -> ready
        # transition and nothing evolves it afterwards, so a column added post-publish would
        # leave the dataset unwritable at `PUT /datasets/{id}/records/bulk`. Reject at publish
        # so the failure stays at the call that caused it.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        await dataset.update(db, status=DatasetStatus.ready)

        with pytest.raises(UnprocessableEntityError, match="cannot be added to a published dataset"):
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_wider_body(), bucket="ws")

        assert [v.version for v in await schema_versions.list_versions(db, dataset)] == [1]
        assert {f.name for f in await _fields_for(db, dataset.id)} == {"population", "n_arms"}

    async def test_a_column_colliding_with_an_annotation_field_is_rejected(self, db):
        # `Field.upsert_many` keys on (name, dataset_id), so without this check the upsert
        # would rewrite the text field's settings into a column -- silently dropping it from
        # record value validation, since column fields are deliberately not value-validated.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await TextFieldFactory.create(name="population", dataset=dataset)

        with pytest.raises(UnprocessableEntityError, match="collides with an existing text field"):
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")

        assert await schema_versions.list_versions(db, dataset) == []
        fields_by_name = {f.name: f for f in await _fields_for(db, dataset.id)}
        assert fields_by_name["population"].settings["type"] == FieldType.text

    async def test_publish_notifies_the_dataset_updated_webhook_event(self, db):
        # A schema version is a dataset mutation, so it gets `updated` -- the same event
        # update_dataset fires for any other attribute change. `published` belongs to
        # contexts/datasets.py::publish_dataset alone, now that this no longer flips status.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)

        with patch("extralit_server.contexts.schema_versions.notify_dataset_event_v1") as mock_notify:
            mock_notify.return_value = []
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")

        mock_notify.assert_awaited_once()
        awaited_args = mock_notify.await_args.args
        assert awaited_args[1] == DatasetEvent.updated
        assert awaited_args[2] is dataset

    async def test_every_republish_notifies_updated_too(self, db):
        # Without this a consumer subscribed to `updated` hears about version 1 and never
        # learns that versions 2..n exist.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)

        with patch("extralit_server.contexts.schema_versions.notify_dataset_event_v1") as mock_notify:
            mock_notify.return_value = []
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
            v2 = await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")

        assert v2.version == 2
        assert [call.args[1] for call in mock_notify.await_args_list] == [
            DatasetEvent.updated,
            DatasetEvent.updated,
        ]
        assert all(call.args[2] is dataset for call in mock_notify.await_args_list)

    async def test_publish_of_a_column_less_body_still_creates_a_version(self, db):
        # `derive_column_fields` legally returns an empty list for a column-less body;
        # `Field.upsert_many` raises on an empty `objects` list, so publish_version must
        # skip the upsert call rather than blow up on a degenerate-but-valid schema.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        version = await schema_versions.publish_version(db, _s3_client(), dataset, body=_empty_body(), bucket="ws")
        assert version.version == 1
        assert await _fields_for(db, dataset.id) == []


class TestVersionAllocationLocking:
    """Pin both halves of the version-allocation race story.

    The unit suite runs on SQLite, which cannot exercise real row locking, so these assert
    the two statically checkable facts the guarantee rests on rather than simulating a race.
    """

    def test_the_row_lock_reaches_postgresql_and_is_dropped_by_sqlite(self):
        # This asymmetry IS the documented gap: SQLAlchemy compiles `with_for_update()` away
        # on SQLite silently rather than raising, so the allocation is serialized on
        # PostgreSQL only. If SQLite ever gains a rendering for it, this fails and the
        # caveat in `_next_version_number` and fold-followups section 5 should be revisited.
        stmt = select(Dataset.id).with_for_update()
        assert "FOR UPDATE" in str(stmt.compile(dialect=postgresql.dialect()))
        assert "FOR UPDATE" not in str(stmt.compile(dialect=sqlite.dialect()))


@pytest.mark.asyncio
class TestVersionAllocationLockingStatement:
    async def test_publish_takes_a_row_lock_before_allocating(self, db):
        # Guards the PostgreSQL half: without this locking read, two publishers derive the
        # same version number, hence the same object key, and overwrite each other's body
        # after one has already committed a checksum for its own. Asserting the statement is
        # issued is the most this suite can do on SQLite.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        executed = []
        original_execute = db.execute

        async def _spy(statement, *args, **kwargs):
            executed.append(statement)
            return await original_execute(statement, *args, **kwargs)

        with patch.object(db, "execute", _spy):
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")

        assert any(getattr(statement, "_for_update_arg", None) is not None for statement in executed), (
            "publish_version must take a row lock before allocating a version number"
        )


@pytest.mark.asyncio
class TestReadVersions:
    async def test_list_versions_is_ordered_by_version_number(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        for _ in range(3):
            await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert [v.version for v in await schema_versions.list_versions(db, dataset)] == [1, 2, 3]

    async def test_get_version_by_number(self, db):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await schema_versions.publish_version(db, _s3_client(), dataset, body=_body(), bucket="ws")
        assert (await schema_versions.get_version_by_number(db, dataset.id, 1)).version == 1
        assert await schema_versions.get_version_by_number(db, dataset.id, 99) is None
