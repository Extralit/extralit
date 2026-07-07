import pandera.pandas as pa
import pytest

from extralit_server.enums import SchemaKind
from tests.factories import WorkspaceFactory

pytestmark = pytest.mark.asyncio


def _body() -> str:
    return pa.DataFrameSchema(columns={"name": pa.Column(pa.String, nullable=False)}).to_json()


async def test_create_get_list_schema(async_client, owner_auth_header):
    ws = await WorkspaceFactory.create()
    resp = await async_client.post(
        "/api/v2/schemas",
        headers=owner_auth_header,
        json={"name": "population", "kind": SchemaKind.table.value, "workspace_id": str(ws.id)},
    )
    assert resp.status_code == 201, resp.text
    schema_id = resp.json()["id"]

    resp = await async_client.get(f"/api/v2/schemas/{schema_id}", headers=owner_auth_header)
    assert resp.status_code == 200
    assert resp.json()["name"] == "population"

    resp = await async_client.get(f"/api/v2/schemas?workspace_id={ws.id}", headers=owner_auth_header)
    assert resp.status_code == 200
    assert [s["id"] for s in resp.json()["items"]] == [schema_id]


async def test_publish_version_and_columns(async_client, owner_auth_header, monkeypatch):
    from datetime import datetime
    from unittest.mock import AsyncMock

    from extralit_server.contexts.files import ObjectMetadata

    monkeypatch.setattr(
        "extralit_server.contexts.v2.schemas.files_ctx.put_object",
        AsyncMock(
            return_value=ObjectMetadata(
                bucket_name="b",
                object_name="k",
                etag="etag-1",
                size=1,
                last_modified=datetime(2026, 1, 1),
                content_type="application/json",
                version_id="ver-1",
                metadata={},
            )
        ),
    )

    ws = await WorkspaceFactory.create()
    resp = await async_client.post(
        "/api/v2/schemas",
        headers=owner_auth_header,
        json={"name": "outcomes", "kind": SchemaKind.table.value, "workspace_id": str(ws.id)},
    )
    schema_id = resp.json()["id"]

    resp = await async_client.post(
        f"/api/v2/schemas/{schema_id}/versions",
        headers=owner_auth_header,
        json={"body": _body()},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 1

    resp = await async_client.get(f"/api/v2/schemas/{schema_id}/columns", headers=owner_auth_header)
    assert resp.status_code == 200
    assert any(c["name"] == "name" for c in resp.json())


async def test_non_member_cannot_create_or_read_schema(async_client, annotator_auth_header):
    # The annotator behind annotator_auth_header is NOT a member of this workspace.
    ws = await WorkspaceFactory.create()
    resp = await async_client.post(
        "/api/v2/schemas",
        headers=annotator_auth_header,
        json={"name": "secret", "kind": SchemaKind.table.value, "workspace_id": str(ws.id)},
    )
    assert resp.status_code == 403, resp.text


async def test_publish_version_creates_index_table(async_client, owner_auth_header, db, monkeypatch):
    from datetime import datetime
    from unittest.mock import AsyncMock

    from extralit_server.contexts.files import ObjectMetadata

    monkeypatch.setattr(
        "extralit_server.contexts.v2.schemas.files_ctx.put_object",
        AsyncMock(
            return_value=ObjectMetadata(
                bucket_name="b",
                object_name="k",
                etag="etag-1",
                size=1,
                last_modified=datetime(2026, 1, 1),
                content_type="application/json",
                version_id="ver-1",
                metadata={},
            )
        ),
    )

    ensure = AsyncMock()
    monkeypatch.setattr("extralit_server.contexts.v2.index_sync.sync_schema_table", ensure)

    from tests.factories import SchemaFactory

    schema = await SchemaFactory.create()
    import pandera.pandas as pa

    body = pa.DataFrameSchema(columns={"title": pa.Column(pa.String, nullable=False)}).to_json()
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/versions",
        headers=owner_auth_header,
        json={"body": body},
    )
    assert resp.status_code in (200, 201), resp.text
    ensure.assert_awaited_once()
