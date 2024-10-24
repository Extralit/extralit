import logging
from typing import Optional, Union, List, Literal
from uuid import UUID

import pandas as pd
from fastapi import FastAPI, Depends, Body, Query, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langfuse.llama_index import LlamaIndexCallbackHandler
from langfuse.model import ChatPromptClient
from langfuse.utils.base_callback_handler import LangfuseBaseCallbackHandler
from llama_index.core.chat_engine.types import ChatMode
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from minio import Minio
from weaviate import WeaviateClient

import argilla as rg
from extralit.convert.json_table import json_to_df
from extralit.extraction.extraction import extract_schema
from extralit.extraction.models.paper import PaperExtraction
from extralit.extraction.models.schema import SchemaStructure
from extralit.extraction.prompts import DEFAULT_CHAT_PROMPT_TMPL, CHAT_SYSTEM_PROMPT
from extralit.extraction.query import get_nodes_metadata, vectordb_contains_any
from extralit.extraction.vector_index import create_vector_index, load_index
from extralit.server.context.files import get_minio_client
from extralit.server.context.llamaindex import get_langfuse_callback
from extralit.server.context.vectordb import get_weaviate_client
from extralit.server.models.extraction import ExtractionRequest, ExtractionResponse
from extralit.server.models.segments import SegmentsResponse

_LOGGER = logging.getLogger(__name__)
app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://argilla-server"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

weaviate_client: WeaviateClient = None
minio_client: Minio = None


@app.on_event("startup")
async def startup():
    global weaviate_client, minio_client
    if weaviate_client is None:
        weaviate_client = get_weaviate_client()
    if minio_client is None:
        minio_client = get_minio_client()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/schemas/{workspace}")
async def schemas(
    workspace: str = 'itn-recalibration',
):
    ss = SchemaStructure.from_s3(workspace_name=workspace, minio_client=minio_client)
    return ss.ordering


@app.get("/chat", status_code=status.HTTP_200_OK, response_class=StreamingResponse)
async def chat(
    query: str = Query(...),
    workspace: str = Query(...),
    reference: str = Query(...),
    similarity_top_k: int = Query(5, alias="k"),
    chat_mode: ChatMode = Query(ChatMode.BEST),
    llm_model: str = Query("gpt-3.5-turbo"),
    username: Optional[Union[str, UUID]] = None,
    prompt_template: str = "chat",
    langfuse_callback: Optional[LlamaIndexCallbackHandler] = Depends(get_langfuse_callback),
):
    index = load_index(paper=pd.Series(name=reference), llm_model=llm_model, embed_model='text-embedding-3-small',
                       weaviate_client=weaviate_client, index_name="LlamaIndexDocumentSections")

    if not vectordb_contains_any(reference, weaviate_client=weaviate_client, index_name="LlamaIndexDocumentSections"):
        raise HTTPException(status_code=404, detail=f"No context found for reference: {reference}")

    try:
        if isinstance(langfuse_callback, LlamaIndexCallbackHandler):
            langfuse_callback.set_trace_params(
                name=f"chat-{reference}",
                user_id=username,
                session_id=reference,
                tags=[workspace, reference, 'chat'],
            )
    except Exception as e:
        _LOGGER.error(f"Failed to set trace params: {e}")

    # Get the system prompt
    try:
        chat_prompts: ChatPromptClient = langfuse_callback.langfuse.get_prompt(prompt_template, cache_ttl_seconds=3000)
        system_prompt = chat_prompts.prompt[0]['content']
    except Exception as e:
        _LOGGER.error(f"Failed to get system prompt: {e}")
        system_prompt = None

    filters = MetadataFilters(
        filters=[MetadataFilter(key="reference", value=reference, operator=FilterOperator.EQ)],
    )

    query_engine = index.as_chat_engine(
        chat_mode=chat_mode,
        vector_store_query_mode="hybrid",
        alpha=0.25,
        similarity_top_k=similarity_top_k,
        filters=filters,
        system_prompt=system_prompt or CHAT_SYSTEM_PROMPT,
        text_qa_template=DEFAULT_CHAT_PROMPT_TMPL,
    )

    response = query_engine.stream_chat(query)
    return StreamingResponse(response.response_gen, media_type="text/event-stream")


@app.post("/extraction", status_code=status.HTTP_201_CREATED, response_model=ExtractionResponse)
async def extraction(
    *,
    extraction_request: ExtractionRequest = Body(...),
    workspace: str = Query(...),
    model: str = "gpt-4o",
    similarity_top_k: int = 8,
    username: Optional[Union[str, UUID]] = None,
    prompt_template: str = "completion",
    langfuse_callback: Optional[LlamaIndexCallbackHandler] = Depends(get_langfuse_callback),
):
    print(extraction_request)
    schema_structure = SchemaStructure.from_s3(workspace_name=workspace, minio_client=minio_client)
    schema = schema_structure[extraction_request.schema_name]

    extraction_dfs = {}
    for schema_name, extraction_dict in extraction_request.extractions.items():
        schema = schema_structure[schema_name]
        extraction_dfs[schema.name] = json_to_df(extraction_dict, schema=schema)

    extractions = PaperExtraction(
        reference=extraction_request.reference,
        extractions=extraction_dfs,
        schemas=schema_structure
    )

    # Get the system prompt
    try:
        system_prompt = langfuse_callback.langfuse.get_prompt(prompt_template, cache_ttl_seconds=3000, max_retries=0)
    except Exception as e:
        _LOGGER.error(f"Failed to get system prompt: {e}")
        system_prompt = None

    try:
        if isinstance(langfuse_callback, LlamaIndexCallbackHandler):
            langfuse_callback.set_trace_params(
                name=f"extract-{extraction_request.reference}",
                user_id=username,
                session_id=extraction_request.reference,
                tags=[workspace, extraction_request.reference, extraction_request.schema_name, 'partial-extraction'],
            )
    except Exception as e:
        _LOGGER.error(f"Failed to set trace params: {e}")

    ### Create or load the index ###
    try:
        index = load_index(paper=pd.Series(name=extraction_request.reference), llm_model=model,
                           embed_model='text-embedding-3-small', weaviate_client=weaviate_client,
                           index_name="LlamaIndexDocumentSections")
    except Exception as e:
        _LOGGER.error(f"Failed to create or load the index: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to create an extraction request: {e}')

    if extraction_request.headers and len(extraction_request.headers) > similarity_top_k:
        similarity_top_k = len(extraction_request.headers)

    try:
        ### Extract entities ###
        df, rag_response = extract_schema(schema=schema, extractions=extractions, index=index,
                                          include_fields=extraction_request.columns, headers=extraction_request.headers,
                                          types=extraction_request.types, similarity_top_k=similarity_top_k,
                                          system_prompt=system_prompt, user_prompt=extraction_request.prompt,
                                          vector_store_query_mode="hybrid")

        if not isinstance(df, pd.DataFrame) or df.empty:
            if rag_response.source_nodes is None or len(rag_response.source_nodes) == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f'There were no context selected due to stringent filters. Please modify your <br>'
                           f'filters: {dict(headers=extraction_request.headers, types=extraction_request.types)}')
            raise HTTPException(status_code=404,
                                detail="No extraction found with the selected context and your query.")

        response = ExtractionResponse.parse_raw(df.to_json(orient='table'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if isinstance(langfuse_callback, LangfuseBaseCallbackHandler):
        langfuse_callback.flush()

    return response


@app.get("/segments/", status_code=status.HTTP_200_OK, response_model=SegmentsResponse)
async def segments(
    *,
    workspace: str = Query(...),
    reference: str = Query(...),
    types: Optional[List[Literal['text', 'table', 'figure']]] = Query(None),
    username: Optional[Union[str, UUID]] = Query(None),
    limit=100,
):
    filters = []

    if types:
        filters.append(MetadataFilter(key="type", value=types, operator=FilterOperator.NE))

    filters.append(MetadataFilter(key="reference", value=reference, operator=FilterOperator.EQ))

    entries = get_nodes_metadata(
        weaviate_client=weaviate_client, filters=MetadataFilters(filters=filters),
        limit=limit, index_name="LlamaIndexDocumentSections",
    )

    return SegmentsResponse(items=entries)


@app.post("/index/", status_code=status.HTTP_201_CREATED)
async def create_index(
    workspace: str = Query(...),
    reference: str = Query(...),
    preprocessing_dataset: str = Query(None),
    embed_model: str = Query("text-embedding-3-small"),
    username: Optional[Union[str, UUID]] = Query(None),
):
    try:
        preprocessing_dataset = rg.FeedbackDataset.from_argilla(name=preprocessing_dataset, workspace=workspace) \
            if preprocessing_dataset else None
    except Exception as e:
        preprocessing_dataset = None

    try:
        index = create_vector_index(
            paper=pd.Series(name=reference),
            weaviate_client=weaviate_client,
            preprocessing_dataset=preprocessing_dataset,
            preprocessing_path="data/preprocessing/nougat/",
            index_name="LlamaIndexDocumentSections",
            embed_model=embed_model,
        )

        return index.index_id
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
