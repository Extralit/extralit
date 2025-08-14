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

import os
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from datasets import ClassLabel, Features, Value
from datasets import Dataset as HFDataset
from huggingface_hub.errors import HfHubHTTPError

import extralit as ex

_RETRIES = 5


@pytest.fixture
def dataset(client, dataset_name: str) -> Generator[ex.Dataset, None, None]:
    settings = ex.Settings(
        fields=[
            ex.TextField(name="text"),
            ex.ImageField(name="image"),
        ],
        questions=[
            ex.LabelQuestion(name="label", labels=["positive", "negative"]),
        ],
    )
    dataset = ex.Dataset(
        name=dataset_name,
        settings=settings,
        client=client,
    )
    dataset.create()
    yield dataset
    dataset.delete()


@pytest.fixture
def mock_data() -> list[dict[str, Any]]:
    return [
        {
            "text": "Hello World, how are you?",
            "image": "http://mock.url/image",
            "label": "positive",
            "id": uuid.uuid4(),
        },
        {
            "text": "Hello World, how are you?",
            "image": "http://mock.url/image",
            "label": "negative",
            "id": uuid.uuid4(),
        },
        {
            "text": "Hello World, how are you?",
            "image": "http://mock.url/image",
            "label": "positive",
            "id": uuid.uuid4(),
        },
    ]


@pytest.fixture
def token():
    return os.getenv("HF_TOKEN_EXTRALIT_INTERNAL_TESTING")


@pytest.mark.skipif(not os.getenv("HF_TOKEN_EXTRALIT_INTERNAL_TESTING"), reason="No HF token provided")
class TestImportFeaturesFromHub:
    def test_import_records_from_datasets_with_classlabel(
        self, token: str, dataset: ex.Dataset, client, mock_data: list[dict[str, Any]]
    ):
        repo_id = f"extralit-dev/test_import_dataset_from_hub_with_classlabel_{uuid.uuid4()}"

        hf_dataset = HFDataset.from_dict(
            {
                "text": [record["text"] for record in mock_data],
                "label": [record["label"] for record in mock_data],
            },
            features=Features(
                {
                    "text": Value("string"),
                    "label": ClassLabel(names=["positive", "negative"]),
                }
            ),
        )

        try:
            hf_dataset.push_to_hub(repo_id=repo_id, token=token)
        except HfHubHTTPError as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub HTTP error: {e}")

        dataset.records.log(mock_data)

        for i, record in enumerate(dataset.records(with_suggestions=True)):
            assert record.fields["text"] == mock_data[i]["text"]
            assert record.suggestions["label"].value == mock_data[i]["label"]

        exported_dataset = dataset.records.to_datasets()

        assert exported_dataset.features["label.suggestion"].names == ["positive", "negative"]
        assert exported_dataset["label.suggestion"] == [0, 1, 0]

    def test_import_from_hub_with_upper_case_columns(self, client: ex.Extralit, token: str, dataset_name: str):
        created_dataset = None
        try:
            created_dataset = ex.Dataset.from_hub(
                "extralit-dev/test_import_from_hub_with_upper_case_columns",
                token=token,
                name=dataset_name,
                settings="auto",
            )
        except HfHubHTTPError as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub HTTP error: {e}")
        except Exception as e:
            if "Repository Not Found" in str(e) or "Dataset not found" in str(e):
                pytest.skip(f"Dataset not available on Hub: {e!s}")
            else:
                raise

        if created_dataset:
            assert created_dataset.settings.fields[0].name == "Text"
            assert next(iter(created_dataset.records)).fields["Text"] == "Hello World, how are you?"

    def test_import_from_hub_with_unlabelled_classes(self, client: ex.Extralit, token: str, dataset_name: str):
        created_dataset = None
        try:
            created_dataset = ex.Dataset.from_hub(
                "extralit-dev/test_import_from_hub_with_unlabelled_classes",
                token=token,
                name=dataset_name,
                settings="auto",
            )
        except HfHubHTTPError as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub HTTP error: {e}")
        except Exception as e:
            if "Repository Not Found" in str(e) or "Dataset not found" in str(e):
                pytest.skip(f"Dataset not available on Hub: {e!s}")
            else:
                raise
        if created_dataset:
            assert created_dataset.settings.fields[0].name == "Text"
            assert next(iter(created_dataset.records)).fields["Text"] == "Hello World, how are you?"

    def test_import_with_row_id_as_record_id(self, client: ex.Extralit, token: str, dataset_name: str):
        created_dataset = None
        try:
            created_dataset = ex.Dataset.from_hub(
                "extralit-dev/test_import_from_hub_with_unlabelled_classes",
                token=token,
                name=dataset_name,
                split="train",
                settings="auto",
            )
        except HfHubHTTPError as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub HTTP error: {e}")
        except Exception as e:
            if "Repository Not Found" in str(e) or "Dataset not found" in str(e):
                pytest.skip(f"Dataset not available on Hub: {e!s}")
            else:
                raise

        if created_dataset:
            records = list(created_dataset.records)

            for idx, record in enumerate(records):
                assert record.id == f"train_{idx}"
