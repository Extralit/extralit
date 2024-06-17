import logging
from typing import Dict, List

import argilla as rg
import pandas as pd
import pandera as pa
from argilla.client.feedback.dataset.remote.dataset import RemoteFeedbackDataset
from llama_index.embeddings.openai import OpenAIEmbedding
from tqdm import tqdm

from extralit.convert.json_table import df_to_json
from extralit.extraction.models.paper import PaperExtraction
from extralit.extraction.models.response import ResponseResults
_LOGGER = logging.getLogger(__name__)


def create_extraction_records(paper_extractions: Dict[str, PaperExtraction],
                              responses: Dict[str, ResponseResults],
                              papers: pd.DataFrame,
                              dataset: RemoteFeedbackDataset = None) \
        -> List[rg.FeedbackRecord]:
    """
    Push the extractions to the Argilla (Preprocessing) FeedbackDataset.
    """
    records = []
    for ref, extractions in paper_extractions.items():
        paper = papers.loc[[ref]].iloc[0]

        if dataset is not None:
            assert isinstance(dataset, RemoteFeedbackDataset)
            if isinstance(paper.file_path, str):
                doc = dataset.add_document(
                    rg.Document.from_file(paper.file_path, reference=ref, pmid=paper.pmid, doi=paper.doi,
                                          id=paper.get('id')))
            else:
                raise Exception(f'Unable to load document for {ref}')
        else:
            doc = rg.Document(file_name='/')

        ### metadata ###
        metadata = {
            'reference': ref,
            **({"pmid": doc.pmid} if isinstance(doc.pmid, str) else {}),
            **({"doc_id": str(doc.id)} if doc.id is not None else {}),
        }

        schema_order = extractions.schemas.ordering
        for schema_name, extraction in extractions.items():
            schema = extractions.schemas[schema_name]
            if extraction is None or extraction.empty:
                _LOGGER.warning(f'No {schema_name} extraction for {ref}, generating an empty table.')
                extraction = generate_empty_extraction(schema, size=2)

            ### fields ###
            fields = {
                'extraction': df_to_json(
                    extraction, schema, drop_columns=['publication_ref', 'Group'],
                    metadata={'reference': ref}),
            }

            ref_url = f'dataset/{dataset.id}/annotation-mode'
            nav_df = pd.DataFrame(
                [[
                    f'[Step {i}]({ref_url}?_page={i}&_metadata=reference.{ref})' \
                        if step != schema_name else f'Step {i} (here)' \
                    for i, step in enumerate(schema_order, start=1)]],
                columns=schema_order,
                index=pd.Index(['Navigate to']))
            fields['metadata'] = f'Paper: {ref}\n' + nav_df.to_markdown(index=True)

            # Retrieve most relevant context
            if ref in responses and schema_name in responses[ref].items:
                nodes_df = responses[ref].items[schema_name].get_nodes_info()
                nodes_df.drop(columns=nodes_df.columns.difference(['relevance', 'header', 'page_number', 'text']),
                              errors='ignore', inplace=True)
                # nodes_df['page_number'] = nodes_df['page_number'].map(lambda x: f"[Page {x}](#page_number.{x})" if x else None)
                fields['context'] = nodes_df \
                    .style.background_gradient(axis=1, subset=['relevance'], cmap='RdYlGn') \
                    .to_html(index=False, na_rep='')

            # ### suggestions ###
            # suggestions = [
            #     {
            #         "question_name": "context-relevant",
            #         "value": headers,
            #         "type": "selection",
            #     },
            # ]

            record = rg.FeedbackRecord(
                fields=fields,
                # suggestions=suggestions if len(headers) else [],
                metadata={**metadata, 'type': schema_name, },
            )
            records.append(record)

    return records


def create_publication_records(
        papers: pd.DataFrame,
        schema: pa.DataFrameSchema,
        embed_model='text-embedding-3-large',
        dataset: RemoteFeedbackDataset = None) \
        -> List[rg.FeedbackRecord]:
    """
    Push the publications to the Argilla (Preprocessing) FeedbackDataset.
    """
    records = []
    question_names = [q.name for q in dataset.questions]

    embed_models = {}
    if embed_model:
        for vectors_setting in dataset.vectors_settings:
            embed_models[vectors_setting.name] = OpenAIEmbedding(
                model=embed_model, dimensions=vectors_setting.dimensions or 1024)

    for _, paper in tqdm(papers.iterrows()):
        if dataset is not None:
            assert isinstance(dataset, RemoteFeedbackDataset)
            if isinstance(paper.file_path, str):
                doc = dataset.add_document(
                    rg.Document.from_file(paper.file_path, reference=paper.name, pmid=paper.pmid, doi=paper.doi,
                                          id=paper.id if hasattr(paper, 'id') else None))
            else:
                raise Exception(f'Unable to load document for {paper.name}')
        else:
            doc = rg.Document(file_name='/')

        metadata = {
            'reference': paper.name,
            **({"pmid": doc.pmid} if isinstance(doc.pmid, str) else {}),
            **({"doc_id": str(doc.id)} if doc.id is not None else {}),
        }

        publication_metadata = {
            'title': paper.title,
            'authors': ', '.join([f"{author.get('first_name')} {author.get('last_name')}".strip() \
                                  for author in paper.authors]),
            'journal': paper.source,
            'year': paper.year,
            'doi': paper.doi,
            'pmid': paper.pmid,
            'keywords': paper.keywords,
            'collections': paper.collections,
        }
        metadata.update(publication_metadata)
        publication_metadata = pd.Series(publication_metadata, name=paper.name)

        fields = {
            'metadata': publication_metadata.to_frame().to_html(index=True),
            'abstract': paper.abstract or "",
        }

        vectors = {
            name: model.get_text_embedding(fields[name]) \
            for name, model in embed_models.items() \
            if name in fields and fields[name].strip()
        }

        # Create suggestions
        try:
            agent = paper['Check_out_by'].strip() or None
        except AttributeError:
            agent = None
        suggestions = []
        for field in schema.columns:
            if field in question_names and field in paper and paper[field] is not None:
                suggestions.append({
                    "question_name": field.lower(),
                    "value": str(paper[field]),
                    "type": "human",
                    "agent": agent,
                })

        record = rg.FeedbackRecord(
            fields=fields,
            metadata={k: v for k, v in metadata.items() if not pd.isna(v)},
            suggestions=suggestions,
            vectors=vectors,
        )
        records.append(record)

    return records


def generate_empty_extraction(schema: pa.DataFrameSchema, size=1) -> pd.DataFrame:
    default_value = ['NA'] * size
    df = pd.DataFrame.from_dict({col: default_value \
                                 for i, col in enumerate(schema.columns) if i < 5})

    if isinstance(schema.index, pa.MultiIndex):
        index_names = []
        index_prefixes = []
        for index in schema.index.indexes:
            index_names.append(index.name)
            str_startswith_check = next(check for check in index.checks if check.name == 'str_startswith')
            index_prefixes.append(str_startswith_check.statistics['string'])
        index = pd.MultiIndex.from_tuples(
            [tuple(f'{prefix}{i+1}' for prefix in index_prefixes) for i in range(size)],
            names=index_names)
    else:
        str_startswith_check = next(check for check in schema.index.checks if check.name == 'str_startswith')
        prefix = str_startswith_check.statistics['string']
        index = pd.Index([f'{prefix}{i+1}' for i in range(size)], name=schema.index.name)

    df = df.set_index(index)

    return df
