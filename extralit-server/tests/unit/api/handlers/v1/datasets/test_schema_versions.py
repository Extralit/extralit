from unittest.mock import patch

import pandera.pandas as pa
import pytest
from fastapi.encoders import jsonable_encoder

from extralit_server.api.routes import api_v1
from extralit_server.api.schemas.v1.files import ObjectMetadata
from extralit_server.api.schemas.v1.schema_versions import SCHEMA_VERSION_BODY_MAX_LENGTH
from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.enums import DatasetStatus
from extralit_server.jobs.queues import HIGH_QUEUE
from extralit_server.search_engine import get_search_engine
from extralit_server.search_engine.commons import (
    es_field_for_metadata_property,
    es_field_for_record_field,
    es_field_for_vector_settings,
)
from extralit_server.search_engine.elasticsearch import ElasticSearchEngine
from extralit_server.webhooks.v1.datasets import build_dataset_event
from extralit_server.webhooks.v1.enums import DatasetEvent
from tests.factories import (
    AdminFactory,
    AnnotatorFactory,
    DatasetFactory,
    IntegerMetadataPropertyFactory,
    RatingQuestionFactory,
    TextFieldFactory,
    VectorSettingsFactory,
    WebhookFactory,
    WorkspaceFactory,
)


def _body() -> str:
    return pa.DataFrameSchema({"population": pa.Column(str, nullable=True)}).to_json()


class _RealMappingSearchEngine:
    """Fake engine whose `create_index` calls the REAL `ElasticSearchEngine._configure_index_mappings`
    -- unlike `mocker.AsyncMock(SearchEngine)` (the suite-wide `mock_search_engine` fixture),
    which never touches the ORM and so cannot express Critical 1's bug at all.

    `_configure_index_mappings` (search_engine/commons.py) is a pure function of the ORM
    object: it reads FOUR relationships off `dataset` (`fields`, `metadata_properties`,
    `vectors_settings`, `questions`) and needs no live cluster connection to run, so this fake
    can call the real production code path directly instead of hand-picking which relationships
    to check. Delegating to the real method means this test automatically covers any
    relationship `_configure_index_mappings` reads today AND any it reads in the future (e.g. a
    fifth relationship added later), without anyone having to remember to update this fake.
    """

    def __init__(self):
        # number_of_shards/replicas are required dataclass fields but irrelevant here --
        # `_configure_index_mappings` never reads them. `config` needs a `hosts` entry only so
        # `AsyncElasticsearch.__init__` doesn't raise; no request is ever sent to it.
        self._engine = ElasticSearchEngine(
            number_of_shards=1, number_of_replicas=0, config={"hosts": ["http://localhost:9200"]}
        )
        self.observed_mappings: dict | None = None

    async def create_index(self, dataset):
        self.observed_mappings = self._engine._configure_index_mappings(dataset)

    async def index_exists(self, dataset) -> bool:
        return False


@pytest.fixture(autouse=True)
def _mock_put_object():
    # `publish_version` (Task 6) calls the real `files_ctx.put_object`, which would
    # otherwise hit real object storage (or the LocalFileClient fallback under
    # ~/.extralit) through the `files_ctx.get_s3_client` dependency. Stub at the
    # `put_object` call site rather than the dependency itself, matching the existing
    # convention in tests/unit/api/handlers/v1/test_files.py (`test_put_file` patches
    # `extralit_server.contexts.files.put_object`). This keeps the stub local to this
    # test module instead of adding a suite-wide override to tests/unit/conftest.py.
    with patch("extralit_server.contexts.schema_versions.files_ctx.put_object") as mock_put_object:
        mock_put_object.return_value = ObjectMetadata(
            bucket_name="workspace",
            object_name="schemas/dataset/v1.json",
            etag="etag",
        )
        yield mock_put_object


@pytest.mark.asyncio
class TestPublishSchemaVersion:
    async def test_owner_publishes_a_version(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 201, response.json()
        assert response.json()["version"] == 1
        assert response.json()["dataset_id"] == str(dataset.id)

    async def test_publish_returns_422_for_an_invalid_body(self, async_client, owner_auth_header):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": "{not pandera}"},
        )
        assert response.status_code == 422

    async def test_publish_returns_422_for_an_oversized_body(self, async_client, owner_auth_header):
        # The body is parsed in-process and then uploaded whole, so one request sizes both
        # the parse and the object write. Rejected by the request schema, before either.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": "x" * (SCHEMA_VERSION_BODY_MAX_LENGTH + 1)},
        )
        assert response.status_code == 422

    async def test_publish_returns_404_for_an_unknown_dataset(self, async_client, owner_auth_header):
        response = await async_client.post(
            "/api/v1/datasets/00000000-0000-0000-0000-000000000000/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 404

    async def test_annotator_cannot_publish(self, async_client, mock_search_engine):
        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(workspace=workspace, status=DatasetStatus.draft)
        annotator = await AnnotatorFactory.create(workspaces=[workspace])
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers={"X-Extralit-Api-Key": annotator.api_key},
            json={"body": _body()},
        )
        assert response.status_code == 403

    async def test_published_columns_are_readable_as_dataset_fields(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        # The former GET /schemas/{id}/columns is now the existing v1 fields endpoint.
        fields = await async_client.get(f"/api/v1/datasets/{dataset.id}/fields", headers=owner_auth_header)
        assert fields.status_code == 200
        assert [f["name"] for f in fields.json()["items"]] == ["population"]
        # NOT "str" — see Task 6 Step 1; pandera emits "string"/"string[pyarrow]"/"object".
        assert fields.json()["items"][0]["settings"]["dtype"] in {"string", "string[pyarrow]", "object"}

    async def test_admin_member_can_publish(self, async_client, owner_auth_header):
        # T7: DatasetPolicy.publish grants owner OR admin-member (dataset_policy.py:110-114);
        # the admin branch was untested on this endpoint.
        workspace = await WorkspaceFactory.create()
        admin = await AdminFactory.create(workspaces=[workspace])
        dataset = await DatasetFactory.create(workspace=workspace, status=DatasetStatus.draft)

        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers={API_KEY_HEADER_NAME: admin.api_key},
            json={"body": _body()},
        )
        assert response.status_code == 201, response.json()

    async def test_admin_outside_the_workspace_cannot_publish(self, async_client):
        # T7: no cross-workspace/non-member-denied case existed for this endpoint.
        workspace = await WorkspaceFactory.create()
        other_workspace = await WorkspaceFactory.create()
        admin = await AdminFactory.create(workspaces=[other_workspace])
        dataset = await DatasetFactory.create(workspace=workspace, status=DatasetStatus.draft)

        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers={API_KEY_HEADER_NAME: admin.api_key},
            json={"body": _body()},
        )
        assert response.status_code == 403

    async def test_published_columns_reach_the_search_index_mapping(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        """The column fields a schema version materializes must appear in the index mapping
        that `PUT /datasets/{id}/publish` builds -- that publish is the only `create_index`
        caller, and the mapping it builds is `"dynamic": "strict"`, so a column missing from it
        makes the dataset unwritable for that column. See `_RealMappingSearchEngine` for why
        this calls the real `_configure_index_mappings` rather than hand-reading a subset.
        """
        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(workspace=workspace, status=DatasetStatus.draft)
        # One of each relationship `_configure_index_mappings` reads besides `fields` (which
        # the schema-versions publish below populates via the "population" column).
        metadata_property = await IntegerMetadataPropertyFactory.create(dataset=dataset)
        vector_settings = await VectorSettingsFactory.create(dataset=dataset)
        question = await RatingQuestionFactory.create(dataset=dataset, required=True)

        version = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert version.status_code == 201, version.json()

        fake_engine = _RealMappingSearchEngine()

        async def override_get_search_engine():
            yield fake_engine

        api_v1.dependency_overrides[get_search_engine] = override_get_search_engine
        try:
            response = await async_client.put(f"/api/v1/datasets/{dataset.id}/publish", headers=owner_auth_header)
        finally:
            api_v1.dependency_overrides.pop(get_search_engine, None)

        assert response.status_code == 200, response.json()
        properties = fake_engine.observed_mappings["properties"]
        # dataset.fields (the "population" column projected from this publish's body)
        assert es_field_for_record_field("population") in properties
        # dataset.metadata_properties
        assert es_field_for_metadata_property(metadata_property) in properties
        # dataset.vectors_settings
        assert es_field_for_vector_settings(vector_settings) in properties
        # dataset.questions (suggestions + responses mappings)
        assert f"suggestions.{question.name}" in properties
        assert question.name in properties["responses"]["properties"]

    async def test_republishing_does_not_500(self, async_client, owner_auth_header, mock_search_engine):
        # `create_index` is not idempotent on real backends (es_index_name_for_dataset is
        # stable per dataset id), which is one reason publishing a schema version does not
        # touch the index at all. Assert the mock stays untouched across both publishes.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        first = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert first.status_code == 201, first.json()

        second = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert second.status_code == 201, second.json()
        assert second.json()["version"] == 2
        mock_search_engine.create_index.assert_not_awaited()

    async def test_publish_schema_version_on_a_dataset_already_published_via_put_publish_returns_422(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        # A dataset published as an annotation dataset already has a `"dynamic": "strict"`
        # index, and nothing evolves that mapping afterwards, so it cannot retroactively gain
        # schema columns. The 422 keeps that failure at the publish call rather than surfacing
        # later as a rejected record write.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await TextFieldFactory.create(dataset=dataset, required=True)
        await RatingQuestionFactory.create(dataset=dataset, required=True)
        webhook = await WebhookFactory.create(events=[DatasetEvent.published])

        publish = await async_client.put(f"/api/v1/datasets/{dataset.id}/publish", headers=owner_auth_header)
        assert publish.status_code == 200, publish.json()
        mock_search_engine.create_index.assert_awaited_once()
        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id

        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 422
        assert "cannot be added to a published dataset" in response.text
        assert HIGH_QUEUE.count == 1

    async def test_republishing_with_a_changed_column_dtype_returns_422(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        first = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert first.status_code == 201, first.json()

        changed_body = pa.DataFrameSchema({"population": pa.Column(pa.Int64, nullable=True)}).to_json()
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": changed_body},
        )
        assert response.status_code == 422
        assert "population" in response.text

    async def test_publish_schema_version_enqueues_webhook_dataset_updated_event(
        self, db, async_client, owner_auth_header, mock_search_engine
    ):
        # A schema version reassigns `current_schema_version_id` and materializes `Field`
        # rows, so it is a dataset mutation -- `updated`, the same event update_dataset fires.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        webhook = await WebhookFactory.create(events=[DatasetEvent.updated])

        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 201, response.json()

        event = await build_dataset_event(db, DatasetEvent.updated, dataset)

        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == DatasetEvent.updated
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event.data)

    async def test_publishing_a_schema_version_never_fires_dataset_published(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        # `published` belongs to `PUT /datasets/{id}/publish` alone. Publishing a schema
        # version leaves the dataset a draft, so a consumer subscribed only to `published`
        # hears nothing until the dataset is actually published.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await WebhookFactory.create(events=[DatasetEvent.published])

        for expected_version in (1, 2):
            response = await async_client.post(
                f"/api/v1/datasets/{dataset.id}/schema-versions",
                headers=owner_auth_header,
                json={"body": _body()},
            )
            assert response.status_code == 201, response.json()
            assert response.json()["version"] == expected_version

        assert HIGH_QUEUE.count == 0

    async def test_every_republish_fires_the_webhook_dataset_updated_event(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        # Without this a consumer subscribed to `updated` learns about version 1 and never
        # learns that versions 2..n exist.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        webhook = await WebhookFactory.create(events=[DatasetEvent.updated])

        for expected_version in (1, 2):
            response = await async_client.post(
                f"/api/v1/datasets/{dataset.id}/schema-versions",
                headers=owner_auth_header,
                json={"body": _body()},
            )
            assert response.status_code == 201, response.json()
            assert response.json()["version"] == expected_version

        assert HIGH_QUEUE.count == 2
        assert [job.args[0] for job in HIGH_QUEUE.jobs] == [webhook.id, webhook.id]
        assert [job.args[1] for job in HIGH_QUEUE.jobs] == [DatasetEvent.updated, DatasetEvent.updated]


@pytest.mark.asyncio
class TestReadSchemaVersions:
    async def test_list_versions(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        for _ in range(2):
            await async_client.post(
                f"/api/v1/datasets/{dataset.id}/schema-versions",
                headers=owner_auth_header,
                json={"body": _body()},
            )
        response = await async_client.get(f"/api/v1/datasets/{dataset.id}/schema-versions", headers=owner_auth_header)
        assert response.status_code == 200
        assert [v["version"] for v in response.json()] == [1, 2]

    async def test_list_versions_is_empty_for_an_unpublished_dataset(self, async_client, owner_auth_header):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.get(f"/api/v1/datasets/{dataset.id}/schema-versions", headers=owner_auth_header)
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_version_by_number(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        response = await async_client.get(f"/api/v1/datasets/{dataset.id}/schema-versions/1", headers=owner_auth_header)
        assert response.status_code == 200
        assert response.json()["version"] == 1

    async def test_get_unknown_version_returns_404(self, async_client, owner_auth_header):
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        response = await async_client.get(
            f"/api/v1/datasets/{dataset.id}/schema-versions/99", headers=owner_auth_header
        )
        assert response.status_code == 404

    async def test_annotator_in_the_workspace_can_read_versions(self, async_client):
        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(workspace=workspace)
        annotator = await AnnotatorFactory.create(workspaces=[workspace])
        response = await async_client.get(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers={"X-Extralit-Api-Key": annotator.api_key},
        )
        assert response.status_code == 200
