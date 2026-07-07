from unittest.mock import AsyncMock

import pandera.pandas as pa
import pytest

from extralit_server.contexts.v2 import records as records_ctx
from extralit_server.enums import SchemaKind, V2RecordStatus
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.v2 import Schema, SchemaVersion, V2Record
from tests.factories import SchemaFactory, SchemaVersionFactory, V2RecordFactory, WorkspaceFactory

pytestmark = pytest.mark.asyncio

BODY = pa.DataFrameSchema(
    columns={
        "name": pa.Column(pa.String, nullable=False),
        "age": pa.Column(pa.Int, nullable=True),
    }
).to_json()


def _patch_fetch(monkeypatch, body: str = BODY) -> AsyncMock:
    fetch = AsyncMock(return_value=body)
    monkeypatch.setattr("extralit_server.contexts.v2.records._fetch_body_json", fetch)
    return fetch


async def _published_schema(db) -> tuple[Schema, SchemaVersion]:
    schema = await SchemaFactory.create(kind=SchemaKind.table)
    version = await SchemaVersionFactory.create(schema=schema, version=1)
    await schema.update(db, current_version_id=version.id)
    return schema, version


def _item(**overrides) -> dict:
    from extralit_server.api.schemas.v2.records import RecordUpsert

    payload = {"fields": {"name": "Ada", "age": 36}, "reference": "pmid:1"}
    payload.update(overrides)
    return RecordUpsert(**payload)


async def test_bulk_upsert_creates_records_in_input_order(db, monkeypatch):
    fetch = _patch_fetch(monkeypatch)
    schema, version = await _published_schema(db)

    s3 = AsyncMock()
    records = await records_ctx.bulk_upsert_records(
        db,
        s3,
        schema,
        items=[
            _item(external_id="x-1", fields={"name": "Ada", "age": 36}),
            _item(fields={"name": "Grace", "age": None}, reference="pmid:2"),
        ],
        bucket="ws",
    )

    assert [r.external_id for r in records] == ["x-1", None]
    assert records[0].schema_version_id == version.id
    assert records[0].fields == {"name": "Ada", "age": 36}
    assert records[1].fields == {"name": "Grace", "age": None}
    assert records[0].status == V2RecordStatus.pending
    assert fetch.await_count == 1


async def test_bulk_upsert_updates_existing_by_external_id(db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)
    s3 = AsyncMock()

    first = await records_ctx.bulk_upsert_records(db, s3, schema, items=[_item(external_id="x-1")], bucket="ws")
    updated = await records_ctx.bulk_upsert_records(
        db,
        s3,
        schema,
        items=[_item(external_id="x-1", fields={"name": "Ada L.", "age": 37}, status=V2RecordStatus.completed)],
        bucket="ws",
    )

    assert updated[0].id == first[0].id
    assert updated[0].fields == {"name": "Ada L.", "age": 37}
    assert updated[0].status == V2RecordStatus.completed

    _, total = await records_ctx.list_records(db, schema, offset=0, limit=10)
    assert total == 1


async def test_bulk_upsert_fetches_body_once_per_distinct_version(db, monkeypatch):
    fetch = _patch_fetch(monkeypatch)
    schema, version1 = await _published_schema(db)
    version2 = await SchemaVersionFactory.create(schema=schema, version=2)
    await schema.update(db, current_version_id=version2.id)

    s3 = AsyncMock()
    records = await records_ctx.bulk_upsert_records(
        db,
        s3,
        schema,
        items=[
            _item(schema_version_id=version1.id),
            _item(reference="pmid:2"),
            _item(schema_version_id=version1.id, reference="pmid:3"),
            _item(reference="pmid:4"),
        ],
        bucket="ws",
    )

    assert fetch.await_count == 2
    assert records[0].schema_version_id == version1.id
    assert records[1].schema_version_id == version2.id


async def test_bulk_upsert_validation_failure_is_all_or_nothing(db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)
    s3 = AsyncMock()

    with pytest.raises(UnprocessableEntityError) as exc:
        await records_ctx.bulk_upsert_records(
            db,
            s3,
            schema,
            items=[_item(), _item(fields={"name": "Bob", "age": "not-a-number"}, reference="pmid:2")],
            bucket="ws",
        )
    assert "items[1]" in exc.value.message
    assert "age" in exc.value.message

    _, total = await records_ctx.list_records(db, schema, offset=0, limit=10)
    assert total == 0


async def test_bulk_upsert_requires_published_version(db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema = await SchemaFactory.create()

    with pytest.raises(UnprocessableEntityError, match="no published version"):
        await records_ctx.bulk_upsert_records(db, AsyncMock(), schema, items=[_item()], bucket="ws")


async def test_bulk_upsert_rejects_foreign_schema_version_pin(db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)
    _, other_version = await _published_schema(db)

    with pytest.raises(UnprocessableEntityError, match="does not belong"):
        await records_ctx.bulk_upsert_records(
            db, AsyncMock(), schema, items=[_item(schema_version_id=other_version.id)], bucket="ws"
        )


async def test_bulk_upsert_rejects_duplicate_external_ids_in_payload(db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)

    with pytest.raises(UnprocessableEntityError, match=r"[Dd]uplicate"):
        await records_ctx.bulk_upsert_records(
            db,
            AsyncMock(),
            schema,
            items=[_item(external_id="x-1"), _item(external_id="x-1", reference="pmid:2")],
            bucket="ws",
        )


async def test_list_records_paginates_and_filters(db):
    schema, version = await _published_schema(db)
    _, other_version = await _published_schema(db)

    r1 = await V2RecordFactory.create(version=version, reference="pmid:1")
    r2 = await V2RecordFactory.create(version=version, reference="pmid:1", status=V2RecordStatus.completed)
    r3 = await V2RecordFactory.create(version=version, reference="pmid:2")
    await V2RecordFactory.create(version=other_version)

    items, total = await records_ctx.list_records(db, schema, offset=0, limit=10)
    assert total == 3
    assert [r.id for r in items] == [r1.id, r2.id, r3.id]

    items, total = await records_ctx.list_records(db, schema, offset=1, limit=1)
    assert total == 3
    assert len(items) == 1

    items, total = await records_ctx.list_records(db, schema, offset=0, limit=10, reference="pmid:1")
    assert total == 2

    items, total = await records_ctx.list_records(db, schema, offset=0, limit=10, status=V2RecordStatus.completed)
    assert total == 1
    assert items[0].id == r2.id


async def test_delete_records_is_schema_scoped(db):
    schema, version = await _published_schema(db)
    _, other_version = await _published_schema(db)

    r1 = await V2RecordFactory.create(version=version)
    r2 = await V2RecordFactory.create(version=version)
    r3 = await V2RecordFactory.create(version=version)
    foreign = await V2RecordFactory.create(version=other_version)

    deleted = await records_ctx.delete_records(db, schema, [r1.id, r2.id, foreign.id])
    assert deleted == 2

    _, total = await records_ctx.list_records(db, schema, offset=0, limit=10)
    assert total == 1
    assert (await V2Record.get(db, r3.id)) is not None
    assert (await V2Record.get(db, foreign.id)) is not None


async def test_list_records_by_reference_is_workspace_scoped(db):
    workspace_a = await WorkspaceFactory.create()
    workspace_b = await WorkspaceFactory.create()

    schema1 = await SchemaFactory.create(workspace=workspace_a)
    schema2 = await SchemaFactory.create(workspace=workspace_a)
    schema3 = await SchemaFactory.create(workspace=workspace_b)
    version1 = await SchemaVersionFactory.create(schema=schema1, version=1)
    version2 = await SchemaVersionFactory.create(schema=schema2, version=1)
    version3 = await SchemaVersionFactory.create(schema=schema3, version=1)

    r1 = await V2RecordFactory.create(version=version1, reference="pmid:99")
    r2 = await V2RecordFactory.create(version=version2, reference="pmid:99")
    await V2RecordFactory.create(version=version3, reference="pmid:99")  # workspace B
    await V2RecordFactory.create(version=version1, reference="pmid:other")

    records = await records_ctx.list_records_by_reference(db, workspace_id=workspace_a.id, reference="pmid:99")
    assert {r.id for r in records} == {r1.id, r2.id}
