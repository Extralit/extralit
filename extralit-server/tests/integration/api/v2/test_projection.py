import pytest

from extralit_server.enums import QuestionType, SchemaStatus
from tests.factories import (
    SchemaFactory,
    SchemaVersionFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2SuggestionFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.asyncio


async def _schema_with_question(workspace):
    schema = await SchemaFactory.create(status=SchemaStatus.published, workspace=workspace)
    version = await SchemaVersionFactory.create(
        schema=schema, columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}]
    )
    q = await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )
    return schema, version, q


async def test_projection_view_resolves_suggestion_cell(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    schema, version, q = await _schema_with_question(workspace)
    record = await V2RecordFactory.create(version=version, reference="doc-1")
    await V2SuggestionFactory.create(record=record, question=q, value="flu")

    resp = await async_client.get(
        f"/api/v2/projection/references/doc-1?workspace_id={workspace.id}", headers=owner_auth_header
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reference"] == "doc-1"
    assert body["total_records"] == 1
    proj_record = body["records"][0]
    assert proj_record["record_id"] == str(record.id)
    assert proj_record["schema_id"] == str(schema.id)
    cell = proj_record["cells"][0]
    assert cell["question_name"] == "dx"
    assert cell["value"] == "flu"
    assert cell["source"] == "suggestion"


async def test_projection_view_unknown_reference_returns_empty(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    resp = await async_client.get(
        f"/api/v2/projection/references/doc-nope?workspace_id={workspace.id}", headers=owner_auth_header
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reference"] == "doc-nope"
    assert body["total_records"] == 0
    assert body["records"] == []
