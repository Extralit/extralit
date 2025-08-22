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

import random
from string import ascii_lowercase

import pytest

import extralit as ex
from extralit import Dataset, Extralit, LabelQuestion, Settings, TextField, Workspace


@pytest.fixture
def dataset(client: Extralit, workspace: Workspace) -> Dataset:
    name = "".join(random.choices(ascii_lowercase, k=16))
    settings = Settings(
        fields=[TextField(name="text")],
        questions=[LabelQuestion(name="label", labels=["positive", "negative"])],
    )
    dataset = Dataset(
        name=name,
        workspace=workspace.name,
        settings=settings,
        client=client,
    )
    dataset.create()
    yield dataset
    dataset.delete()


def test_query_records_by_text(client: Extralit, dataset: Dataset):
    dataset.records.log(
        [
            {"text": "First record", "id": 1},
            {"text": "Second record", "id": 2},
        ]
    )

    records = list(dataset.records(query="first"))

    assert len(records) == 1
    assert records[0].id == "1"
    assert records[0].fields["text"] == "First record"

    records = list(dataset.records(query="second"))
    assert len(records) == 1
    assert records[0].id == "2"
    assert records[0].fields["text"] == "Second record"

    records = list(dataset.records(query="record"))
    assert len(records) == 2


def test_query_records_by_suggestion_value(client: Extralit, dataset: Dataset):
    data = [
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": 1,
        },
        {
            "text": "Hello World, how are you?",
            "label": "negative",
            "id": 2,
        },
        {
            "text": "Hello World, how are you?",
            "label": "positive",
            "id": 3,
        },
    ]

    dataset.records.log(data)

    query = ex.Query(filter=ex.Filter([("label", "==", "positive")]))
    records = list(dataset.records(query=query))

    assert len(records) == 2
    assert records[0].id == "1"
    assert records[1].id == "3"

    query = ex.Query(filter=ex.Filter(("label", "==", "negative")))
    records = list(dataset.records(query=query))

    assert len(records) == 1
    assert records[0].id == "2"

    query = ex.Query(filter=ex.Filter(("label", "in", ["positive", "negative"])))
    records = list(dataset.records(query=query))
    assert len(records) == 3

    test_filter = ex.Filter([("label", "==", "positive"), ("label", "==", "negative")])
    query = ex.Query(filter=test_filter)
    records = list(dataset.records(query=query))
    assert len(records) == 0
