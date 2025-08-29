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
import copy
import uuid
from typing import Any

import pytest
from pytest_mock import MockerFixture

import extralit as ex
from extralit import Dataset
from extralit._exceptions import SettingsError
from extralit._models import DatasetModel
from extralit.settings._task_distribution import TaskDistribution


class TestSettings:
    def test_init_settings(self):
        settings = ex.Settings()
        assert len(settings.fields) == 0
        assert len(settings.questions) == 0

    def test_with_guidelines(self):
        mock_guidelines = "This is a guideline"
        settings = ex.Settings(
            guidelines=mock_guidelines,
        )
        assert settings.guidelines == mock_guidelines

    def test_with_guidelines_attribute(self):
        mock_guidelines = "This is a guideline"
        settings = ex.Settings()
        settings.guidelines = mock_guidelines
        assert settings.guidelines == mock_guidelines

    def test_with_text_field(self):
        mock_name = "prompt"
        mock_use_markdown = True
        settings = ex.Settings(fields=[ex.TextField(name=mock_name, use_markdown=mock_use_markdown)])
        assert settings.fields[0].name == mock_name
        assert settings.fields[0].use_markdown == mock_use_markdown

    def test_with_text_field_attribute(self):
        settings = ex.Settings()
        mock_name = "prompt"
        mock_use_markdown = True
        settings.fields = [ex.TextField(name=mock_name, use_markdown=mock_use_markdown)]
        assert settings.fields[0].name == mock_name
        assert settings.fields[0].use_markdown == mock_use_markdown

    def test_with_label_question(self):
        settings = ex.Settings(questions=[ex.LabelQuestion(name="sentiment", labels=["positive", "negative"])])
        assert settings.questions[0].name == "sentiment"
        assert settings.questions[0].labels == ["positive", "negative"]

    def test_with_label_question_attribute(self):
        settings = ex.Settings()
        settings.questions = [ex.LabelQuestion(name="sentiment", labels=["positive", "negative"])]
        assert settings.questions[0].name == "sentiment"
        assert settings.questions[0].labels == ["positive", "negative"]

    def test_settings_repr(self):
        settings = ex.Settings(
            fields=[
                ex.TextField(name="text", title="text"),
                ex.ImageField(name="image", title="image"),
            ],
            metadata=[
                ex.FloatMetadataProperty("source"),
            ],
            questions=[
                ex.LabelQuestion(name="label", title="text", labels=["positive", "negative"]),
                ex.RatingQuestion(name="rating", title="text", values=[1, 2, 3, 4, 5]),
                ex.TextQuestion(name="text", title="text"),
                ex.SpanQuestion(
                    name="span",
                    title="text",
                    field="text",
                    labels=["Apparatus", "Method", "Machine", "Manufacture", "Design"],
                    visible_labels=3,
                ),
            ],
            vectors=[ex.VectorField(name="text", dimensions=3)],
        )
        assert (
            settings.__repr__() == f"Settings(guidelines=None, allow_extra_metadata=False, "
            "distribution=OverlapTaskDistribution(min_submitted=1), "
            f"fields={settings.fields}, questions={settings.questions}, vectors={settings.vectors}, metadata={settings.metadata})"
        )

    def test_settings_validation_with_duplicated_names(self):
        settings = ex.Settings(
            fields=[ex.TextField(name="text", title="text")],
            metadata=[ex.FloatMetadataProperty("source")],
            questions=[ex.LabelQuestion(name="label", title="text", labels=["positive", "negative"])],
            vectors=[ex.VectorField(name="text", dimensions=3)],
        )

        with pytest.raises(SettingsError, match="names of dataset settings must be unique"):
            settings.validate()

    def test_copy_settings(self):
        settings = ex.Settings(
            fields=[ex.TextField(name="text", title="text")],
            metadata=[ex.FloatMetadataProperty("source")],
            questions=[ex.LabelQuestion(name="label", title="text", labels=["positive", "negative"])],
            vectors=[ex.VectorField(name="text", dimensions=3)],
        )

        settings_copy = copy.copy(settings)
        assert settings == settings_copy

        settings.fields["text"].title = "New title"
        assert settings == settings_copy

    def test_custom_copy_settings(self):
        settings = ex.Settings(
            fields=[ex.TextField(name="text", title="text")],
            metadata=[ex.FloatMetadataProperty("source")],
            questions=[ex.LabelQuestion(name="label", title="text", labels=["positive", "negative"])],
            vectors=[ex.VectorField(name="text", dimensions=3)],
        )

        settings_copy = settings._copy()
        assert settings == settings_copy

        settings.fields["text"].title = "New title"
        assert settings != settings_copy

    def test_settings_access(self):
        fields = [ex.TextField(name="text"), ex.TextField(name="other-text")]
        for field in fields:
            field._model.id = uuid.uuid4()

        settings = ex.Settings(fields=fields)

        assert settings.fields[0] == settings.fields["text"]
        assert settings.fields[1] == settings.fields["other-text"]
        assert settings.fields[fields[0].id] == fields[0]
        assert settings.fields[fields[1].id] == fields[1]

    def test_settings_access_by_none_id(self):
        settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])
        assert settings.fields[None] is None

    def test_settings_access_by_missing(self):
        field = ex.TextField(name="text", title="title")
        field._model.id = uuid.uuid4()

        settings = ex.Settings(fields=[field])
        assert settings.fields[uuid.uuid4()] is None
        assert settings.fields["missing"] is None

    def test_settings_access_by_out_of_range(self):
        settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])
        with pytest.raises(IndexError):
            _ = settings.fields[10]

    def test_settings_with_modified_default_task_distribution(self):
        settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])

        assert settings.distribution == TaskDistribution(min_submitted=1)
        settings.distribution.min_submitted = 10

        other_settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])
        assert other_settings.distribution == TaskDistribution(min_submitted=1)

    def test_settings_with_modified_task_distribution_value(self):
        settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])

        assert settings.distribution == TaskDistribution(min_submitted=1)
        settings.distribution.min_submitted = 10

        assert settings.distribution == TaskDistribution(min_submitted=10)

    def test_compare_equal_settings(self):
        settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])
        assert settings == settings

    @pytest.mark.parametrize("other_settings", [None, "value", 100, ex.Settings()])
    def test_compare_different_settings(self, other_settings: Any):
        settings = ex.Settings(fields=[ex.TextField(name="text", title="title")])
        assert settings != other_settings

    def test_read_settings_without_distribution(self, mocker: "MockerFixture"):
        settings = ex.Settings(
            fields=[ex.TextField(name="text", title="title")],
            _dataset=Dataset(name="dataset"),
        )

        mocker.patch.object(settings, "_fetch_fields", return_value=list(settings.fields))
        mocker.patch.object(settings, "_fetch_questions", return_value=[])
        mocker.patch.object(settings, "_fetch_vectors", return_value=[])
        mocker.patch.object(settings, "_fetch_metadata", return_value=[])

        mocker.patch.object(
            settings._client.api.datasets,
            "get",
            return_value=DatasetModel(name=settings.dataset.name, distribution=None),
        )

        settings.get()
        assert settings.distribution == TaskDistribution.default()

    def test_serialize(self):
        settings = ex.Settings(
            guidelines="This is a guideline",
            fields=[ex.TextField(name="prompt", use_markdown=True)],
            questions=[ex.LabelQuestion(name="sentiment", labels=["positive", "negative"])],
        )
        settings_serialized = settings.serialize()
        assert settings_serialized["guidelines"] == "This is a guideline"
        assert settings_serialized["fields"][0]["name"] == "prompt"
        assert settings_serialized["fields"][0]["settings"]["use_markdown"] is True

    def test_remove_property_from_settings(self):
        settings = ex.Settings(
            fields=[ex.TextField(name="text", title="text")],
            questions=[ex.LabelQuestion(name="label", title="text", labels=["positive", "negative"])],
            metadata=[ex.FloatMetadataProperty("source")],
            vectors=[ex.VectorField(name="vector", dimensions=3)],
        )

        settings.fields.remove("text")
        assert len(settings.fields) == 0

        settings.questions.remove("label")
        assert len(settings.questions) == 0

        settings.metadata.remove("source")
        assert len(settings.metadata) == 0

        settings.vectors.remove("vector")
        assert len(settings.vectors) == 0

    def test_adding_properties_with_override_enabled(self):
        settings = ex.Settings()

        settings.add(ex.TextField(name="text", title="text"))
        assert len(settings.fields) == 1

        settings.add(ex.TextQuestion(name="question", title="question"))
        assert len(settings.questions) == 1

        settings.add(ex.FloatMetadataProperty(name="text"), override=True)
        assert len(settings.metadata) == 1
        assert len(settings.fields) == 0

    def test_adding_properties_with_disabled_override(self):
        settings = ex.Settings()

        settings.add(ex.TextField(name="text", title="text"))
        assert len(settings.fields) == 1

        settings.add(ex.TextQuestion(name="question", title="question"))
        assert len(settings.questions) == 1

        with pytest.raises(SettingsError, match="Property with name 'text' already exists"):
            settings.add(ex.FloatMetadataProperty(name="text"), override=False)
