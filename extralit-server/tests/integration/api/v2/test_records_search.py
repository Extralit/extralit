from unittest.mock import AsyncMock

import pandera.pandas as pa
import pytest

from extralit_server.index.base import IndexSearchHit, IndexSearchResult
from tests.factories import SchemaFactory, SchemaVersionFactory, V2RecordFactory

pytestmark = pytest.mark.asyncio

BODY = pa.DataFrameSchema(
    columns={"title": pa.Column(pa.String, nullable=False), "year": pa.Column(pa.Int, nullable=True)}
).to_json()


async def _published(db):
    schema = await SchemaFactory.create()
    version = await SchemaVersionFactory.create(
        schema=schema,
        version=1,
        columns_cache=[
            {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
            {"name": "year", "dtype": "int64", "nullable": True, "review": None},
        ],
    )
    await schema.update(db, current_version_id=version.id)
    return schema, version


async def test_search_hydrates_from_postgres_in_hit_order(async_client, owner_auth_header, db, monkeypatch):
    schema, version = await _published(db)
    r1 = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Deep", "year": 2016})
    r2 = await V2RecordFactory.create(schema=schema, version=version, fields={"title": "Shallow", "year": 1999})

    # Engine returns r2 then r1; response must preserve that order and hydrate real payloads.
    fake = IndexSearchResult(hits=[IndexSearchHit(record_id=r2.id), IndexSearchHit(record_id=r1.id)], total=2)
    monkeypatch.setattr("extralit_server.index.lancedb_engine.LanceIndexEngine.search", AsyncMock(return_value=fake))

    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:search",
        headers=owner_auth_header,
        json={"text": "deep"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [str(r2.id), str(r1.id)]
    assert body["items"][1]["fields"]["title"] == "Deep"  # real PG payload, not from Lance


async def test_search_empty_result(async_client, owner_auth_header, db, monkeypatch):
    schema, _ = await _published(db)
    monkeypatch.setattr(
        "extralit_server.index.lancedb_engine.LanceIndexEngine.search",
        AsyncMock(return_value=IndexSearchResult(hits=[], total=0)),
    )
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:search",
        headers=owner_auth_header,
        json={"filters": [{"column": "year", "op": "ge", "value": 3000}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"items": [], "total": 0}


async def test_search_requires_membership(async_client, annotator_auth_header, db):
    # `annotator_auth_header` is a non-member of the schema's workspace (repo idiom for
    # the 403 case; see test_records.py::test_non_member_cannot_read_records).
    schema, _ = await _published(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/records:search",
        headers=annotator_auth_header,
        json={"text": "x"},
    )
    assert resp.status_code == 403, resp.text


async def test_rebuild_index_reindexes_all_records(async_client, owner_auth_header, db, monkeypatch):
    schema, version = await _published(db)
    await V2RecordFactory.create(schema=schema, version=version, fields={"title": "A", "year": 2001})
    await V2RecordFactory.create(schema=schema, version=version, fields={"title": "B", "year": 2002})

    calls = {}

    async def fake_rebuild(engine, db_, s, *, batch_size=500):
        calls["schema_id"] = s.id
        return 2

    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.rebuild_schema_index", fake_rebuild)

    resp = await async_client.post(f"/api/v2/schemas/{schema.id}:rebuild-index", headers=owner_auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"indexed": 2}
    assert calls["schema_id"] == schema.id


async def test_rebuild_index_requires_write_access(async_client, annotator_auth_header, db):
    # Non-member of the workspace → 403 (repo idiom; see test_records.py negative-authz tests).
    schema, _ = await _published(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}:rebuild-index",
        headers=annotator_auth_header,
    )
    assert resp.status_code == 403, resp.text
