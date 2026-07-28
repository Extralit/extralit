import pytest

from tests.factories import (
    DatasetFactory,
    FieldFactory,
    QuestionFactory,
    RecordFactory,
    SchemaVersionFactory,
    SuggestionFactory,
    WorkspaceFactory,
    WorkspaceUserFactory,
)

pytestmark = pytest.mark.asyncio


async def _dataset_with_question(workspace):
    dataset = await DatasetFactory.create(workspace=workspace)
    version = await SchemaVersionFactory.create(dataset=dataset)
    await dataset.update(dataset.current_async_session, current_schema_version_id=version.id)
    await FieldFactory.create(
        dataset=dataset, name="disease", settings={"type": "column", "dtype": "string[pyarrow]", "nullable": True}
    )
    question = await QuestionFactory.create(
        dataset=dataset, name="dx", settings={"type": "text", "columns": ["disease"]}
    )
    return dataset, question


async def test_workspace_projection_returns_manifest_rows_and_total(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    dataset, q = await _dataset_with_question(workspace)
    record = await RecordFactory.create(dataset=dataset, reference="doc-1")
    await SuggestionFactory.create(record=record, question=q, value="flu", agent="gpt-x", score=0.92)

    resp = await async_client.get(
        f"/api/v1/me/datasets/projection?workspace_id={workspace.id}", headers=owner_auth_header
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_references"] == 1
    [column] = [c for c in body["columns"] if c["question_name"] == q.name]
    assert column["dataset_id"] == str(dataset.id)
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
    dataset, _q = await _dataset_with_question(workspace)
    for i in range(3):
        await RecordFactory.create(dataset=dataset, reference=f"doc-{i}")

    resp = await async_client.get(
        f"/api/v1/me/datasets/projection?workspace_id={workspace.id}&offset=1&limit=1", headers=owner_auth_header
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_references"] == 3
    assert [r["reference"] for r in body["rows"]] == ["doc-1"]


async def test_workspace_projection_rejects_limit_over_100(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    resp = await async_client.get(
        f"/api/v1/me/datasets/projection?workspace_id={workspace.id}&limit=101", headers=owner_auth_header
    )
    assert resp.status_code == 422


async def test_workspace_projection_authz(async_client, annotator_auth_header, annotator):
    workspace = await WorkspaceFactory.create()
    dataset, q = await _dataset_with_question(workspace)
    record = await RecordFactory.create(dataset=dataset, reference="doc-1")
    await SuggestionFactory.create(record=record, question=q, value="flu", agent="gpt-x", score=0.92)

    # Non-member: forbidden.
    resp = await async_client.get(
        f"/api/v1/me/datasets/projection?workspace_id={workspace.id}", headers=annotator_auth_header
    )
    assert resp.status_code == 403, resp.text

    # Member annotator: allowed to read.
    await WorkspaceUserFactory.create(workspace_id=workspace.id, user_id=annotator.id)
    resp = await async_client.get(
        f"/api/v1/me/datasets/projection?workspace_id={workspace.id}", headers=annotator_auth_header
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_references"] == 1


async def test_workspace_projection_does_not_leak_a_foreign_workspaces_rows(
    async_client, annotator_auth_header, annotator
):
    """The worst-case defect for this endpoint: a member of workspace A must never see
    workspace B's projection, even via a crafted `workspace_id` query param."""
    own_workspace = await WorkspaceFactory.create()
    await WorkspaceUserFactory.create(workspace_id=own_workspace.id, user_id=annotator.id)

    foreign_workspace = await WorkspaceFactory.create()
    dataset, q = await _dataset_with_question(foreign_workspace)
    record = await RecordFactory.create(dataset=dataset, reference="secret-doc")
    await SuggestionFactory.create(record=record, question=q, value="classified")

    resp = await async_client.get(
        f"/api/v1/me/datasets/projection?workspace_id={foreign_workspace.id}", headers=annotator_auth_header
    )

    assert resp.status_code == 403, resp.text


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

    resp = await async_client.get(f"/api/v1/me/datasets/projection?{query}", headers=owner_auth_header)
    assert resp.status_code == 422, resp.text
