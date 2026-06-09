import uuid

import pytest

import extralit as ex
from extralit import Extralit, Workspace


@pytest.fixture(scope="session")
def client() -> ex.Extralit:
    client = ex.Extralit()

    if len(list(client.workspaces)) == 0:
        client.workspaces.add(ex.Workspace(name=f"test-{uuid.uuid4()}"))

    yield client

    _cleanup(client)


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
    """use this fixture to autogenerate a safe dataset name for tests"""
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
