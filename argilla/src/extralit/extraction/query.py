import logging
from typing import List, Dict, Any, Optional, Union

from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator, FilterCondition,
)
from llama_index.vector_stores.weaviate.base import _to_weaviate_filter
from llama_index.vector_stores.weaviate.utils import validate_client, class_schema_exists
from weaviate import WeaviateClient
from weaviate.exceptions import WeaviateQueryError

_LOGGER = logging.getLogger(__name__)


def get_nodes_metadata(weaviate_client: WeaviateClient,
                       filters: Union[Dict[str, Any], MetadataFilters],
                       index_name: str='LlamaIndexDocumentSections',
                       properties: Union[List, Dict] = ['header', 'page_number', 'type', 'reference', 'doc_id'],
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Query document nodes and metadata from Vector DB based on specified filters.
    
    Args:
        weaviate_client (WeaviateClient): The Weaviate client object.
        filters (Union[Dict[str, Any], MetadataFilters]): The filters to apply on the metadata.
            It can be either a dictionary of key-value pairs or a MetadataFilters object.
        index_name (str, optional): The name of the index to query. Defaults to 'LlamaIndexDocumentSections'.
        properties (Union[List, Dict], optional): The properties to include in the query result.
            It can be a list of property names or a dictionary of property names and their values.
            Defaults to ['header', 'page_number', 'type', 'reference', 'doc_id'].
        limit (Optional[int], optional): The maximum number of results to return. Defaults to None.
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the metadata of the nodes.
    Raises:
        None
    Examples:
        # Example 1: Retrieve metadata with simple filters
        filters = {'type': 'chapter', 'reference': 'ch01'}
        metadata = get_nodes_metadata(weaviate_client, filters)
        # Example 2: Retrieve metadata with complex filters
                MetadataFilter(key='type', value='chapter', operator=FilterOperator.EQ),
                MetadataFilter(key='reference', value=['ch01', 'ch02'], operator=FilterOperator.IN)
            ],
        metadata = get_nodes_metadata(weaviate_client, filters, limit=10)
    """

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

    try:
        query_result = collection.query.fetch_objects(
            filters=_to_weaviate_filter(filters),
            return_properties=properties,
            limit=limit,
        )

        entries = [o.properties for o in query_result.objects]
        return entries
    
    except WeaviateQueryError as wqe:
        _LOGGER.error("Error while querying Weaviate: %s", wqe)
        return []



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

