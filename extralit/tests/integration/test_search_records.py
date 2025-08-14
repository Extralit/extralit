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

from datetime import datetime
from random import random

import pytest

from extralit import (
    Dataset,
    Extralit,
    LabelQuestion,
    Query,
    Record,
    Settings,
    Similar,
    Suggestion,
    TextField,
    TextQuestion,
    VectorField,
    Workspace,
)


@pytest.fixture
def dataset(client: Extralit, workspace: Workspace, dataset_name: str) -> Dataset:
    settings = Settings(
        fields=[TextField(name="text")],
        vectors=[VectorField(name="vector", dimensions=10)],
        questions=[
            TextQuestion(name="comment", use_markdown=False),
            LabelQuestion(name="sentiment", labels=["positive", "negative"], required=False),
        ],
    )

    dataset = Dataset(
        name=dataset_name,
        workspace=workspace.name,
        settings=settings,
        client=client,
    )

    dataset.create()
    yield dataset
    dataset.delete()


class TestSearchRecords:
    def test_search_records_by_id(self, client: Extralit, dataset: Dataset):
        dataset.records.log(
            [
                {"text": "The record text field", "id": 1},
                {"text": "The record text field", "id": 2},
            ]
        )

        records = list(dataset.records(query=Query(filter=("id", "==", 1))))
        assert len(records) == 1
        assert records[0].id == "1"

    def test_search_records_by_server_id(self, client: Extralit, dataset: Dataset):
        dataset.records.log(
            [
                {"text": "The record text field", "id": 1},
                {"text": "The record text field", "id": 2},
            ]
        )

        records = list(dataset.records)

        server_id = records[0]._server_id

        records = list(dataset.records(query=Query(filter=("_server_id", "==", server_id))))
        assert len(records) == 1
        assert records[0]._server_id == server_id

    def test_search_records_by_inserted_at(self, client: Extralit, dataset: Dataset):
        dataset.records.log(
            [
                {"text": "The record text field", "id": 1},
                {"text": "The record text field", "id": 2},
            ]
        )

        records = list(dataset.records(query=Query(filter=("inserted_at", "<=", datetime.utcnow()))))
        assert len(records) == 2
        assert records[0].id == "1"
        assert records[1].id == "2"

    def test_search_records_by_updated_at(self, client: Extralit, dataset: Dataset):
        dataset.records.log(
            [
                {"text": "The record text field", "id": 1},
                {"text": "The record text field", "id": 2},
            ]
        )

        records = list(dataset.records(query=Query(filter=("updated_at", "<=", datetime.utcnow()))))
        assert len(records) == 2
        assert records[0].id == "1"
        assert records[1].id == "2"

    def test_search_records_by_suggestion_agent(self, client: Extralit, dataset: Dataset):
        dataset.records.log(
            [
                Record(
                    id="1",
                    fields={"text": "The record text field"},
                    suggestions=[Suggestion(question_name="sentiment", agent="agent", value="positive")],
                ),
                Record(
                    id="2",
                    fields={"text": "The record text field"},
                    suggestions=[Suggestion(question_name="sentiment", agent="other-agent", value="positive")],
                ),
                {"text": "The record text field", "id": 3},
            ]
        )

        records = list(dataset.records(query=Query(filter=("sentiment.agent", "==", "agent"))))
        assert len(records) == 1
        assert records[0].id == "1"

    def test_search_records_by_suggestion_type(self, client: Extralit, dataset: Dataset):
        dataset.records.log(
            [
                Record(
                    id="1",
                    fields={"text": "The record text field"},
                    suggestions=[Suggestion(question_name="sentiment", type="human", value="positive")],
                ),
                Record(
                    id="2",
                    fields={"text": "The record text field"},
                    suggestions=[Suggestion(question_name="sentiment", type="model", value="positive")],
                ),
                {"text": "The record text field", "id": 3},
            ]
        )

        records = list(dataset.records(query=Query(filter=("sentiment.type", "==", "human"))))
        assert len(records) == 1
        assert records[0].id == "1"

    def test_search_records_by_similar_value(self, client: Extralit, dataset: Dataset):
        data = [
            {
                "id": i,
                "text": "The record text field",
                "vector": [random() for _ in range(10)],
            }
            for i in range(1500)
        ]

        dataset.records.log(data)

        records = list(
            dataset.records(
                query=Query(
                    similar=Similar(name="vector", value=data[3]["vector"]),
                )
            )
        )
        assert len(records) == 1000
        assert records[0][0].id == str(data[3]["id"])

    def test_search_records_by_least_similar_value(self, client: Extralit, dataset: Dataset):
        data = [
            {
                "id": i,
                "text": "The record text field",
                "vector": [random() for _ in range(10)],
            }
            for i in range(10)
        ]

        dataset.records.log(data)

        records = list(
            dataset.records(
                query=Query(
                    similar=Similar(name="vector", value=data[3]["vector"], most_similar=False),
                )
            )
        )

        if records and str(data[3]["id"]) == records[0][0].id:
            pytest.skip("Random tie: least similar record is the same as the query record. Skipping flaky test.")

        assert records[0][0].id != str(data[3]["id"])

    def test_search_records_by_similar_record(self, client: Extralit, dataset: Dataset):
        data = [
            {
                "id": i,
                "text": "The record text field",
                "vector": [random() for _ in range(10)],
            }
            for i in range(1500)
        ]

        dataset.records.log(data)

        record = next(iter(dataset.records(limit=1, with_vectors=False)))

        records = list(
            dataset.records(
                query=Query(
                    similar=Similar(name="vector", value=record),
                )
            )
        )
        assert len(records) == 1000
        assert records[0][0].id != str(record.id)

    def test_search_records_by_least_similar_record(self, client: Extralit, dataset: Dataset):
        data = [
            {
                "id": i,
                "text": "The record text field",
                "vector": [random() for _ in range(10)],
            }
            for i in range(100)
        ]

        dataset.records.log(data)

        record = next(iter(dataset.records(limit=1, with_vectors=False)))

        records = list(
            dataset.records(
                query=Query(
                    similar=Similar(name="vector", value=record, most_similar=False),
                )
            )
        )
        assert all(r.id != str(record.id) for r, s in records)
