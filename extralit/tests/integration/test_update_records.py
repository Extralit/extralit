import uuid

import pytest

import extralit as ex


@pytest.fixture
def dataset(client: ex.Extralit, dataset_name: str) -> ex.Dataset:
    workspace = client.workspaces[0]
    settings = ex.Settings(
        allow_extra_metadata=True,
        fields=[
            ex.TextField(name="text"),
        ],
        questions=[
            ex.TextQuestion(name="label", use_markdown=False),
        ],
    )
    dataset = ex.Dataset(
        name=dataset_name,
        workspace=workspace.name,
        settings=settings,
        client=client,
    )
    dataset.create()
    return dataset


class TestUpdateRecords:
    def test_update_records_fields(self, client: ex.Extralit, dataset: ex.Dataset):
        mock_data = [
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
        ]

        dataset.records.log(records=mock_data)

        updated_mock_data = [{"text": "New text", "id": r["id"]} for r in mock_data]

        dataset.records.log(records=updated_mock_data)

        for record in dataset.records():
            assert record.fields["text"] == "New text"


class TestUpdateSuggestions:
    def test_update_records_suggestions_from_data(self, client: ex.Extralit, dataset: ex.Dataset):
        mock_data = [
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
        ]
        updated_mock_data = [
            {
                "text": r["text"],
                "label": "positive",
                "id": r["id"],
            }
            for r in mock_data
        ]

        dataset.records.log(records=mock_data)
        dataset.records.log(records=updated_mock_data)
        dataset_records = list(dataset.records)

        assert dataset_records[0].id == str(mock_data[0]["id"])
        assert dataset_records[1].id == str(mock_data[1]["id"])
        assert dataset_records[2].id == str(mock_data[2]["id"])
        for record in dataset.records(with_suggestions=True):
            assert record.suggestions["label"].value == "positive"

    @pytest.mark.skip(reason="This test is failing because the backend expects the fields to be present in the data.")
    def test_update_records_without_fields(self, client: ex.Extralit, dataset: ex.Dataset):
        mock_data = [
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
        ]

        updated_mock_data = mock_data.copy()
        for record in updated_mock_data:
            record.pop("text")
            record["label"] = "positive"
        dataset.records.log(records=mock_data)
        dataset.records.log(records=updated_mock_data)

        for i, record in enumerate(dataset.records(with_suggestions=True)):
            assert record.suggestions["label"].value == updated_mock_data[i]["label"]

    def test_update_records_add_suggestions(self, client: ex.Extralit, dataset: ex.Dataset):
        mock_data = [
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
        ]
        dataset.records.log(records=mock_data)

        updated_records = []

        for record in dataset.records(with_suggestions=True):
            record.suggestions.add(
                ex.Suggestion(
                    question_name="label",
                    value="positive",
                )
            )
            updated_records.append(record)

        dataset.records.log(records=updated_records)

        for record in dataset.records(with_suggestions=True):
            assert record.suggestions["label"].value == "positive"


class TestUpdateResponses:
    def test_update_records_add_responses(self, client: ex.Extralit, dataset: ex.Dataset):
        mock_data = [
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
            {
                "text": "Hello World, how are you?",
                "label": "negative",
                "id": uuid.uuid4(),
            },
        ]
        dataset.records.log(records=mock_data)

        updated_records = []

        for record in dataset.records(with_suggestions=True):
            record.responses.add(
                ex.Response(
                    question_name="label",
                    value="positive",
                    user_id=client.users[0].id,
                )
            )
            updated_records.append(record)

        dataset.records.log(records=updated_records)

        for record in dataset.records(with_suggestions=True):
            assert record.responses["label"][-1].value == "positive"
