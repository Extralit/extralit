import pytest
from opensearchpy import OpenSearch

from extralit_server.search_engine import ElasticSearchEngine
from extralit_server.search_engine.commons import es_index_name_for_dataset
from extralit_server.settings import settings
from tests.factories import DatasetFactory, VectorSettingsFactory
from tests.unit.search_engine.test_commons import refresh_dataset


@pytest.mark.asyncio
@pytest.mark.skipif(not settings.search_engine == "elasticsearch", reason="Running on elasticsearch engine")
class TestElasticSearchEngine:
    async def test_create_dataset_index_with_vectors(self, search_engine: ElasticSearchEngine, opensearch: OpenSearch):
        vectors_settings = await VectorSettingsFactory.create_batch(5)
        dataset = await DatasetFactory.create(vectors_settings=vectors_settings)

        await refresh_dataset(dataset)
        await search_engine.create_index(dataset)

        index_name = es_index_name_for_dataset(dataset)
        assert opensearch.indices.exists(index=index_name)

        index = opensearch.indices.get(index=index_name)[index_name]
        assert index["mappings"]["properties"]["vectors"]["properties"] == {
            str(settings.id): {
                "type": "dense_vector",
                "dims": settings.dimensions,
                "index": True,
                "similarity": "cosine",
                "index_options": {
                    "type": "int8_hnsw",
                    "m": 16,
                    "ef_construction": 100,
                },
            }
            for settings in vectors_settings
        }

    async def test_create_index_with_existing_index(self, search_engine: ElasticSearchEngine, opensearch: OpenSearch):
        from elasticsearch8 import RequestError

        dataset = await DatasetFactory.create()

        await refresh_dataset(dataset)

        await search_engine.create_index(dataset)

        index_name = es_index_name_for_dataset(dataset)
        assert opensearch.indices.exists(index=index_name)

        with pytest.raises(RequestError, match="resource_already_exists_exception"):
            await search_engine.create_index(dataset)
