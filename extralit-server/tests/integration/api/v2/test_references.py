import pytest

from tests.factories import (
    SchemaFactory,
    SchemaVersionFactory,
    V2RecordFactory,
    WorkspaceFactory,
    WorkspaceUserFactory,
)

pytestmark = pytest.mark.asyncio


async def _schema_with_version(workspace, name: str):
    schema = await SchemaFactory.create(workspace=workspace, name=name)
    version = await SchemaVersionFactory.create(schema=schema, version=1)
    return schema, version


async def test_reference_view_groups_records_per_schema_in_workspace(async_client, owner_auth_header):
    workspace_a = await WorkspaceFactory.create()
    workspace_b = await WorkspaceFactory.create()

    schema_pop, version_pop = await _schema_with_version(workspace_a, "population")
    schema_out, version_out = await _schema_with_version(workspace_a, "outcomes")
    _, version_foreign = await _schema_with_version(workspace_b, "foreign")

    r1 = await V2RecordFactory.create(version=version_pop, reference="pmid:99")
    r2 = await V2RecordFactory.create(version=version_pop, reference="pmid:99")
    r3 = await V2RecordFactory.create(version=version_out, reference="pmid:99")
    await V2RecordFactory.create(version=version_foreign, reference="pmid:99")  # workspace B
    await V2RecordFactory.create(version=version_pop, reference="pmid:other")

    resp = await async_client.get(
        f"/api/v2/references/pmid:99?workspace_id={workspace_a.id}", headers=owner_auth_header
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reference"] == "pmid:99"
    assert body["total_records"] == 3
    # Groups ordered by schema name: outcomes, population.
    assert [g["schema_name"] for g in body["groups"]] == ["outcomes", "population"]
    assert {g["schema_id"] for g in body["groups"]} == {str(schema_out.id), str(schema_pop.id)}
    by_name = {g["schema_name"]: g for g in body["groups"]}
    assert {r["id"] for r in by_name["population"]["records"]} == {str(r1.id), str(r2.id)}
    assert [r["id"] for r in by_name["outcomes"]["records"]] == [str(r3.id)]


async def test_reference_view_supports_slash_containing_references(async_client, owner_auth_header):
    # DOIs contain slashes; the route must use the `:path` converter to match them.
    workspace = await WorkspaceFactory.create()
    _, version = await _schema_with_version(workspace, "population")
    record = await V2RecordFactory.create(version=version, reference="10.1000/j.foo.2020.01")

    resp = await async_client.get(
        f"/api/v2/references/10.1000/j.foo.2020.01?workspace_id={workspace.id}", headers=owner_auth_header
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reference"] == "10.1000/j.foo.2020.01"
    assert body["total_records"] == 1
    assert body["groups"][0]["records"][0]["id"] == str(record.id)


async def test_reference_view_unknown_reference_returns_empty(async_client, owner_auth_header):
    workspace = await WorkspaceFactory.create()
    resp = await async_client.get(
        f"/api/v2/references/pmid:nope?workspace_id={workspace.id}", headers=owner_auth_header
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"reference": "pmid:nope", "groups": [], "total_records": 0}


async def test_reference_view_requires_workspace_id(async_client, owner_auth_header):
    resp = await async_client.get("/api/v2/references/pmid:99", headers=owner_auth_header)
    assert resp.status_code == 422


async def test_reference_view_authz(async_client, annotator_auth_header, annotator):
    workspace = await WorkspaceFactory.create()
    _, version = await _schema_with_version(workspace, "population")
    await V2RecordFactory.create(version=version, reference="pmid:99")

    # Non-member: forbidden.
    resp = await async_client.get(
        f"/api/v2/references/pmid:99?workspace_id={workspace.id}", headers=annotator_auth_header
    )
    assert resp.status_code == 403, resp.text

    # Member annotator: allowed to read.
    await WorkspaceUserFactory.create(workspace_id=workspace.id, user_id=annotator.id)
    resp = await async_client.get(
        f"/api/v2/references/pmid:99?workspace_id={workspace.id}", headers=annotator_auth_header
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_records"] == 1
