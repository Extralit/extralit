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


import pytest

import extralit as ex


@pytest.fixture
def dataset(client: ex.Extralit, dataset_name: str):
    ws = client.workspaces.default
    settings = ex.Settings(
        guidelines="The dataset guidelines",
        fields=[ex.TextField(name="text", required=True, title="Text")],
        questions=[
            ex.LabelQuestion(name="label", title="Label", labels=["positive", "negative"]),
            ex.RankingQuestion(name="ranking", title="Ranking", values=["1", "2", "3"]),
        ],
    )

    ds = ex.Dataset(
        name=dataset_name,
        settings=settings,
        client=client,
        workspace=ws,
    )
    ds.create()
    yield ds
    ds.delete()


def test_ranking_question_with_suggestions(dataset: ex.Dataset):
    dataset.records.log(
        [
            {"text": "This is a test text", "label": "positive", "ranking": ["2", "1", "3"]},
        ],
    )
    assert next(iter(dataset.records(with_suggestions=True))).suggestions["ranking"].value == ["2", "1", "3"]


def test_ranking_question_with_responses(dataset: ex.Dataset):
    dataset.records.log(
        [
            {"text": "This is a test text", "label": "positive", "ranking_": ["2"]},
        ],
        mapping={"ranking_": "ranking.response"},
    )
    assert next(iter(dataset.records(with_responses=True))).responses["ranking"][0].value == ["2"]
