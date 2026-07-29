from unittest.mock import patch

import pandera.pandas as pa
import pytest
from fastapi.encoders import jsonable_encoder

from extralit_server.api.routes import api_v1
from extralit_server.api.schemas.v1.files import ObjectMetadata
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
    to check. That matters: a hand-rolled fake that only reads `.fields` (an earlier version of
    this fake) passed against a build of `publish_version` that only refreshed `.fields` and
    left the other three relationships unloaded -- i.e. it passed against a still-broken
    endpoint. Delegating to the real method means this test automatically covers any
    relationship `_configure_index_mappings` reads today AND any it reads in the future (e.g. a
    fifth relationship added later), without anyone having to remember to update this fake.

    The handler loads `dataset` with only `Dataset.workspace` eagerly loaded
    (handlers/v1/datasets/schema_versions.py). Without `contexts/schema_versions.publish_version`
    refreshing every relationship `_configure_index_mappings` reads after the commit, this
    engine's `create_index` blows up on the first unloaded lazy relationship it touches --
    `MissingGreenlet` on an `AsyncSession`.
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
            version_id="v1",
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

    async def test_publish_refreshes_every_relationship_create_index_reads_before_creating_the_index(
        self, async_client, owner_auth_header
    ):
        """Critical 1 pin. See `_RealMappingSearchEngine` for why this must call the real
        `_configure_index_mappings` rather than hand-read a chosen subset of relationships.
        """
        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(workspace=workspace, status=DatasetStatus.draft)
        # One of each relationship `_configure_index_mappings` reads besides `fields` (which
        # the schema-versions publish itself populates via the "population" column below).
        metadata_property = await IntegerMetadataPropertyFactory.create(dataset=dataset)
        vector_settings = await VectorSettingsFactory.create(dataset=dataset)
        question = await RatingQuestionFactory.create(dataset=dataset)

        fake_engine = _RealMappingSearchEngine()

        async def override_get_search_engine():
            yield fake_engine

        api_v1.dependency_overrides[get_search_engine] = override_get_search_engine
        try:
            response = await async_client.post(
                f"/api/v1/datasets/{dataset.id}/schema-versions",
                headers=owner_auth_header,
                json={"body": _body()},
            )
        finally:
            api_v1.dependency_overrides.pop(get_search_engine, None)

        assert response.status_code == 201, response.json()
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
        # Critical 2. Real backends' `indices.create` raises `resource_already_exists_exception`
        # on a second call for the same dataset (es_index_name_for_dataset is stable per
        # dataset id). Simulate that here: configure the mock the same way, so that if
        # `publish_version` ever called `create_index` unconditionally again, this request
        # would fail loudly instead of silently passing.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        first = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert first.status_code == 201, first.json()

        mock_search_engine.index_exists.return_value = True
        mock_search_engine.create_index.side_effect = AssertionError("must not recreate an existing index")

        second = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert second.status_code == 201, second.json()
        assert second.json()["version"] == 2

    async def test_publish_schema_version_on_a_dataset_already_published_via_put_publish(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        # Critical 2's second broken flow: PUT /datasets/{id}/publish already created the
        # index; a *first* schema-versions publish on that same dataset must not try to
        # recreate it.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        await TextFieldFactory.create(dataset=dataset, required=True)
        await RatingQuestionFactory.create(dataset=dataset, required=True)
        # This is the *other* duplicate-`published` flow: PUT /publish already fired the
        # event, so the schema-version publish that follows must not fire it a second time.
        # It is also what distinguishes the implemented `was_already_ready` guard from a
        # plausible "this is not version 1" alternative, which would pass the two-versions
        # test and still re-fire here.
        webhook = await WebhookFactory.create(events=[DatasetEvent.published])

        publish = await async_client.put(f"/api/v1/datasets/{dataset.id}/publish", headers=owner_auth_header)
        assert publish.status_code == 200, publish.json()
        mock_search_engine.create_index.assert_awaited_once()
        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id

        mock_search_engine.index_exists.return_value = True
        mock_search_engine.create_index.side_effect = AssertionError("must not recreate an existing index")

        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 201, response.json()
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

    async def test_publish_schema_version_enqueues_webhook_dataset_published_event(
        self, db, async_client, owner_auth_header, mock_search_engine
    ):
        # Important 3: publish_version flips status -> ready but, before this fix, never
        # notified -- extraction datasets went ready silently while annotation datasets
        # (contexts/datasets.py::publish_dataset) fired correctly.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        webhook = await WebhookFactory.create(events=[DatasetEvent.published])

        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert response.status_code == 201, response.json()

        event = await build_dataset_event(db, DatasetEvent.published, dataset)

        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[0].args[1] == DatasetEvent.published
        assert HIGH_QUEUE.jobs[0].args[3] == jsonable_encoder(event.data)

    async def test_republishing_does_not_refire_the_webhook_dataset_published_event(
        self, async_client, owner_auth_header, mock_search_engine
    ):
        # Minor found in re-review: publish_version has no draft-gate (unlike
        # contexts/datasets.py::publish_dataset, which can only fire once because
        # DatasetPublishValidator rejects publishing an already-ready dataset). Without
        # tracking the pre-update status, every republish (version 2..n) would re-fire
        # `published` for a dataset that was already ready.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        webhook = await WebhookFactory.create(events=[DatasetEvent.published])

        first = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert first.status_code == 201, first.json()
        assert HIGH_QUEUE.count == 1

        second = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert second.status_code == 201, second.json()
        assert second.json()["version"] == 2

        # Still just the one job, from the first publish's draft -> ready transition.
        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[0] == webhook.id

    async def test_republishing_fires_the_webhook_dataset_updated_event(
        self, db, async_client, owner_auth_header, mock_search_engine
    ):
        # The counterpart to the test above: suppressing `published` on a republish must not
        # leave the republish silent. `current_schema_version_id` is reassigned and new
        # `Field` rows are materialized, so a consumer subscribed to both events has to be
        # able to learn that versions 2..n exist.
        dataset = await DatasetFactory.create(status=DatasetStatus.draft)
        webhook = await WebhookFactory.create(events=[DatasetEvent.published, DatasetEvent.updated])

        first = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert first.status_code == 201, first.json()
        assert HIGH_QUEUE.count == 1
        assert HIGH_QUEUE.jobs[0].args[1] == DatasetEvent.published

        second = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/schema-versions",
            headers=owner_auth_header,
            json={"body": _body()},
        )
        assert second.status_code == 201, second.json()

        # The event type differs between the first publish and the republish.
        assert HIGH_QUEUE.count == 2
        assert HIGH_QUEUE.jobs[1].args[0] == webhook.id
        assert HIGH_QUEUE.jobs[1].args[1] == DatasetEvent.updated
        event = await build_dataset_event(db, DatasetEvent.updated, dataset)
        assert HIGH_QUEUE.jobs[1].args[3] == jsonable_encoder(event.data)


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
