import logging
import time
from grpc import StatusCode
from grpc.experimental.aio import AioRpcError
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

def get_nodes_metadata(
    weaviate_client: WeaviateClient,
    filters: Union[Dict[str, Any], MetadataFilters],
    index_name: str = 'LlamaIndexDocumentSections',
    properties: Union[List, Dict] = ['header', 'page_number', 'type', 'reference', 'doc_id'],
    limit: Optional[int] = None,
    retries: int = 2  # New parameter
) -> List[Dict[str, Any]]:
    """
    Query document nodes and metadata from Vector DB based on specified filters.
    
    Args:
        weaviate_client (WeaviateClient): The Weaviate client object.
        filters (Union[Dict[str, Any], MetadataFilters]): The filters to apply on the metadata.
        index_name (str, optional): The name of the index to query. 
        properties (Union[List, Dict], optional): The properties to include in the query result.
        limit (Optional[int], optional): The maximum number of results to return.
        retries (int, optional): Number of retry attempts for timeout errors. Defaults to 2.
    """
    attempt = 0
    while attempt <= retries:
        try:
            validate_client(weaviate_client)
            if not weaviate_client or not class_schema_exists(weaviate_client, index_name):
                return []

            if isinstance(filters, dict):
                assert set(filters.keys()).issubset(properties), \
                    f"Filters {list(filters)} must be subset of properties {list(properties)}"
                filters = MetadataFilters(
                    filters=[
                        MetadataFilter(
                            key=k,
                            value=v,
                            operator=FilterOperator.IN if isinstance(v, list) else FilterOperator.EQ
                        ) for k, v in filters.items()],
                    condition=FilterCondition.AND
                )

            collection = weaviate_client.collections.get(index_name)
            query_result = collection.query.fetch_objects(
                filters=_to_weaviate_filter(filters),
                return_properties=properties,
                limit=limit,
            )
            return [o.properties for o in query_result.objects]

        except AioRpcError as rpc_error:
            if rpc_error.code() == StatusCode.DEADLINE_EXCEEDED and attempt < retries:
                _LOGGER.warning("Timeout detected, retrying in 3 minutes...")
                time.sleep(180)
                attempt += 1
                continue
            _LOGGER.error("Query failed: %s", rpc_error)
            return []
            
        except WeaviateQueryError as wqe:
            _LOGGER.error("Query failed: %s", wqe)
            return []
    
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

