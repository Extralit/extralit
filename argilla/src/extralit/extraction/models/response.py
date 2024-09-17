from typing import Union, List, Dict, Any, Optional
from pydantic.v1 import BaseModel, validator, Field
from typing_extensions import TypedDict

import pandas as pd
import tiktoken
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import TextNode

from extralit.extraction.staging import to_df


class BaseModelForLlamaIndexResponse(BaseModel):
    items: List[Dict[str, Any]]

    def to_df(self, *args, **kwargs) -> pd.DataFrame:
        return to_df(self, *args, **kwargs)


class SourceNode(TypedDict):
    node: Union[TextNode, Dict[str, Union[str, Dict[str, str]]]]
    score: Optional[float]

    class Config:
        arbitrary_types_allowed = True


class ResponseResult(BaseModel):
    response: Optional[BaseModelForLlamaIndexResponse]
    source_nodes: Optional[List[SourceNode]]
    metadata: Optional[Dict[str, Dict[str, Any]]]

    @validator('source_nodes', pre=True)
    def parse_source_nodes(cls, v):
        return [dict(node) for node in v]

    def get_nodes_info(self,
                       count_tokens=False,
                       tokenizer_model='text-embedding-3-small',
                       max_char_len=25, header_doc_id_map: Optional[Dict[str, str]] = None) \
            -> pd.DataFrame:
        if count_tokens:
            tiktoken_encoder = tiktoken.get_encoding(tokenizer_model)

        nodes_dict = {}
        for i, source_node in enumerate(self.source_nodes, start=1):
            node, score = source_node['node'], source_node['score']
            text, metadata = node['text'], node['metadata']
            tokens = len(tiktoken_encoder.encode(text)) if count_tokens and text else None

            if header_doc_id_map:
                header = metadata.get('header')
                if header in header_doc_id_map:
                    metadata['doc_id'] = header_doc_id_map[header]

            nodes_dict[i] = {
                'doc_id': node['id_'],
                'relevance': score,
                **metadata,
                'text': text[:max_char_len].replace('\n', '') + ('...' if len(text) > max_char_len else ''),
            }
            if count_tokens:
                nodes_dict[i]['n_tokens'] = tokens

        context_df = pd.DataFrame.from_dict(nodes_dict, orient='index')

        return context_df

    class Config:
        arbitrary_types_allowed = True

class ResponseResults(BaseModel):
    items: Dict[str, ResponseResult] = Field(default_factory=dict)
    docs_metadata: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Metadata for all nodes in the RAG index")

    def init_docs_from_index(self, index: VectorStoreIndex, reference: str):
        if type(index.vector_store).__name__ == 'WeaviateVectorStore':
            from extralit.extraction.query import get_nodes_metadata
            
            weaviate_client = index.vector_store.client

            results = get_nodes_metadata(weaviate_client, index_name=index.vector_store.index_name,
                                         properties=['reference', 'header', 'doc_id', 'page_number'],
                                         filters={'reference': reference})
            docs_metadata = {result['doc_id']: result for result in results}
        else:
            docs_metadata = {id: doc.metadata for id, doc in index.docstore.docs.items()}

        self.docs_metadata = docs_metadata

    def get_nodes_info(self, schema_name=None, **kwargs) -> pd.DataFrame:
        if schema_name:
            return self.items[schema_name].get_nodes_info(**kwargs)
        elif not schema_name and not self.docs_metadata:
            raise ValueError("No metadata available to extract nodes from, run `init_docs_from_index` first.")

        df = pd.DataFrame.from_dict(self.docs_metadata, orient='index')
        df.index.name = 'doc_id'
        return df.reset_index(drop=df.index.name in df.columns)

    def get_ranked_nodes(self, schema_name: str, include_all_nodes=True) -> pd.DataFrame:
        header_doc_id_map = {doc['header']: doc['doc_id'] for doc in self.docs_metadata.values()}
        selected_nodes = self.items[schema_name].get_nodes_info(count_tokens=False, header_doc_id_map=header_doc_id_map)
        if include_all_nodes:
            all_nodes = self.get_nodes_info()
            ranked_nodes = pd.concat([selected_nodes, all_nodes]).drop_duplicates(subset=['header'])
        else:
            ranked_nodes = selected_nodes

        return ranked_nodes

    def __getitem__(self, key):
        return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value

    class Config:
        arbitrary_types_allowed = True