import pytest

from extralit_server.enums import QuestionType, SchemaStatus
from tests.factories import (
    SchemaFactory,
    SchemaVersionFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2SuggestionFactory,
    WorkspaceFactory,
    WorkspaceUserFactory,
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
    await V2SuggestionFactory.create(record=record, question=q, value="flu", agent="e2e-agent", score=0.5)

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
    assert cell["record_id"] == str(record.id)
    assert cell["agent"] == "e2e-agent"
    assert cell["score"] == 0.5


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


async def test_workspace_projection_returns_manifest_rows_and_total(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    schema, version, q = await _schema_with_question(workspace)
    record = await V2RecordFactory.create(version=version, reference="doc-1")
    await V2SuggestionFactory.create(record=record, question=q, value="flu", agent="gpt-x", score=0.92)

    resp = await async_client.get(f"/api/v2/projection?workspace_id={workspace.id}", headers=owner_auth_header)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_references"] == 1
    [column] = [c for c in body["columns"] if c["question_name"] == q.name]
    assert column["schema_id"] == str(schema.id)
    assert column["sub_column"] is None
    [row] = body["rows"]
    assert row["reference"] == "doc-1"
    assert row["row_index"] == 0
    cell = row["cells"][column["name"]]
    assert cell == {
        "value": "flu",
        "source": "suggestion",
        "record_id": str(record.id),
        "agent": "gpt-x",
        "score": 0.92,
    }


async def test_workspace_projection_paginates_references(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    _schema, version, _q = await _schema_with_question(workspace)
    for i in range(3):
        await V2RecordFactory.create(version=version, reference=f"doc-{i}")

    resp = await async_client.get(
        f"/api/v2/projection?workspace_id={workspace.id}&offset=1&limit=1", headers=owner_auth_header
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_references"] == 3
    assert [r["reference"] for r in body["rows"]] == ["doc-1"]


async def test_workspace_projection_rejects_limit_over_100(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    resp = await async_client.get(
        f"/api/v2/projection?workspace_id={workspace.id}&limit=101", headers=owner_auth_header
    )
    assert resp.status_code == 422


async def test_workspace_projection_authz(async_client, annotator_auth_header, annotator):
    workspace = await WorkspaceFactory.create()
    _schema, version, q = await _schema_with_question(workspace)
    record = await V2RecordFactory.create(version=version, reference="doc-1")
    await V2SuggestionFactory.create(record=record, question=q, value="flu", agent="gpt-x", score=0.92)

    # Non-member: forbidden.
    resp = await async_client.get(f"/api/v2/projection?workspace_id={workspace.id}", headers=annotator_auth_header)
    assert resp.status_code == 403, resp.text

    # Member annotator: allowed to read.
    await WorkspaceUserFactory.create(workspace_id=workspace.id, user_id=annotator.id)
    resp = await async_client.get(f"/api/v2/projection?workspace_id={workspace.id}", headers=annotator_auth_header)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_references"] == 1


@pytest.mark.parametrize(
    ("query_params", "needs_workspace"),
    [
        ("limit=0", True),
        ("offset=-1", True),
        ("workspace_id=not-a-uuid", False),
        ("", False),  # workspace_id missing entirely
    ],
    ids=["limit_below_minimum", "offset_negative", "workspace_id_malformed", "workspace_id_missing"],
)
async def test_workspace_projection_rejects_invalid_query_params(
    async_client, owner_auth_header, query_params, needs_workspace
):
    query = query_params
    if needs_workspace:
        workspace = await WorkspaceFactory.create()
        query = f"workspace_id={workspace.id}&{query_params}"

    resp = await async_client.get(f"/api/v2/projection?{query}", headers=owner_auth_header)
    assert resp.status_code == 422, resp.text
