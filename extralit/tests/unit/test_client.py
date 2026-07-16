from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pytest_httpx import HTTPXMock

from extralit import Extralit
from extralit._exceptions import ExtralitError

API_URL = "http://test_url"


@pytest.fixture
def client() -> Extralit:
    return Extralit(api_url=API_URL, api_key="test-api-key")


@pytest.fixture
def resources() -> dict[str, dict]:
    timestamp = datetime.now(timezone.utc).isoformat()
    workspace_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    return {
        "workspace": {
            "id": str(workspace_id),
            "name": "test-workspace",
            "inserted_at": timestamp,
            "updated_at": timestamp,
        },
        "dataset": {
            "id": str(dataset_id),
            "name": "test-dataset",
            "status": "ready",
            "workspace_id": str(workspace_id),
            "inserted_at": timestamp,
            "updated_at": timestamp,
        },
        "user": {
            "id": str(user_id),
            "username": "test-user",
            "role": "annotator",
            "inserted_at": timestamp,
            "updated_at": timestamp,
        },
    }


def add_response(httpx_mock: HTTPXMock, path: str, json: dict, status_code: int = 200) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{API_URL}{path}",
        json=json,
        status_code=status_code,
    )


class TestClientCollections:
    def test_get_resources_by_name_and_id(
        self, client: Extralit, httpx_mock: HTTPXMock, resources: dict[str, dict]
    ) -> None:
        workspace = resources["workspace"]
        user = resources["user"]
        dataset = resources["dataset"]
        add_response(httpx_mock, "/api/v1/me/workspaces", {"items": [workspace]})
        add_response(httpx_mock, f"/api/v1/workspaces/{workspace['id']}", workspace)
        add_response(httpx_mock, "/api/v1/users", {"items": [user]})
        add_response(httpx_mock, f"/api/v1/users/{user['id']}", user)
        add_response(httpx_mock, "/api/v1/me/workspaces", {"items": [workspace]})
        add_response(httpx_mock, "/api/v1/me/datasets", {"items": [dataset]})
        add_response(httpx_mock, f"/api/v1/datasets/{dataset['id']}", dataset)
        add_response(httpx_mock, f"/api/v1/datasets/{dataset['id']}/fields", {"items": []})
        add_response(httpx_mock, f"/api/v1/datasets/{dataset['id']}/questions", {"items": []})
        add_response(httpx_mock, f"/api/v1/datasets/{dataset['id']}/vectors-settings", {"items": []})
        add_response(httpx_mock, f"/api/v1/me/datasets/{dataset['id']}/metadata-properties", {"items": []})

        assert client.workspaces(name=workspace["name"]).id == UUID(workspace["id"])
        assert client.workspaces(id=workspace["id"]).name == workspace["name"]

        assert client.users(username=user["username"]).id == UUID(user["id"])
        assert client.users(id=user["id"]).username == user["username"]

        assert client.datasets(name=dataset["name"]).id == UUID(dataset["id"])
        assert client.datasets(id=dataset["id"]).name == dataset["name"]

    def test_missing_resources_warn_and_return_none(
        self, client: Extralit, httpx_mock: HTTPXMock, resources: dict[str, dict]
    ) -> None:
        workspace = resources["workspace"]
        user = resources["user"]
        dataset = resources["dataset"]
        missing_workspace_id = uuid4()
        missing_user_id = uuid4()
        missing_dataset_id = uuid4()

        add_response(httpx_mock, f"/api/v1/workspaces/{missing_workspace_id}", {}, status_code=404)
        add_response(httpx_mock, f"/api/v1/users/{missing_user_id}", {}, status_code=404)
        add_response(httpx_mock, f"/api/v1/datasets/{missing_dataset_id}", {}, status_code=404)
        add_response(httpx_mock, "/api/v1/me/workspaces", {"items": [workspace]})
        add_response(httpx_mock, "/api/v1/users", {"items": [user]})
        add_response(httpx_mock, "/api/v1/me/workspaces", {"items": [workspace]})
        add_response(httpx_mock, "/api/v1/me/datasets", {"items": [dataset]})

        with pytest.warns(UserWarning, match="Workspace with id"):
            assert client.workspaces(id=missing_workspace_id) is None
        with pytest.warns(UserWarning, match="User with id"):
            assert client.users(id=missing_user_id) is None
        with pytest.warns(UserWarning, match="Dataset with id"):
            assert client.datasets(id=missing_dataset_id) is None

        with pytest.warns(UserWarning, match="Workspace with name"):
            assert client.workspaces(name="missing") is None
        with pytest.warns(UserWarning, match="User with username"):
            assert client.users(username="missing") is None
        with pytest.warns(UserWarning, match="Dataset with name"):
            assert client.datasets(name="missing") is None

    @pytest.mark.parametrize("collection", ["workspaces", "users", "datasets"])
    def test_collections_require_a_lookup_argument(self, client: Extralit, collection: str) -> None:
        with pytest.raises(ExtralitError):
            getattr(client, collection)()

    def test_me_uses_the_real_client_api(
        self, client: Extralit, httpx_mock: HTTPXMock, resources: dict[str, dict]
    ) -> None:
        add_response(httpx_mock, "/api/v1/me", resources["user"])

        assert client.me.id == UUID(resources["user"]["id"])
        assert client.me.username == resources["user"]["username"]


@pytest.mark.parametrize(
    "api_url, api_key", [(None, "test-api-key"), ("", "test-api-key"), (API_URL, None), (API_URL, "")]
)
def test_client_requires_api_url_and_key(api_url: str | None, api_key: str | None) -> None:
    with pytest.raises(ExtralitError):
        Extralit(api_url=api_url, api_key=api_key)
