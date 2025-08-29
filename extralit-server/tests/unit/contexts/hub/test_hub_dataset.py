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
from datasets.exceptions import DataFilesNotFoundError

# Import Hugging Face and network-related exceptions
from huggingface_hub.errors import HfHubHTTPError
from requests.exceptions import ConnectTimeout, HTTPError, ReadTimeout, RequestException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.datasets import DatasetMapping, DatasetMappingItem
from extralit_server.contexts.hub import HubDataset
from extralit_server.enums import DatasetStatus, QuestionType
from extralit_server.models import Record
from extralit_server.search_engine import SearchEngine
from tests.factories import (
    ChatFieldFactory,
    DatasetFactory,
    ImageFieldFactory,
    IntegerMetadataPropertyFactory,
    QuestionFactory,
    TextFieldFactory,
)


@pytest.mark.asyncio
class TestHubDataset:
    async def test_hub_dataset_import_to(self, db: AsyncSession, mock_search_engine: SearchEngine):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="package_name", required=True, dataset=dataset)
        await TextFieldFactory.create(name="review", required=True, dataset=dataset)
        await TextFieldFactory.create(name="date", dataset=dataset)
        await TextFieldFactory.create(name="star", dataset=dataset)

        await IntegerMetadataPropertyFactory.create(name="version_id", dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="lhoestq/demo1",
            subset="default",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="package_name", target="package_name"),
                    DatasetMappingItem(source="review", target="review"),
                    DatasetMappingItem(source="date", target="date"),
                    DatasetMappingItem(source="star", target="star"),
                ],
                metadata=[
                    DatasetMappingItem(source="version_id", target="version_id"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.external_id == "train_0"
        assert record.fields["package_name"] == "com.mantz_it.rfanalyzer"
        assert (
            record.fields["review"]
            == "Great app! The new version now works on my Bravia Android TV which is great as it's right by my rooftop aerial cable. The scan feature would be useful...any ETA on when this will be available? Also the option to import a list of bookmarks e.g. from a simple properties file would be useful."
        )
        assert record.fields["date"] == "October 12 2016"
        assert record.fields["star"] == "4"
        assert record.metadata_ == {"version_id": 1487}

    async def test_hub_dataset_import_to_with_suggestions(self, db: AsyncSession, mock_search_engine: SearchEngine):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="package_name", required=True, dataset=dataset)
        await TextFieldFactory.create(name="review", required=True, dataset=dataset)

        question = await QuestionFactory.create(
            name="star",
            required=True,
            dataset=dataset,
            settings={
                "type": QuestionType.rating,
                "options": [
                    {"value": 1},
                    {"value": 2},
                    {"value": 3},
                    {"value": 4},
                    {"value": 5},
                ],
            },
        )

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="lhoestq/demo1",
            subset="default",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="package_name", target="package_name"),
                    DatasetMappingItem(source="review", target="review"),
                ],
                suggestions=[
                    DatasetMappingItem(source="star", target="star"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.suggestions[0].value == 4
        assert record.suggestions[0].question_id == question.id

    async def test_hub_dataset_import_to_with_class_label_suggestions(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="text", required=True, dataset=dataset)

        question = await QuestionFactory.create(
            name="label",
            settings={
                "type": QuestionType.label_selection,
                "options": [
                    {"value": "neg", "text": "Negative"},
                    {"value": "pos", "text": "Positive"},
                ],
            },
            dataset=dataset,
        )

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="stanfordnlp/imdb",
            subset="plain_text",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="text", target="text"),
                ],
                suggestions=[
                    DatasetMappingItem(source="label", target="label"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.suggestions[0].value == "neg"
        assert record.suggestions[0].question_id == question.id

    async def test_hub_dataset_import_to_with_sequence_class_label_suggestions(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="text", required=True, dataset=dataset)

        await QuestionFactory.create(
            name="labels",
            required=True,
            settings={
                "type": QuestionType.multi_label_selection,
                "options": [
                    {"value": "neutral", "text": "Neutral"},
                    {"value": "admiration", "text": "Admiration"},
                    {"value": "confusion", "text": "Confusion"},
                ],
            },
            dataset=dataset,
        )

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="google-research-datasets/go_emotions",
            subset="simplified",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="text", target="text"),
                ],
                suggestions=[
                    DatasetMappingItem(source="labels", target="labels"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.suggestions[0].value == ["neutral"]

    async def test_hub_dataset_import_to_with_class_label_fields(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="text", required=True, dataset=dataset)
        await TextFieldFactory.create(name="label", required=True, dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="stanfordnlp/imdb",
            subset="plain_text",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="text", target="text"),
                    DatasetMappingItem(source="label", target="label"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.fields["label"] == "neg"

    async def test_hub_dataset_import_to_with_class_label_suggestions_using_no_label(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="text", required=True, dataset=dataset)

        await QuestionFactory.create(
            name="label",
            settings={
                "type": QuestionType.label_selection,
                "options": [
                    {"value": "neg", "text": "Negative"},
                    {"value": "pos", "text": "Positive"},
                ],
            },
            dataset=dataset,
        )

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="stanfordnlp/imdb",
            subset="plain_text",
            split="unsupervised",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="text", target="text"),
                ],
                suggestions=[
                    DatasetMappingItem(source="label", target="label"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.suggestions == []

    async def test_hub_dataset_import_to_with_class_label_fields_using_no_label(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="text", required=True, dataset=dataset)
        await TextFieldFactory.create(name="label", dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="stanfordnlp/imdb",
            subset="plain_text",
            split="unsupervised",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="text", target="text"),
                    DatasetMappingItem(source="label", target="label"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert "label" not in record.fields

    async def test_hub_dataset_import_to_with_chat_fields(self, db: AsyncSession, mock_search_engine: SearchEngine):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await ChatFieldFactory.create(name="messages", required=True, dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="mlabonne/ultrachat_200k_sft",
            subset="default",
            split="train_sft",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="messages", target="messages"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.fields["messages"]

    async def test_hub_dataset_import_to_with_image_fields(self, db: AsyncSession, mock_search_engine: SearchEngine):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await ImageFieldFactory.create(name="image-to-review", required=True, dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="lmms-lab/llava-critic-113k",
            subset="pairwise",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="image", target="image-to-review"),
                ],
            ),
        )

        try:
            await hub_dataset.take(1).import_to(db, mock_search_engine, dataset)
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        record = (await db.execute(select(Record))).scalar_one()
        assert record.external_id == "train_0"
        assert (
            record.fields["image-to-review"][:100]
            == "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aH"
        )

    @pytest.mark.skip(
        reason="Dataset 'extralit-dev/argilla-invalid-rows' doesn't exist on the Hub or cannot be accessed"
    )
    async def test_hub_dataset_import_to_with_invalid_rows(self, db: AsyncSession, mock_search_engine: SearchEngine):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="letter", required=True, dataset=dataset)
        await TextFieldFactory.create(name="count", dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="extralit-dev/argilla-invalid-rows",
            subset="default",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="letter", target="letter"),
                    DatasetMappingItem(source="count", target="count"),
                ],
            ),
        )

        await hub_dataset.import_to(db, mock_search_engine, dataset)
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 4

        records = (await db.execute(select(Record))).scalars().all()
        assert records[0].external_id == "1.0"
        assert records[0].fields == {"letter": "A", "count": "100.0"}
        assert records[1].external_id == "2.0"
        assert records[1].fields == {"letter": "B", "count": "200.0"}
        assert records[2].external_id == "4.0"
        assert records[2].fields == {"letter": "D"}
        assert records[3].external_id == "5.0"
        assert records[3].fields == {"letter": "E", "count": "500.0"}

    async def test_hub_dataset_import_to_idempotency_with_external_id(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="package_name", required=True, dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="lhoestq/demo1",
            subset="default",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="package_name", target="package_name"),
                ],
            ),
        )

        try:
            await hub_dataset.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 5

            await hub_dataset.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 5
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        records = (await db.execute(select(Record).order_by(Record.inserted_at.asc()))).scalars().all()
        assert [record.external_id for record in records] == [
            "train_0",
            "train_1",
            "train_2",
            "train_3",
            "train_4",
        ]

    async def test_hub_dataset_import_to_idempotency_without_external_id(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="package_name", required=True, dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset = HubDataset(
            name="lhoestq/demo1",
            subset="default",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="package_name", target="package_name"),
                ],
            ),
        )

        try:
            await hub_dataset.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 5

            await hub_dataset.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 5
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        records = (await db.execute(select(Record).order_by(Record.inserted_at.asc()))).scalars().all()
        assert [record.external_id for record in records] == ["train_0", "train_1", "train_2", "train_3", "train_4"]

    async def test_hub_dataset_import_to_idempotency_without_external_id_and_multiple_splits(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)

        await TextFieldFactory.create(name="package_name", required=True, dataset=dataset)

        await dataset.awaitable_attrs.fields
        await dataset.awaitable_attrs.questions
        await dataset.awaitable_attrs.metadata_properties

        hub_dataset_train = HubDataset(
            name="lhoestq/demo1",
            subset="default",
            split="train",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="package_name", target="package_name"),
                ],
            ),
        )

        hub_dataset_test = HubDataset(
            name="lhoestq/demo1",
            subset="default",
            split="test",
            mapping=DatasetMapping(
                fields=[
                    DatasetMappingItem(source="package_name", target="package_name"),
                ],
            ),
        )

        try:
            await hub_dataset_train.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 5

            await hub_dataset_train.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 5

            await hub_dataset_test.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 10

            await hub_dataset_test.import_to(db, mock_search_engine, dataset)
            assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 10
        except (HfHubHTTPError, DataFilesNotFoundError, ReadTimeout, ConnectTimeout, HTTPError, RequestException) as e:
            pytest.skip(f"Skipping test due to Hugging Face Hub connection error: {e}")

        records = (await db.execute(select(Record))).scalars().all()
        assert [record.external_id for record in records] == [
            "train_0",
            "train_1",
            "train_2",
            "train_3",
            "train_4",
            "test_0",
            "test_1",
            "test_2",
            "test_3",
            "test_4",
        ]
