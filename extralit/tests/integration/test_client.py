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

from extralit import Dataset, Extralit, Settings, TextField, TextQuestion, User, Workspace
from extralit._exceptions import ExtralitError


@pytest.fixture
def dataset(client: Extralit) -> Dataset:
    return Dataset(
        name=f"test_dataset{uuid.uuid4()}",
        settings=Settings(fields=[TextField(name="text")], questions=[TextQuestion(name="question")]),
        client=client,
    ).create()


@pytest.fixture
def user(client: Extralit) -> User:
    user = User(username="test_user", password="test password").create()
    user.password = None  # to align with GET user result

    return user


@pytest.fixture
def workspace(client: Extralit) -> Workspace:
    return Workspace(name=f"test_workspace{uuid.uuid4()}").create()


# TODO: We can move this test suite to tests/unit once we have a mock client implementation
class TestClient:
    def test_get_resources(self, client: Extralit, workspace: Workspace, user: User, dataset: Dataset):
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

    def test_get_resources_warnings(self, client: Extralit):
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

        with pytest.warns(UserWarning, match="Dataset with name"):
            assert client.datasets(name="missing") is None

    def test_get_resource_with_missing_args(self, client: Extralit):
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
