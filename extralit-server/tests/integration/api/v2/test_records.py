from unittest.mock import AsyncMock
from uuid import uuid4

import pandera.pandas as pa
import pytest

from extralit_server.enums import V2RecordStatus
from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import SchemaFactory, SchemaVersionFactory, V2RecordFactory, WorkspaceUserFactory

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
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(schema=schema, version=1)
    await schema.update(db, current_version_id=version.id)
    return schema, version


async def test_bulk_upsert_creates_and_updates_records(async_client, owner_auth_header, db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema, version = await _published_schema(db)

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={
            "items": [
                {"fields": {"name": "Ada", "age": 36}, "reference": "pmid:1", "external_id": "x-1"},
                {"fields": {"name": "Grace", "age": None}, "reference": "pmid:2"},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["external_id"] == "x-1"
    assert body["items"][0]["fields"] == {"name": "Ada", "age": 36}
    assert body["items"][0]["schema_version_id"] == str(version.id)
    assert body["items"][0]["status"] == V2RecordStatus.pending.value

    # Re-upsert by external_id updates in place instead of duplicating.
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada L.", "age": 37}, "reference": "pmid:1", "external_id": "x-1"}]},
    )
    assert resp.status_code == 200, resp.text

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records", headers=owner_auth_header)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_bulk_upsert_validation_failure_returns_422(async_client, owner_auth_header, db, monkeypatch):
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Bob", "age": "not-a-number"}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 422, resp.text
    assert "items[0]" in resp.json()["detail"]
    assert "age" in resp.json()["detail"]


async def test_bulk_upsert_without_published_version_returns_422(async_client, owner_auth_header, monkeypatch):
    _patch_fetch(monkeypatch)
    schema = await SchemaFactory.create()

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada"}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 422, resp.text
    assert "no published version" in resp.json()["detail"]


async def test_bulk_upsert_unknown_schema_returns_404(async_client, owner_auth_header, monkeypatch):
    _patch_fetch(monkeypatch)
    resp = await async_client.post(
        f"/api/v2/schemas/{uuid4()}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada"}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 404, resp.text


async def test_list_records_paginates_and_filters(async_client, owner_auth_header, db):
    schema, version = await _published_schema(db)
    await V2RecordFactory.create(version=version, reference="pmid:1")
    await V2RecordFactory.create(version=version, reference="pmid:1", status=V2RecordStatus.completed)
    await V2RecordFactory.create(version=version, reference="pmid:2")

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records?offset=1&limit=1", headers=owner_auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 3
    assert len(resp.json()["items"]) == 1

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records?reference=pmid:1", headers=owner_auth_header)
    assert resp.json()["total"] == 2

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records?status=completed", headers=owner_auth_header)
    assert resp.json()["total"] == 1


async def test_delete_records(async_client, owner_auth_header, db):
    schema, version = await _published_schema(db)
    r1 = await V2RecordFactory.create(version=version)
    r2 = await V2RecordFactory.create(version=version)
    r3 = await V2RecordFactory.create(version=version)

    resp = await async_client.delete(
        f"/api/v2/schemas/{schema.id}/records?ids={r1.id},{r2.id}", headers=owner_auth_header
    )
    assert resp.status_code == 204, resp.text

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records", headers=owner_auth_header)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["id"] == str(r3.id)


async def test_delete_records_validates_ids(async_client, owner_auth_header, db):
    schema, _ = await _published_schema(db)

    resp = await async_client.delete(f"/api/v2/schemas/{schema.id}/records?ids=", headers=owner_auth_header)
    assert resp.status_code == 422
    assert "No record IDs provided" in resp.json()["detail"]

    too_many = ",".join(str(uuid4()) for _ in range(101))
    resp = await async_client.delete(f"/api/v2/schemas/{schema.id}/records?ids={too_many}", headers=owner_auth_header)
    assert resp.status_code == 422
    assert "more than" in resp.json()["detail"]


async def test_member_annotator_can_read_but_not_write_records(
    async_client, annotator_auth_header, annotator, db, monkeypatch
):
    _patch_fetch(monkeypatch)
    schema, version = await _published_schema(db)
    await WorkspaceUserFactory.create(workspace_id=schema.workspace_id, user_id=annotator.id)

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records", headers=annotator_auth_header)
    assert resp.status_code == 200, resp.text

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=annotator_auth_header,
        json={"items": [{"fields": {"name": "Ada"}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 403, resp.text

    record = await V2RecordFactory.create(version=version)
    resp = await async_client.delete(
        f"/api/v2/schemas/{schema.id}/records?ids={record.id}", headers=annotator_auth_header
    )
    assert resp.status_code == 403, resp.text


async def test_non_member_cannot_read_records(async_client, annotator_auth_header, db):
    schema, _ = await _published_schema(db)

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/records", headers=annotator_auth_header)
    assert resp.status_code == 403, resp.text


async def test_bulk_upsert_syncs_index(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    sync = AsyncMock()
    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.sync_upserted_records", sync)
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada", "age": 36}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 200, resp.text
    sync.assert_awaited_once()


async def test_bulk_upsert_survives_index_failure(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    # Real best-effort path: engine raises, request must still be 200.
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.upsert",
        AsyncMock(side_effect=RuntimeError("lance down")),
    )
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.ensure_table",
        AsyncMock(side_effect=RuntimeError("lance down")),
    )
    _patch_fetch(monkeypatch)
    schema, _ = await _published_schema(db)

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:bulk-upsert",
        headers=owner_auth_header,
        json={"items": [{"fields": {"name": "Ada", "age": 36}, "reference": "pmid:1"}]},
    )
    assert resp.status_code == 200, resp.text


async def test_delete_syncs_index(async_client, owner_auth_header, db, monkeypatch):
    from unittest.mock import AsyncMock

    sync = AsyncMock()
    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.sync_deleted_records", sync)
    _patch_fetch(monkeypatch)
    schema, version = await _published_schema(db)
    from tests.factories import V2RecordFactory

    record = await V2RecordFactory.create(schema=schema, version=version, fields={"name": "X"})
    resp = await async_client.delete(
        f"/api/v2/schemas/{schema.id}/records?ids={record.id}",
        headers=owner_auth_header,
    )
    assert resp.status_code == 204, resp.text
    sync.assert_awaited_once()
