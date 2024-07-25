from typing import List, Dict, Any, Optional, Union

from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator, FilterCondition,
)
from llama_index.vector_stores.weaviate.base import _to_weaviate_filter
from llama_index.vector_stores.weaviate.utils import validate_client, class_schema_exists
from weaviate import WeaviateClient


def get_nodes_metadata(weaviate_client: WeaviateClient,
                       filters: Union[Dict[str, Any], MetadataFilters],
                       index_name: str='LlamaIndexDocumentSections',
                       properties: Union[List, Dict] = ['header', 'page_number', 'type', 'reference', 'doc_id'],
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:

    validate_client(weaviate_client)
    if not class_schema_exists(weaviate_client, index_name):
        return []

    if isinstance(filters, dict):
        assert set(filters.keys()).issubset(
            properties), f"Filters {list(filters)} must be a subset of properties {list(properties)}"
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key=k,
                    value=v,
                    operator=FilterOperator.IN if isinstance(v, list) else FilterOperator.EQ)
                for k, v in filters.items()],
            condition=FilterCondition.AND
        )

    collection = weaviate_client.collections.get(index_name)

    query_result = collection.query.fetch_objects(
        filters=_to_weaviate_filter(filters),
        return_properties=properties,
        limit=limit,
    )

    entries = [o.properties for o in query_result.objects]
    return entries


def vectordb_contains_any(reference: str, *, filters: Optional[Dict[str, str]] = None,
                          weaviate_client: WeaviateClient = None, index_name: str = 'LlamaIndexDocumentSections') -> bool:
    if weaviate_client is None:
        return False

    nodes = get_nodes_metadata(
        weaviate_client, index_name=index_name,
        filters={'reference': reference, **(filters or {})},
        properties=['doc_id', 'reference', 'type'],
        limit=1)

    return len(nodes) > 0

