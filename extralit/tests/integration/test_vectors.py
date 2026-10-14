import random
import uuid

import pytest

import extralit as ex


@pytest.fixture
def dataset(client: ex.Extralit, dataset_name: str) -> ex.Dataset:
    workspace = client.workspaces[0]
    settings = ex.Settings(
        fields=[ex.TextField(name="text")],
        questions=[ex.LabelQuestion(name="label", labels=["positive", "negative"])],
        vectors=[ex.VectorField(name="vector", dimensions=10)],
    )
    dataset = ex.Dataset(
        name=dataset_name,
        workspace=workspace,
        settings=settings,
        client=client,
    )
    dataset.create()
    yield dataset
    dataset.delete()


def test_vectors(client: ex.Extralit, dataset: ex.Dataset):
    mock_data = [
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
        {
            "text": "Hello World, how are you?",
            "label": "negative",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
    ]
    dataset.records.log(records=mock_data)

    dataset_records = list(dataset.records(with_responses=True, with_suggestions=True, with_vectors=["vector"]))
    assert dataset_records[0].id == str(mock_data[0]["id"])
    assert dataset_records[1].id == str(mock_data[1]["id"])
    assert dataset_records[2].id == str(mock_data[2]["id"])
    assert dataset_records[0].vectors["vector"] == mock_data[0]["vector"]
    assert dataset_records[1].vectors["vector"] == mock_data[1]["vector"]
    assert dataset_records[2].vectors["vector"] == mock_data[2]["vector"]


def test_vectors_return_with_bool(client: ex.Extralit, dataset: ex.Dataset):
    mock_data = [
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
        {
            "text": "Hello World, how are you?",
            "label": "negative",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
    ]
    dataset.records.log(records=mock_data)

    dataset_records = list(dataset.records(with_responses=True, with_suggestions=True, with_vectors=True))
    assert dataset_records[0].id == str(mock_data[0]["id"])
    assert dataset_records[1].id == str(mock_data[1]["id"])
    assert dataset_records[2].id == str(mock_data[2]["id"])
    assert dataset_records[0].vectors["vector"] == mock_data[0]["vector"]
    assert dataset_records[1].vectors["vector"] == mock_data[1]["vector"]
    assert dataset_records[2].vectors["vector"] == mock_data[2]["vector"]


def test_vectors_return_with_name(client: ex.Extralit, dataset: ex.Dataset):
    mock_data = [
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
        {
            "text": "Hello World, how are you?",
            "label": "negative",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": uuid.uuid4(),
            "vector": [random.random() for _ in range(10)],
        },
    ]
    dataset.records.log(records=mock_data)

    dataset_records = list(dataset.records(with_responses=True, with_suggestions=True, with_vectors="vector"))
    assert dataset_records[0].id == str(mock_data[0]["id"])
    assert dataset_records[1].id == str(mock_data[1]["id"])
    assert dataset_records[2].id == str(mock_data[2]["id"])
    assert dataset_records[0].vectors["vector"] == mock_data[0]["vector"]
    assert dataset_records[1].vectors["vector"] == mock_data[1]["vector"]
    assert dataset_records[2].vectors["vector"] == mock_data[2]["vector"]
