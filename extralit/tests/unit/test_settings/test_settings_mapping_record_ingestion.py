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

from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

import extralit as ex


@pytest.fixture
def dataset():
    mock_mapping = {
        "true_label": "label.response",
        "my_label": "label.suggestion.value",
        "score": "label.suggestion.score",
        "model": "label.suggestion.agent",
        "my_prompt": ("prompt_field", "prompt_question"),
    }
    settings = ex.Settings(
        fields=[ex.TextField(name="prompt_field")],
        questions=[
            ex.LabelQuestion(name="label", labels=["negative", "positive"]),
            ex.TextQuestion(name="prompt_question"),
        ],
        metadata=[ex.FloatMetadataProperty(name="score")],
        vectors=[ex.VectorField(name="vector", dimensions=3)],
        mapping=mock_mapping,
    )
    workspace = ex.Workspace(name="workspace", id=uuid4())
    dataset = ex.Dataset(
        name="test_dataset",
        settings=settings,
        workspace=workspace,
    )
    return dataset


@pytest.mark.skip(reason="Mapping ingestion implementation deprecated")
def test_settings_with_record_mapping(dataset):
    mock_user_id = uuid4()
    record_api_models = dataset.records._ingest_records(
        records=[
            {
                "my_prompt": "What is the capital of France?",
                "my_label": "positive",
                "true_label": "positive",
                "score": 0.9,
                "model": "model_name",
            }
        ],
        user_id=mock_user_id,
    )
    record = record_api_models[0]
    assert record.fields["prompt_field"] == "What is the capital of France?"
    assert record.suggestions[0].value == "positive"
    assert record.suggestions[0].question_name == "label"
    assert record.suggestions[0].score == 0.9
    assert record.suggestions[0].agent == "model_name"
    assert record.responses[0].values["label"]["value"] == "positive"
    assert record.responses[0].user_id == mock_user_id

    record = record_api_models[0]
    suggestions = [s.value for s in record.suggestions]
    assert record.fields["prompt_field"] == "What is the capital of France?"
    assert "positive" in suggestions
    assert "What is the capital of France?" in suggestions


def test_settings_with_record_mapping_export(dataset):
    with TemporaryDirectory() as temp_dir:
        path = f"{temp_dir}/test_dataset.json"
        dataset.settings.to_json(path)
        loaded_settings = ex.Settings.from_json(path)

    assert dataset.settings.mapping == loaded_settings.mapping
    assert dataset.settings == loaded_settings
