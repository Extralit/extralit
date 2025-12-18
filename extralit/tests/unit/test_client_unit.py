# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
import pytest
from unittest.mock import MagicMock

from extralit import Dataset, Extralit, Settings, TextField, TextQuestion, User, Workspace
from extralit._exceptions import ExtralitError
from .client_mocks import MockClient

@pytest.fixture
def client() -> MockClient:
    return MockClient()

@pytest.fixture
def workspace(client: MockClient) -> Workspace:
    ws_id = uuid.uuid4()
    ws = Workspace(name=f"test-workspace{ws_id}", id=ws_id, client=client)
    client.add_workspace(ws)
    return ws

@pytest.fixture
def user(client: MockClient) -> User:
    user_id = uuid.uuid4()
    from extralit._models import UserModel
    user_model = UserModel(id=user_id, username="test_user", first_name="Test", role="admin", api_key="test_key")
    user = User(client=client, _model=user_model)
    client.add_user(user)
    return user

@pytest.fixture
def dataset(client: MockClient, workspace: Workspace) -> Dataset:
    dataset_id = uuid.uuid4()
    ds = Dataset(client=client, name=f"test_dataset{dataset_id}")
    ds._model.id = dataset_id
    # Ensure the dataset belongs to the mock workspace we created
    ds._model.workspace_id = workspace.id

    client.add_dataset(ds)
    return ds

class TestClientUnit:
    def test_get_resources(self, client: MockClient, workspace: Workspace, user: User, dataset: Dataset):
        assert client.workspaces(name=workspace.name) == workspace
        assert client.workspaces(id=workspace.id) == workspace
        assert client.workspaces(id=str(workspace.id)) == workspace
        assert client.workspaces(id=str(workspace.id), name="skip this name") == workspace

        assert client.users(username=user.username) == user
        assert client.users(id=user.id) == user
        assert client.users(id=str(user.id)) == user
        assert client.users(id=str(user.id), username="skip this username") == user

        assert client.datasets(name=dataset.name) == dataset
        assert client.datasets(id=dataset.id) == dataset
        assert client.datasets(id=str(dataset.id)) == dataset
        assert client.datasets(id=str(dataset.id), name="skip this name") == dataset

    def test_get_resources_warnings(self, client: MockClient):
        client.api.workspaces.list.return_value = []
        client.api.users.list.return_value = []
        client.api.datasets.list.return_value = []

        from extralit._exceptions import NotFoundError
        client.api.workspaces.get.side_effect = NotFoundError()
        client.api.users.get.side_effect = NotFoundError()
        client.api.datasets.get.side_effect = NotFoundError()


        with pytest.warns(UserWarning, match="Workspace with id"):
            assert client.workspaces(id=uuid.uuid4()) is None

        with pytest.warns(UserWarning, match="User with id"):
            assert client.users(id=uuid.uuid4()) is None

        with pytest.warns(UserWarning, match="Dataset with id"):
            assert client.datasets(id=uuid.uuid4()) is None

        with pytest.warns(UserWarning, match="Workspace with name"):
            assert client.workspaces(name="missing") is None

        with pytest.warns(UserWarning, match="User with username"):
            assert client.users(username="missing") is None

        ws = Workspace(name="default", id=uuid.uuid4(), client=client)
        client.add_workspace(ws)

        with pytest.warns(UserWarning, match="Dataset with name"):
             assert client.datasets(name="missing") is None


    def test_get_resource_with_missing_args(self, client: MockClient):
        with pytest.raises(ExtralitError):
            client.workspaces()

        with pytest.raises(ExtralitError):
            client.datasets()

        with pytest.raises(ExtralitError):
            client.users()

    def test_init_with_missing_api_url(self):
        with pytest.raises(ExtralitError):
            Extralit(api_url=None)

        with pytest.raises(ExtralitError):
            Extralit(api_url="")

    def test_init_with_missing_api_key(self):
        with pytest.raises(ExtralitError):
            Extralit(api_key=None)

        with pytest.raises(ExtralitError):
            Extralit(api_key="")
