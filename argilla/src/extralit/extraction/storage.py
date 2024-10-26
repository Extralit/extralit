import os
from typing import Optional

from llama_index.core import StorageContext
from extralit.extraction.vector_store import WeaviateVectorStore, create_default_schema
from llama_index.vector_stores.weaviate.utils import class_schema_exists, NODE_SCHEMA, validate_client
from weaviate import Client, WeaviateClient


def get_storage_context(
        weaviate_client: Optional[WeaviateClient] = None,
        persist_dir: Optional[str] = None,
        index_name: Optional[str] = None) -> StorageContext:
    """
    Create a StorageContext given a persist directory.

    Args:
        persist_dir: str
            The directory where the index is persisted.

    Returns:
        StorageContext
            The created StorageContext.
    """
    kwargs = {}
    if weaviate_client:
        assert index_name
        validate_client(weaviate_client)
        if not class_schema_exists(client=weaviate_client, class_name=index_name):
            create_default_schema(client=weaviate_client, class_name=index_name)

        vector_store = WeaviateVectorStore(
            weaviate_client=weaviate_client,
            index_name=index_name, text_key="text"
        )
        kwargs['vector_store'] = vector_store

    elif persist_dir:
        assert os.path.exists(persist_dir)
        kwargs['persist_dir'] = persist_dir

    else:
        raise ValueError("Either weaviate_client or persist_dir must be given")

    storage_context = StorageContext.from_defaults(**kwargs)
    return storage_context
