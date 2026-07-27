from unittest.mock import patch

import pandera.pandas as pa
import pytest

from extralit_server.api.schemas.v1.files import ObjectMetadata
from extralit_server.enums import DatasetStatus
from tests.factories import AnnotatorFactory, DatasetFactory, WorkspaceFactory


def _body() -> str:
    return pa.DataFrameSchema({"population": pa.Column(str, nullable=True)}).to_json()


@pytest.fixture(autouse=True)
def _mock_put_object():
    # `publish_version` (Task 6) calls the real `files_ctx.put_object`, which would
    # otherwise hit real object storage (or the LocalFileClient fallback under
    # ~/.extralit) through the `files_ctx.get_s3_client` dependency. Stub at the
    # `put_object` call site rather than the dependency itself, matching the existing
    # convention in tests/unit/api/handlers/v1/test_files.py (`test_put_file` patches
    # `extralit_server.contexts.files.put_object`). This keeps the stub local to this
    # test module instead of adding a suite-wide override to tests/unit/conftest.py.
    with patch("extralit_server.contexts.schema_versions.files_ctx.put_object") as mock_put_object:
        mock_put_object.return_value = ObjectMetadata(
            bucket_name="workspace",
            object_name="schemas/dataset/v1.json",
            etag="etag",
            version_id="v1",
        )
        yield mock_put_object


@pytest.mark.asyncio
class TestPublishSchemaVersion:
    async def test_owner_publishes_a_version(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 201, response.json()
        assert response.json()["version"] == 1
        assert response.json()["dataset_id"] == str(dataset.id)

    async def test_publish_returns_422_for_an_invalid_body(self, async_client, owner_auth_header):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": "{not pandera}"},
        )
        assert response.status_code == 422

    async def test_publish_returns_404_for_an_unknown_dataset(self, async_client, owner_auth_header):
        response = await async_client.post(
            "/api/v1/datasets/00000000-0000-0000-0000-000000000000/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 404

    async def test_annotator_cannot_publish(self, async_client, mock_search_engine):
        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(workspace=workspace, status=DatasetStatus.draft)
        annotator = await AnnotatorFactory.create(workspaces=[workspace])
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers={"X-Extralit-Api-Key": annotator.api_key},
            json={"body": _body()},
        )
        assert response.status_code == 403

    async def test_published_columns_are_readable_as_dataset_fields(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        # The former GET /schemas/{id}/columns is now the existing v1 fields endpoint.
        fields = await async_client.get(f"/api/v1/datasets/{dataset.id}/fields", headers=owner_auth_header)
        assert fields.status_code == 200
        assert [f["name"] for f in fields.json()["items"]] == ["population"]
        # NOT "str" — see Task 6 Step 1; pandera emits "string"/"string[pyarrow]"/"object".
        assert fields.json()["items"][0]["settings"]["dtype"] in {"string", "string[pyarrow]", "object"}


@pytest.mark.asyncio
class TestReadSchemaVersions:
    async def test_list_versions(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        for _ in range(2):
            await async_client.post(
                f"/api/v1/datasets/{dataset.id}/schema-versions",
                headers=owner_auth_header,
                json={"body": _body()},
            )
        response = await async_client.get(f"/api/v1/datasets/{dataset.id}/schema-versions", headers=owner_auth_header)
        assert response.status_code == 200
        assert [v["version"] for v in response.json()] == [1, 2]

    async def test_list_versions_is_empty_for_an_unpublished_dataset(self, async_client, owner_auth_header):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.get(f"/api/v1/datasets/{dataset.id}/schema-versions", headers=owner_auth_header)
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_version_by_number(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        response = await async_client.get(f"/api/v1/datasets/{dataset.id}/schema-versions/1", headers=owner_auth_header)
        assert response.status_code == 200
        assert response.json()["version"] == 1

    async def test_get_unknown_version_returns_404(self, async_client, owner_auth_header):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.get(
            f"/api/v1/datasets/{dataset.id}/schema-versions/99", headers=owner_auth_header
        )
        assert response.status_code == 404

    async def test_annotator_in_the_workspace_can_read_versions(self, async_client):
        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(workspace=workspace)
        annotator = await AnnotatorFactory.create(workspaces=[workspace])
        response = await async_client.get(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers={"X-Extralit-Api-Key": annotator.api_key},
        )
        assert response.status_code == 200
