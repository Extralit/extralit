import re
from os.path import join, exists
from typing import Optional, List, Tuple, Dict, Any, Iterable

import argilla as rg
from extralit.storage.files import FileHandler, StorageType
import pandas as pd
from llama_index.core.schema import Document

from extralit.convert.html_table import html_to_df
from extralit.pipeline.ingest.segment import get_paper_tables
from extralit.preprocessing.document import create_or_load_nougat_segments
from extralit.preprocessing.segment import Segments

INCLUDE_METADATA_KEYS = {'header': True, 'footer': True, 'level': True, 'page_number': True, 'type': True}
EXCLUDE_LLM_METADATA_KEYS = ['type', 'page_number', 'reference', 'level']


def create_nodes(
    paper: pd.Series,
    preprocessing_path='data/preprocessing/nougat/',
    preprocessing_dataset: Optional[rg.FeedbackDataset] = None,
    response_status=['submitted'],
    exclude_llm_metadata_keys=EXCLUDE_LLM_METADATA_KEYS,
    storage_type: StorageType=StorageType.FILE,
    bucket_name: Optional[str]=None,
    **nougat_kwargs,
) -> Tuple[List[Document], List[Document]]:
    """
    Create or load the documents from the paper segments.

    Args:
        paper: pd.Series, required
            A paper from the dataset.
        preprocessing_dataset: rg.FeedbackDataset, default=None
            Manually annotated preprocessing dataset. If given, the TableSegments will be loaded from this dataset.
        response_status: List[str], default=['submitted']
            The response status of the records to consider.
        preprocessing_path: str, default='data/preprocessing/nougat/'
            Path to the preprocessed data.
        ignore_metadata: set, default={'text', 'type', 'level', 'children', 'coordinates', 'source', 'html', 'original',
                                       'probability', 'image'}
            Metadata to exclude from the documents.
        nougat_kwargs: dict
            Additional arguments for the NougatOCR.
    """
    assert len(paper.name) > 0, f"Paper name must be given, given {paper.name}"
    reference = paper.name

    file_handler = FileHandler(preprocessing_path, storage_type, bucket_name)

    if preprocessing_dataset is not None:
        # Load the segments from the manually annotated preprocessing dataset
        text_segments, _, _ = create_or_load_nougat_segments(paper, file_handler=file_handler, **nougat_kwargs)
        table_segments = get_paper_tables(paper, preprocessing_dataset, response_status=response_status)
    else:
        # Load the segments from `nougat` preprocessed data
        texts_path = join(preprocessing_path, reference, 'texts.json')
        tables_path = join(preprocessing_path, reference, 'tables.json')
        text_segments = Segments.parse_raw(file_handler.read_text(texts_path)) if file_handler.exists(texts_path) else Segments()
        table_segments = Segments.parse_raw(file_handler.read_text(tables_path)) if file_handler.exists(tables_path) else Segments()

    extra_metadata = {'reference': reference}
    text_nodes = create_text_nodes(
        text_segments, extra_metadata=extra_metadata, exclude_llm_metadata_keys=exclude_llm_metadata_keys)

    table_nodes = create_table_nodes(
        table_segments, extra_metadata=extra_metadata, exclude_llm_metadata_keys=exclude_llm_metadata_keys)

    return text_nodes, table_nodes


def create_text_nodes(
    text_segments: Segments, extra_metadata: Optional[Dict[str, Any]],
    exclude_llm_metadata_keys: Iterable
) -> List[Document]:
    text_documents = []
    for i, segment in enumerate(text_segments.items):
        if i == 0:
            continue
        elif i == 1:
            title = text_segments[0].text
            segment.text = title + segment.text

        if 'references' in segment.header.lower():
            continue
        elif len(segment.text) < 1000 and 'conflicts of interest' in segment.header.lower() or \
                'acknowledgements' in segment.header.lower() or \
                re.search(r"author.*contributions", segment.header.lower()):
            continue
        elif not segment.text:
            continue

        metadata = segment.dict(include=INCLUDE_METADATA_KEYS)
        if extra_metadata:
            metadata.update(extra_metadata)

        doc = Document(
            id_=segment.id,
            text=segment.text.strip(),
            type=segment.type,
            metadata=metadata,
            relationships=segment.relationships,
            excluded_embed_metadata_keys=exclude_llm_metadata_keys,
            excluded_llm_metadata_keys=exclude_llm_metadata_keys)
        text_documents.append(doc)

    return text_documents


def create_table_nodes(
    table_segments: Segments, extra_metadata: Optional[Dict[str, Any]], exclude_llm_metadata_keys: Iterable
) -> List[Document]:
    table_documents = []
    for segment in table_segments.items:
        if not segment.html:
            continue

        try:
            df = html_to_df(segment.html, convert_spanning_rows=True)
        except Exception as e:
            print(f"Failed to convert HTML to DataFrame: {e}")
            continue

        assert df.columns.nlevels == 1, f"MultiIndex columns are not supported, given {df.columns}"
        metadata = segment.dict(include=INCLUDE_METADATA_KEYS)
        if extra_metadata:
            metadata.update(extra_metadata)
        metadata['columns'] = df.columns.tolist()

        doc = Document(
            id_=segment.id,
            text=df.to_json(orient='index'),
            type=segment.type,
            metadata=metadata,
            relationships=segment.relationships,
            excluded_embed_metadata_keys=exclude_llm_metadata_keys,
            excluded_llm_metadata_keys=exclude_llm_metadata_keys)
        table_documents.append(doc)

    return table_documents
