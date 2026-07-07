from datetime import datetime
from unittest.mock import AsyncMock

import pandera.pandas as pa
import pytest

from extralit_server.contexts.files import ObjectMetadata
from extralit_server.contexts.v2 import schemas as schemas_ctx
from extralit_server.enums import SchemaKind, SchemaStatus
from extralit_server.models.v2 import Schema, SchemaVersion
from tests.factories import WorkspaceFactory

pytestmark = pytest.mark.asyncio


def _body() -> str:
    return pa.DataFrameSchema(columns={"name": pa.Column(pa.String, nullable=False)}).to_json()


def _patch_put_object(monkeypatch, bucket: str) -> AsyncMock:
    put = AsyncMock(
        return_value=ObjectMetadata(
            bucket_name=bucket,
            object_name="k",
            etag="etag-1",
            size=1,
            last_modified=datetime(2026, 1, 1),
            content_type="application/json",
            version_id="ver-1",
            metadata={},
        )
    )
    monkeypatch.setattr("extralit_server.contexts.v2.schemas.files_ctx.put_object", put)
    return put


async def test_create_and_list_schema(db):
    ws = await WorkspaceFactory.create()
    schema = await schemas_ctx.create_schema(db, name="population", kind=SchemaKind.table, workspace_id=ws.id)
    assert isinstance(schema, Schema)

    listed = await schemas_ctx.list_schemas(db, workspace_id=ws.id)
    assert [s.id for s in listed] == [schema.id]


async def test_publish_version_uploads_body_and_advances_pointer(db, monkeypatch):
    ws = await WorkspaceFactory.create()
    _patch_put_object(monkeypatch, ws.name)
    schema = await schemas_ctx.create_schema(db, name="population", kind=SchemaKind.table, workspace_id=ws.id)

    s3 = AsyncMock()
    version = await schemas_ctx.publish_version(db, s3, schema, body=_body(), bucket=ws.name, created_by=None)

    assert isinstance(version, SchemaVersion)
    assert version.version == 1
    assert version.object_key == f"schemas/{schema.id}/v1.json"
    # The S3 object version returned by put_object is pinned on the row.
    assert version.object_version_id == "ver-1"
    assert any(c["name"] == "name" for c in version.columns_cache)

    refreshed = await Schema.get(db, schema.id)
    assert refreshed.current_version_id == version.id
    assert refreshed.status == SchemaStatus.published

    # Second publish increments version and links lineage
    v2 = await schemas_ctx.publish_version(db, s3, refreshed, body=_body(), bucket=ws.name)
    assert v2.version == 2
    assert v2.parent_version_id == version.id


async def test_publish_version_merges_review_widgets_into_columns_cache(db, monkeypatch):
    ws = await WorkspaceFactory.create()
    _patch_put_object(monkeypatch, ws.name)
    schema = await schemas_ctx.create_schema(db, name="ratings", kind=SchemaKind.table, workspace_id=ws.id)

    s3 = AsyncMock()
    version = await schemas_ctx.publish_version(
        db, s3, schema, body=_body(), bucket=ws.name, review_widgets={"name": {"type": "text"}}
    )
    by_name = {c["name"]: c for c in version.columns_cache}
    assert by_name["name"]["review"] == {"type": "text"}
    assert version.review_widgets == {"name": {"type": "text"}}
