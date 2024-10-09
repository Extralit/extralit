import logging
import os.path
from collections import Counter
from os.path import join
from typing import Optional, Literal
import warnings

import argilla as rg
from extralit.storage.files import StorageType
import pandas as pd
from llama_index.core import VectorStoreIndex, load_index_from_storage, global_handler
from llama_index.core.node_parser import SentenceSplitter, JSONNodeParser
from llama_index.core.service_context import ServiceContext
from llama_index.core.storage import StorageContext
from llama_index.core.vector_stores import SimpleVectorStore, MetadataFilters, MetadataFilter, FilterOperator
from llama_index.embeddings.openai import OpenAIEmbeddingMode, OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from weaviate import WeaviateClient

from extralit.extraction.chunking import create_nodes
from extralit.extraction.query import vectordb_contains_any
from extralit.extraction.storage import get_storage_context
from extralit.extraction.vector_store import WeaviateVectorStore

DEFAULT_RETRIEVAL_MODE = OpenAIEmbeddingMode.TEXT_SEARCH_MODE
_LOGGER = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=DeprecationWarning)


def create_local_index(
    paper: pd.Series,
    preprocessing_path='data/preprocessing/nougat/',
    preprocessing_dataset: rg.FeedbackDataset = None,
    persist_dir: Optional[str] = None,
    embed_model='text-embedding-3-small',
    dimensions=1536,
    retrieval_mode=DEFAULT_RETRIEVAL_MODE,
    chunk_size=4096,
    chunk_overlap=200,
    verbose=True, 
) -> VectorStoreIndex:
    text_nodes, table_nodes = create_nodes(
        paper, preprocessing_path=preprocessing_path,
        preprocessing_dataset=preprocessing_dataset, 
        storage_type=StorageType.FILE)

    _LOGGER.info(
        f"Creating index with {len(text_nodes)} text and {len(table_nodes)} table segments, `persist_dir={persist_dir}`")

    storage_context = get_storage_context(persist_dir=persist_dir)
    embedding_model = OpenAIEmbedding(
        mode=retrieval_mode, model=embed_model, dimensions=dimensions,
    )

    if global_handler and hasattr(global_handler, 'set_trace_params'):
        global_handler.set_trace_params(
            name=f"embed-{paper.name}", tags=[paper.name]
        )

    embed_model_context = ServiceContext.from_defaults(
        embed_model=embedding_model,
        node_parser=SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
    )
    index = VectorStoreIndex.from_documents(
        text_nodes, storage_context=storage_context, service_context=embed_model_context)

    index.insert_nodes(
        table_nodes, node_parser=JSONNodeParser(chunk_size=chunk_size, chunk_overlap=chunk_overlap))

    if persist_dir and not storage_context.vector_store:
        assert os.path.exists(persist_dir)
        index.storage_context.persist(persist_dir)

    if verbose:
        nodes_counts = Counter([doc.metadata['header'] for doc in index.docstore.docs.values()])
        nodes_counts = [(header, count) for header, count in nodes_counts.most_common() if count > 1]
        print(pd.DataFrame(nodes_counts, columns=['header', 'n_chunks'])) if nodes_counts else None

    return index


def create_vector_index(
    paper: pd.Series,
    weaviate_client: WeaviateClient,
    preprocessing_dataset: Optional[rg.FeedbackDataset] = None,
    preprocessing_path='data/preprocessing/nougat/',
    index_name: Optional[str] = "LlamaIndexDocumentSections",
    embed_model='text-embedding-3-small',
    dimensions=1536,
    retrieval_mode=DEFAULT_RETRIEVAL_MODE,
    overwrite: Literal[True, 'text', 'table', 'figure']='table',
    chunk_size=4096,
    chunk_overlap=200,
    storage_type: StorageType=StorageType.FILE,
    bucket_name: Optional[str]=None,
    verbose=True, 
) -> VectorStoreIndex:
    """
    Creates a VectorStoreIndex for a given paper and loads it into a vector db.

    Args:
        paper (pd.Series): The paper to be indexed.
        weaviate_client (WeaviateClient): The Weaviate client to use.
        preprocessing_dataset (Optional[rg.FeedbackDataset]):
            The preprocessing dataset to use. Defaults to None.
            If given, the TableSegments will be loaded from the Argilla dataset with users' annotations. If None,
            the TableSegments will be loaded from the preprocessed table extractions locally from `preprocessing_path`.
        preprocessing_path (str): The path to the preprocessing data. Defaults to 'data/preprocessing/nougat/'.
        index_name (Optional[str]): The name of the index. Defaults to "LlamaIndexDocumentSections".
        embed_model (str): The model to use for embedding documents. Defaults to 'text-embedding-3-small'.
        dimensions (int): The dimensions of the embedding model. Defaults to 1536.
        retrieval_mode (str): The retrieval mode of the embedding model. Defaults to DEFAULT_RETRIEVAL_MODE.
        overwrite (Literal[True, 'text', 'table', 'figure']): The type of nodes to overwrite. Defaults to True,
            which overwrites all nodes for the reference.
        chunk_size (int): The size of the chunks to split the text into. Defaults to 4096.
        chunk_overlap (int): The size of the overlap between chunks. Defaults to 200.
        storage_type (StorageType): The storage type to use. Defaults to StorageType.FILE.
        bucket_name (Optional[str]): The name of the S3 bucket (i.e. workspace name) to use. Defaults to None.
        verbose (bool): Whether to print verbose output. Defaults to True.

    Returns:
        VectorStoreIndex: The loaded VectorStoreIndex.
    """

    text_nodes, table_nodes = create_nodes(
        paper, preprocessing_path=preprocessing_path,
        preprocessing_dataset=preprocessing_dataset, 
        storage_type=storage_type, bucket_name=bucket_name)

    if global_handler and hasattr(global_handler, 'set_trace_params'):
        global_handler.set_trace_params(
            name=f"embed-{paper.name}", tags=[paper.name]
        )

    vector_store = WeaviateVectorStore(weaviate_client=weaviate_client, index_name=index_name)
    has_existing_node = vectordb_contains_any(paper.name, weaviate_client=weaviate_client, index_name=index_name)
    if has_existing_node and overwrite:
        delete_filters = [MetadataFilter(key="reference", value=paper.name, operator=FilterOperator.EQ)]
        if isinstance(overwrite, str):
            delete_filters.append(MetadataFilter(key="type", value=overwrite, operator=FilterOperator.EQ))
        vector_store.delete_nodes(filters=MetadataFilters(filters=delete_filters,))

    embedding_model = OpenAIEmbedding(mode=retrieval_mode, model=embed_model, dimensions=dimensions)
    embed_model_context = ServiceContext.from_defaults(
        embed_model=embedding_model,
        node_parser=SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
    )

    if has_existing_node and not overwrite:
        _LOGGER.info(f"Skipping existing index for {paper.name}")
        return VectorStoreIndex.from_vector_store(vector_store, service_context=embed_model_context)


    loaded_index = VectorStoreIndex.from_vector_store(vector_store, service_context=embed_model_context)
    for node in text_nodes:
        if has_existing_node and overwrite != 'text':
            continue
        loaded_index.insert(node)
    for node in table_nodes:
        if has_existing_node and overwrite != 'table':
            continue
        loaded_index.insert(node, node_parser=JSONNodeParser(chunk_size=chunk_size, chunk_overlap=chunk_overlap))

    if verbose:
        nodes_counts = Counter([doc.metadata['header'] for doc in loaded_index.docstore.docs.values()])
        nodes_counts = [(header, count) for header, count in nodes_counts.most_common() if count > 1]
        print(pd.DataFrame(nodes_counts, columns=['header', 'n_chunks'])) if nodes_counts else None

    return loaded_index


def load_index(paper: pd.Series, llm_model="gpt-4o", embed_model='text-embedding-3-small',
               weaviate_client: Optional[WeaviateClient] = None,
               index_name: Optional[str] = "LlamaIndexDocumentSections", 
               persist_dir='data/interim/vectorstore/',
               **kwargs) -> VectorStoreIndex:
    """
    Creates or loads a VectorStoreIndex for a given paper.

    This function will either create a new VectorStoreIndex by processing the given paper, or load an existing one from
    the specified directory. If the `reindex` parameter is set to True, the function will reindex the paper even if an
    existing index is found.

    Args:
        paper (pd.Series): The paper to be indexed.
        llm_model (str, optional): The model to use for extraction. Defaults to 'gpt-3.5-turbo'.
        embed_model (str, optional): The model to use for embedding documents. Defaults to 'text-embedding-3-small'.
        weaviate_client (Client, optional): The Weaviate client to use. Defaults to None.
        persist_dir (str, optional): The directory where the index is persisted. Defaults to 'data/interim/vectorstore/'.

    Returns:
        VectorStoreIndex: The created or loaded VectorStoreIndex.
    """
    # Load the existing index
    storage_context = get_storage_context(weaviate_client=weaviate_client,
                                          index_name=index_name,
                                          persist_dir=join(persist_dir, paper.name, embed_model))
    llm = OpenAI(model=llm_model, temperature=0.0, max_retries=3, streaming=True)
    service_context = ServiceContext.from_defaults(llm=llm)

    if not isinstance(storage_context.vector_store, SimpleVectorStore):
        index = VectorStoreIndex.from_vector_store(
            storage_context.vector_store, service_context=service_context)
    else:
        index = load_index_from_storage(storage_context, service_context=service_context)

    return index


def load_index_retriever(paper: pd.Series, similarity_top_k=3,
                         embed_model='text-embedding-3-small',
                         vectorstore_path='data/interim/vectorstore/',
                         retrieval_mode=DEFAULT_RETRIEVAL_MODE,
                         **kwargs):
    persist_dir = join(vectorstore_path, paper.name, embed_model)
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)

    llm = OpenAIEmbedding(model=embed_model,
                          mode=retrieval_mode)
    service_context = ServiceContext.from_defaults(
        embed_model=llm)

    index = load_index_from_storage(storage_context, service_context=service_context)
    retriever = index.as_retriever(similarity_top_k=similarity_top_k, **kwargs)

    return retriever
