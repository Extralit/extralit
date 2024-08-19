import logging
import os
import warnings
from os.path import join, exists
from typing import Tuple, Dict, Optional, List, Union

import pandas as pd
import pandera as pa
from langfuse.model import TextPromptClient
from llama_index.core import VectorStoreIndex, PromptTemplate, Response
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator, FilterCondition, )
from pydantic.v1 import BaseModel

from extralit.extraction.models.paper import PaperExtraction
from extralit.extraction.models.response import ResponseResult, ResponseResults
from extralit.extraction.models.schema import SchemaStructure
from extralit.extraction.prompts import create_extraction_prompt, \
    create_completion_prompt, DEFAULT_EXTRACTION_PROMPT_TMPL
from extralit.extraction.schema import get_extraction_schema_model
from extralit.extraction.utils import convert_response_to_dataframe, generate_reference_columns
from extralit.extraction.vector_index import load_index
from extralit.schema.references.assign import assign_unique_index, get_prefix

_LOGGER = logging.getLogger(__name__)


def query_rag_index(
        prompt: str,
        index: VectorStoreIndex,
        output_cls=BaseModel,
        similarity_top_k=20,
        filters: Optional[MetadataFilters] = None,
        response_mode="compact",
        text_qa_template=DEFAULT_EXTRACTION_PROMPT_TMPL,
        **kwargs,
) -> Response:
    warnings.filterwarnings('ignore', module='pydantic')

    query_engine = index.as_query_engine(
        output_cls=output_cls,
        response_mode=response_mode,
        similarity_top_k=similarity_top_k,
        filters=filters,
        text_qa_template=text_qa_template,
        **kwargs,
    )

    obs_response = query_engine.query(prompt)

    return obs_response


def extract_schema(
        schema: pa.DataFrameSchema,
        extractions: PaperExtraction,
        index: VectorStoreIndex,
        include_fields: Optional[List[str]] = None,
        headers: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        similarity_top_k=20,
        system_prompt: Optional[Union[PromptTemplate, TextPromptClient]] = DEFAULT_EXTRACTION_PROMPT_TMPL,
        user_prompt: Optional[str] = None,
        verbose=False,
        **kwargs,
    ) -> Tuple[pd.DataFrame, ResponseResult]:
    """
    Extract a complete table based on schema using the RAG on a paper.
    Args:
        schema (pa.DataFrameSchema): The schema to extract.
        extractions (PaperExtraction): The extractions from the paper.
        index (VectorStoreIndex): The index to use for the extraction.
        similarity_top_k (int): The number of similar documents to retrieve. Defaults to 20.
        include_fields (Optional[List[str]]): A list of column names to include in the Pydantic model. Defaults to None.
        headers (Optional[List[str]]): The headers to filter the documents by. Defaults to None.
        system_prompt (PromptTemplate): The text QA template to use. Defaults to the default text QA template.
        verbose (Optional[int]): The verbosity level. Defaults to None.
        **kwargs (Dict): Additional keyword arguments to pass to the `query_rag_llm` and `as_query_engine` function.
            text_qa_template (PromptTemplate): The text QA template to use. Defaults to the default text QA template.
            vector_store_query_mode (str): The vector store query mode. Defaults to "hybrid".

    Returns:
        Tuple[pd.DataFrame, ResponseResult]: The extracted DataFrame and the ResponseResult.
    """

    if schema.name in extractions.extractions:
        prompt = create_completion_prompt(schema, extractions, include_fields=include_fields, extra_prompt=user_prompt)
    else:
        prompt = create_extraction_prompt(schema, extractions, )

    output_cls = get_extraction_schema_model(
        schema, include_fields=include_fields, exclude_fields=['reference'], top_class=schema.name + 's', lower_class=schema.name,
        validate_assignment=False)

    filters = MetadataFilters(
        filters=[MetadataFilter(key="reference", value=extractions.reference, operator=FilterOperator.EQ)],
        condition=FilterCondition.AND,
    )
    if headers:
        filters.filters.append(
            MetadataFilter(key="header", value=headers, operator=FilterOperator.IN)
        )
    if types:
        filters.filters.append(
            MetadataFilter(key="type", value=types, operator=FilterOperator.IN)
        )

    if verbose:
        _LOGGER.info(f'Filters {filters.__repr__()}')

    if isinstance(system_prompt, TextPromptClient):
        system_prompt = PromptTemplate(system_prompt.get_langchain_prompt())
    elif isinstance(system_prompt, PromptTemplate):
        pass
    else:
        _LOGGER.warning(f"Invalid system_prompt type: {type(system_prompt)}, reverting to "
                        f"DATA_EXTRACTION_SYSTEM_PROMPT_TMPL.")
        system_prompt = DEFAULT_EXTRACTION_PROMPT_TMPL

    response = query_rag_index(
        prompt, index=index, output_cls=output_cls,
        similarity_top_k=similarity_top_k, filters=filters,
        text_qa_template=system_prompt, response_mode="compact", **kwargs)

    df = convert_response_to_dataframe(response)
    df = generate_reference_columns(df, schema)
    try:
        response = ResponseResult(**response.__dict__)
    except Exception as e:
        _LOGGER.error(f"Failed to create ResponseResult: {e}")
        response = ResponseResult()

    return df, response


def extract_paper(
        paper: pd.Series,
        schema_structure: SchemaStructure,
        index: VectorStoreIndex = None,
        prompt: str = "default",
        llm_models: Union[List[str], str]=["gpt-4o", 'gpt-4-turbo'],
        embed_model:str='text-embedding-ada-002',
        index_kwargs: Dict = None,
        interim_path='data/interim/',
        load_only=False,
        verbose: int = 0,
) -> Tuple[PaperExtraction, ResponseResults]:

    reference = paper.name
    if isinstance(llm_models, str):
        llm_models = [llm_models]

    ### Load interim results ###
    interim_save_dir = join(interim_path, llm_models[0], reference)
    if load_only and exists(interim_save_dir):
        if not exists(interim_save_dir):
            raise FileNotFoundError(f"Interim save directory does not exist: {interim_save_dir}")
        with open(join(interim_save_dir, 'responses.json'), 'r') as file:
            responses = ResponseResults.parse_raw(file.read())

        extractions = PaperExtraction(
            extractions={k: v.response.to_df() for k, v in responses.items.items()},
            schemas=schema_structure,
            reference=reference
        )
        return extractions, responses

    ### Create or load the index ###
    if index is None:
        index = load_index(paper, llm_model=llm_models[0], embed_model=embed_model, **(index_kwargs or {}))
    assert index.service_context.llm.model == llm_models[0], \
        f"LLM model mismatch: {index.service_context.llm.model} != {llm_models[0]}"

    extractions = PaperExtraction(
        extractions={}, schemas=schema_structure, reference=reference)
    responses = ResponseResults(
        items={}, docs_metadata={id: doc.metadata for id, doc in index.docstore.docs.items()})

    ### Extract entities ###
    for schema_name in extractions.schemas.ordering:
        schema = extractions.schemas[schema_name]

        df = extract_schema_with_fallback(schema=schema, extractions=extractions, index=index, responses=responses,
                                          models=llm_models, verbose=verbose)

        if schema.index and schema.index.name:
            df = assign_unique_index(df, schema, index_name=schema.index.name, prefix=get_prefix(schema), n_digits=2)
        df = df.drop_duplicates()

        extractions.extractions[schema_name] = df

    ### Save interim results ###
    try:
        os.makedirs(interim_save_dir, exist_ok=True)
        with open(join(interim_save_dir, 'responses.json'), 'w') as file:
            file.write(responses.json())
    except Exception as e:
        _LOGGER.error(f"Interim save responses: {e}")

    return extractions, responses


def extract_schema_with_fallback(schema: pa.DataFrameSchema, extractions: PaperExtraction, index: VectorStoreIndex,
                                 responses: ResponseResults, models: List[str], verbose: Optional[int]=0, **kwargs) -> pd.DataFrame:
    for model in models:
        try:
            index.service_context.llm.model = model
            df, responses[schema.name] = extract_schema(schema=schema, extractions=extractions, index=index, **kwargs)
            return df
        except Exception as e:
            _LOGGER.log(logging.WARNING, f"Error {schema.name} ({model}): {e}")

            if verbose >= 2:
                raise e

    return pd.DataFrame()


