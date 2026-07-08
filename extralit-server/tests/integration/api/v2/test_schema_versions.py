import pytest

from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def test_get_single_version_by_number(async_client, owner_auth_header, db):
    schema = await SchemaFactory.create()
    await SchemaVersionFactory.create(
        schema=schema, version=1, columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}]
    )
    await db.commit()

    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/versions/1", headers=owner_auth_header)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == 1
    assert body["columns_cache"][0]["name"] == "disease"


async def test_get_unknown_version_404(async_client, owner_auth_header, db):
    schema = await SchemaFactory.create()
    await db.commit()
    resp = await async_client.get(f"/api/v2/schemas/{schema.id}/versions/999", headers=owner_auth_header)
    assert resp.status_code == 404
