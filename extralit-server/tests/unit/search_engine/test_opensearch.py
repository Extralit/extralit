import pytest
from opensearchpy import OpenSearch, RequestError
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.search_engine import OpenSearchEngine
from extralit_server.search_engine.commons import es_index_name_for_dataset
from extralit_server.settings import settings
from tests.factories import DatasetFactory, VectorSettingsFactory
from tests.unit.search_engine.test_commons import refresh_dataset


@pytest.mark.asyncio
@pytest.mark.skipif(not settings.search_engine == "opensearch", reason="Running on opensearch engine")
class TestOpenSearchEngine:
    async def test_create_index_for_dataset(
        self, opensearch_engine: OpenSearchEngine, db: AsyncSession, opensearch: OpenSearch
    ):
        dataset = await DatasetFactory.create()

        await refresh_dataset(dataset)

        await opensearch_engine.create_index(dataset)

        index_name = es_index_name_for_dataset(dataset)
        assert opensearch.indices.exists(index=index_name)

        index = opensearch.indices.get(index=index_name)[index_name]
        assert index["settings"]["index"]["knn"] == "false"

    async def test_create_dataset_index_with_vectors(self, search_engine: OpenSearchEngine, opensearch: OpenSearch):
        vectors_settings = await VectorSettingsFactory.create_batch(5)
        dataset = await DatasetFactory.create(vectors_settings=vectors_settings)

        await refresh_dataset(dataset)
        await search_engine.create_index(dataset)

        index_name = es_index_name_for_dataset(dataset)
        assert opensearch.indices.exists(index=index_name)

        index = opensearch.indices.get(index=index_name)[index_name]
        assert index["mappings"]["properties"]["vectors"]["properties"] == {
            str(settings.id): {
                "type": "knn_vector",
                "dimension": settings.dimensions,
                "method": {
                    "engine": "lucene",
                    "space_type": "cosinesimil",
                    "name": "hnsw",
                    "parameters": {"ef_construction": 4, "m": 2},
                },
            }
            for settings in vectors_settings
        }

        assert index["settings"]["index"]["knn"] == "false"

    async def test_create_index_with_existing_index(self, search_engine: OpenSearchEngine, opensearch: OpenSearch):
        dataset = await DatasetFactory.create()

        await refresh_dataset(dataset)

        await search_engine.create_index(dataset)

        index_name = es_index_name_for_dataset(dataset)
        assert opensearch.indices.exists(index=index_name)

        with pytest.raises(RequestError, match="resource_already_exists_exception"):
            await search_engine.create_index(dataset)
