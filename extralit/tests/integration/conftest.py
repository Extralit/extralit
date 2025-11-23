# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
import pytest
import os
import extralit as ex
from extralit import Extralit, Workspace
from unittest.mock import patch


@pytest.fixture(autouse=True, scope="session")
def disable_api_validation():
    with patch("extralit._api._client.APIClient._validate_connection"):
        yield


@pytest.fixture(scope="session")
def client() -> ex.Extralit:
    client = ex.Extralit(
        api_url="http://localhost:9999",
        api_key="fake",
    )
    return client


def _cleanup(client: ex.Extralit):
    for dataset in client.datasets:
        if dataset.name.startswith("test-"):
            dataset.delete()

    for workspace in client.workspaces:
        if workspace.name.startswith("test-"):
            for dataset in workspace.datasets:
                dataset.delete()
            workspace.delete()

    for user in client.users:
        if user.username.startswith("test-"):
            user.delete()


@pytest.fixture()
def dataset_name() -> str:
    return f"test_dataset_{uuid.uuid4()}"


@pytest.fixture()
def username() -> str:
    return f"test_username_{uuid.uuid4()}"


@pytest.fixture
def workspace(client: Extralit) -> Workspace:
    ws_name = f"test-{uuid.uuid4()}"
    workspace = client.workspaces(ws_name)
    if workspace is None:
        workspace = Workspace(name=ws_name).create()

    yield workspace

    for dataset in workspace.list_datasets():
        dataset.delete()
    workspace.delete()