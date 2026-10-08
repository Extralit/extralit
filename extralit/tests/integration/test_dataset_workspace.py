import pytest

import extralit as ex
from extralit._exceptions import NotFoundError


@pytest.fixture
def dataset(client: ex.Extralit, dataset_name: str):
    ws = client.workspaces[0]
    dataset = ex.Dataset(
        name=dataset_name,
        settings=ex.Settings(
            fields=[
                ex.TextField(name="text"),
            ],
            questions=[
                ex.TextQuestion(name="response"),
            ],
        ),
        workspace=ws,
        client=client,
    )
    dataset.create()
    yield dataset
    dataset.delete()


def test_dataset_with_workspace(client: ex.Extralit, dataset_name: str):
    ws = client.workspaces[0]
    dataset = ex.Dataset(
        name=dataset_name,
        settings=ex.Settings(
            fields=[
                ex.TextField(name="text"),
            ],
            questions=[
                ex.TextQuestion(name="response"),
            ],
        ),
        workspace=ws,
        client=client,
    )
    dataset.create()
    assert isinstance(dataset, ex.Dataset)
    assert client.api.datasets.exists(dataset.id)
    assert dataset.workspace == ws


def test_dataset_with_workspace_name(client: ex.Extralit, dataset_name: str):
    ws = client.workspaces[0]
    dataset = ex.Dataset(
        name=dataset_name,
        settings=ex.Settings(
            fields=[
                ex.TextField(name="text"),
            ],
            questions=[
                ex.TextQuestion(name="response"),
            ],
        ),
        workspace=ws.name,
        client=client,
    )
    dataset.create()
    assert isinstance(dataset, ex.Dataset)
    assert dataset.id is not None
    assert client.api.datasets.exists(dataset.id)
    assert dataset.workspace == ws


def test_dataset_with_incorrect_workspace_name(client: ex.Extralit, dataset_name: str):
    with pytest.raises(expected_exception=NotFoundError):
        ex.Dataset(
            name=dataset_name,
            settings=ex.Settings(
                fields=[
                    ex.TextField(name="text"),
                ],
                questions=[
                    ex.TextQuestion(name="response"),
                ],
            ),
            workspace="non_existing_workspace",
            client=client,
        ).create()


def test_dataset_with_default_workspace(client: ex.Extralit, dataset_name: str):
    dataset = ex.Dataset(
        name=dataset_name,
        settings=ex.Settings(
            fields=[
                ex.TextField(name="text"),
            ],
            questions=[
                ex.TextQuestion(name="response"),
            ],
        ),
        client=client,
    )
    dataset.create()
    assert isinstance(dataset, ex.Dataset)
    assert client.api.datasets.exists(dataset.id)
    assert dataset.workspace == client.workspaces[0]


def test_retrieving_dataset(client: ex.Extralit, dataset: ex.Dataset):
    ws = client.workspaces[0]
    dataset = client.datasets(dataset.name, workspace=ws)
    assert isinstance(dataset, ex.Dataset)
    assert client.api.datasets.exists(dataset.id)


def test_retrieving_dataset_on_name(client: ex.Extralit, dataset: ex.Dataset):
    ws = client.workspaces[0]
    dataset = client.datasets(dataset.name, workspace=ws.name)
    assert isinstance(dataset, ex.Dataset)
    assert client.api.datasets.exists(dataset.id)


def test_retrieving_dataset_on_default(client: ex.Extralit, dataset: ex.Dataset):
    dataset = client.datasets(dataset.name)
    assert isinstance(dataset, ex.Dataset)
    assert client.api.datasets.exists(dataset.id)
