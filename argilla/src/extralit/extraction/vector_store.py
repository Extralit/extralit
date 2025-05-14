"""Weaviate Vector store index.

An index that is built on top of an existing vector store.

"""

import logging
from typing import Any, List, Dict, Optional, Union, Callable

import weaviate  # noqa
import weaviate.classes as wvc
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    VectorStoreQuery,
    VectorStoreQueryMode,
    VectorStoreQueryResult, FilterOperator, )
from llama_index.vector_stores.weaviate import WeaviateVectorStore as WeaviateVectorStoreV0_10_0
from llama_index.vector_stores.weaviate.utils import (
    get_all_properties,
    get_node_similarity,
    to_node, validate_client,
)

_LOGGER = logging.getLogger(__name__)

NODE_SCHEMA: List[Dict] = [
    {
        "dataType": ["text"],
        "description": "Text property",
        "name": "text",
    },
    {
        "dataType": ["text"],
        "description": "The ref_doc_id of the Node",
        "name": "ref_doc_id",
    },
    {
        "dataType": ["text"],
        "description": "node_info (in JSON)",
        "name": "node_info",
    },
    {
        "dataType": ["text"],
        "description": "The relationships of the node (in JSON)",
        "name": "relationships",
    },
    {
        "dataType": ["text"],
        "description": "The reference of the Node",
        "name": "reference",
    },
    {
        "dataType": ["text"],
        "description": "The type of the Node",
        "name": "type",
    },
    {
        "dataType": ["text"],
        "description": "The header of the Node",
        "name": "header",
    },
    {
        "dataType": ["text"],
        "description": "The doc_id of the Node",
        "name": "doc_id",
    },
]

def create_default_schema(client: weaviate.WeaviateClient, class_name: str) -> None:
    """Create default schema."""
    validate_client(client)
    class_schema = {
        "class": class_name,
        "description": f"Class for {class_name}",
        "properties": NODE_SCHEMA,
        'vectorIndexType': 'flat',
        # "multiTenancyConfig": {"enabled": True},
    }
    client.collections.create_from_dict(class_schema)



def _transform_weaviate_filter_condition(condition: str) -> Callable:
    """Translate standard metadata filter op to Chroma specific spec."""
    if condition == "and":
        return wvc.query.Filter.all_of
    elif condition == "or":
        return wvc.query.Filter.any_of
    else:
        raise ValueError(f"Filter condition {condition} not supported")


def _transform_weaviate_filter_operator(operator: FilterOperator) -> str:
    """Translate standard metadata filter operator to Weaviate specific spec.
    See https://weaviate.io/developers/weaviate/api/graphql/filters#filter-structure
    """
    if operator == FilterOperator.NE:
        return "not_equal"
    elif operator == FilterOperator.EQ:
        return "equal"
    elif operator == FilterOperator.GT:
        return "greater_than"
    elif operator == FilterOperator.LT:
        return "less_than"
    elif operator == FilterOperator.GTE:
        return "greater_or_equal"
    elif operator == FilterOperator.LTE:
        return "less_or_equal"
    elif operator == FilterOperator.IN:
        return "contains_any"
    elif operator == FilterOperator.ALL:
        return "contains_all"
    elif operator == FilterOperator.TEXT_MATCH:
        return "like"
    else:
        raise ValueError(f"Filter operator {operator} not supported")


def _to_weaviate_filter(
    standard_filters: MetadataFilters,
) -> Union[wvc.query.Filter, List[wvc.query.Filter]]:
    filters_list = []
    condition = standard_filters.condition or "and"
    condition = _transform_weaviate_filter_condition(condition)

    if standard_filters.filters:
        for filter in standard_filters.filters:
            filters_list.append(
                getattr(
                    wvc.query.Filter.by_property(filter.key),
                    _transform_weaviate_filter_operator(filter.operator),
                )(filter.value)
            )
    else:
        return {}

    if len(filters_list) == 1:
        # If there is only one filter, return it directly
        return filters_list[0]

    return condition(filters_list)


class WeaviateVectorStore(WeaviateVectorStoreV0_10_0):

    def get_nodes(self, node_ids: Optional[List[str]] = None, filters: Optional[MetadataFilters] = None) \
            -> List[BaseNode]:
        collection = self._client.collections.get(self.index_name)
        all_properties = get_all_properties(self._client, self.index_name)

        if filters is not None:
            filters = _to_weaviate_filter(filters)

        # list of documents to constrain search
        if node_ids is not None:
            filters = wvc.query.Filter.by_property("id").contains_any(node_ids)

        query_result = collection.query.fetch_objects(
            filters=filters,
            return_properties=all_properties,
            include_vector=False,
        )

        entries = [to_node(o.__dict__) for o in query_result.objects]
        return entries

    def delete_nodes(
            self,
            node_ids: Optional[List[str]] = None,
            filters: Optional[MetadataFilters] = None,
            **delete_kwargs: Any,
    ) -> None:
        collection = self._client.collections.get(self.index_name)

        if node_ids is not None:
            filters = wvc.query.Filter.by_property("id").contains_any(node_ids)
        elif filters is not None:
            filters = _to_weaviate_filter(filters)
        else:
            raise ValueError("Either node_ids or filters must be provided")

        results = collection.data.delete_many(where=filters, verbose=True)
        if results.objects:
            _LOGGER.debug(f"Deleted {len(results.objects)} nodes")

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """Query index for top k most similar nodes."""
        all_properties = get_all_properties(self._client, self.index_name)
        collection = self._client.collections.get(self.index_name)
        filters = None

        # list of documents to constrain search
        if query.doc_ids:
            filters = wvc.query.Filter.by_property("doc_id").contains_any(query.doc_ids)

        if query.node_ids:
            filters = wvc.query.Filter.by_property("id").contains_any(query.node_ids)

        return_metatada = wvc.query.MetadataQuery(distance=True, score=True)

        vector = query.query_embedding
        similarity_key = "distance"
        if query.mode == VectorStoreQueryMode.DEFAULT:
            _LOGGER.debug("Using vector search")
            if vector is not None:
                alpha = 1
        elif query.mode == VectorStoreQueryMode.HYBRID:
            _LOGGER.debug(f"Using hybrid search with alpha {query.alpha}")
            similarity_key = "score"
            if vector is not None and query.query_str:
                alpha = query.alpha

        if query.filters is not None:
            filters = _to_weaviate_filter(query.filters)
        elif "filter" in kwargs and kwargs["filter"] is not None:
            filters = kwargs["filter"]

        limit = query.similarity_top_k
        _LOGGER.debug(f"Using limit of {query.similarity_top_k}")

        # execute query
        try:
            query_result = collection.query.hybrid(
                query=query.query_str,
                vector=vector,
                alpha=alpha,
                limit=limit,
                filters=filters,
                return_metadata=return_metatada,
                return_properties=all_properties,
                include_vector=True,
            )
        except weaviate.exceptions.WeaviateQueryError as e:
            raise ValueError(f"Invalid query, got errors: {e.message}")

        # parse results

        entries = query_result.objects

        similarities = []
        nodes: List[BaseNode] = []
        node_ids = []

        for i, entry in enumerate(entries):
            if i < query.similarity_top_k:
                entry_as_dict = entry.__dict__
                similarities.append(get_node_similarity(entry_as_dict, similarity_key))
                nodes.append(to_node(entry_as_dict, text_key=self.text_key))
                node_ids.append(nodes[-1].node_id)
            else:
                break

        return VectorStoreQueryResult(
            nodes=nodes, ids=node_ids, similarities=similarities
        )