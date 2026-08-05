import datasets
import pytest

from extralit_server.contexts import hub
from extralit_server.contexts.hub import HubDatasetExporter
from extralit_server.enums import DatasetStatus, FieldType
from tests.database import SyncTestSession
from tests.factories import DatasetSyncFactory, FieldSyncFactory, RecordSyncFactory


@pytest.fixture
def sync_test_session(mocker):
    session = SyncTestSession()

    def override_get_sync_db():
        yield session

    mocker.patch.object(hub, "get_sync_db", override_get_sync_db)

    yield session


class TestHubDatasetExporter:
    def test_export_to(self, sync_test_session, mocker):
        """The basic export path: records are read from the database and shaped into the
        `datasets.Dataset` that gets pushed.

        The push itself is mocked rather than exercised. Nothing is created on Hugging Face,
        so this needs no token and no `extralit-dev` repo, and it asserts on the dataset
        directly instead of round-tripping it through the Hub to read it back.
        """
        push_to_hub = mocker.patch.object(datasets.Dataset, "push_to_hub", autospec=True)
        push_extra_files = mocker.patch.object(HubDatasetExporter, "_push_extra_files_to_hub")

        dataset = DatasetSyncFactory.create(status=DatasetStatus.ready)
        FieldSyncFactory.create(
            name="text", settings={"type": FieldType.text, "use_markdown": False, "use_table": False}, dataset=dataset
        )
        record = RecordSyncFactory.create(fields={"text": "Hello World"}, dataset=dataset)

        HubDatasetExporter(dataset).export_to(
            name="extralit-dev/extralit-server-dataset-test",
            subset="default",
            split="train",
            private=False,
            token="fake-token",
        )

        # autospec=True makes the bound instance the first positional arg, which is the
        # dataset that would have been uploaded.
        exported_dataset = push_to_hub.call_args.args[0]
        assert exported_dataset[0] == {
            "id": record.external_id,
            "status": record.status,
            "inserted_at": record.inserted_at,
            "updated_at": record.updated_at,
            "_server_id": str(record.id),
            "text": "Hello World",
        }
        assert exported_dataset.split == "train"

        assert push_to_hub.call_args.kwargs == {
            "repo_id": "extralit-dev/extralit-server-dataset-test",
            "config_name": "default",
            "private": False,
            "token": "fake-token",
        }
        push_extra_files.assert_called_once_with(
            repo_id="extralit-dev/extralit-server-dataset-test", token="fake-token"
        )
