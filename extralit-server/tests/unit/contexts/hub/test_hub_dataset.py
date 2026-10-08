import pytest
from datasets.exceptions import DataFilesNotFoundError

# Import Hugging Face and network-related exceptions
from huggingface_hub.errors import HfHubHTTPError
from requests.exceptions import ConnectTimeout, HTTPError, ReadTimeout, RequestException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.datasets import DatasetMapping, DatasetMappingItem
from extralit_server.contexts.hub import HubDataset
from extralit_server.enums import DatasetStatus
from extralit_server.models import Record
from extralit_server.search_engine import SearchEngine
from tests.factories import (
    DatasetFactory,
    IntegerMetadataPropertyFactory,
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
