from typing import List, Optional
from collections import defaultdict

import argilla as rg
import pandas as pd
from argilla.client.feedback.schemas.remote.records import RemoteFeedbackRecord

from extralit.convert.json_table import json_to_df, is_json_table
from extralit.extraction.models.paper import PaperExtraction
from extralit.extraction.models.schema import SchemaStructure
from extralit.pipeline.ingest.record import get_record_data


def get_paper_extraction_status(references: List[str], schemas: SchemaStructure,
                                paper_dataset: rg.FeedbackDataset,
                                extraction_dataset: rg.FeedbackDataset=None,
                                preprocessing_dataset: rg.FeedbackDataset=None) -> pd.DataFrame:
    assert schemas.singleton_schema is not None, "Document schema must be given in the schemas."
    users = rg.Workspace.from_name(paper_dataset.workspace.name).users
    users_id_to_username = {u.id: u.username for u in users}

    paper_records: List[RemoteFeedbackRecord] = paper_dataset.filter_by(
        metadata_filters=rg.TermsMetadataFilter(
            name='reference',
            values=references)).records

    document_schema = schemas.singleton_schema
    references_data = []
    for record in paper_records:
        reference = record.metadata['reference']
        metadata = record.metadata
        values = get_record_data(record, answers=document_schema.columns,
                                 suggestions=document_schema.columns,
                                 status=['submitted'], include_user_id=True)
        values['reference'] = reference
        values['checked_out'] = users_id_to_username.get(values.pop('user_id', 'NA'), 'NA')
        user_statuses = {users_id_to_username.get(response.user_id, 'NA'): response.status.name \
                         for response in record.responses}
        values[document_schema.name] = user_statuses
        metadata.update(values)
        references_data.append(metadata)

    references_df = pd.DataFrame(references_data).set_index('reference')

    extraction_records: List[RemoteFeedbackRecord] = extraction_dataset.filter_by(
        metadata_filters=rg.TermsMetadataFilter(
            name='reference',
            values=references)).records

    extraction_schemas = schemas.schemas
    extraction_data = defaultdict(dict)
    for record in extraction_records:
        schema_name = record.metadata['type']
        reference = record.metadata['reference']
        user_statuses = {users_id_to_username.get(response.user_id, 'NA'): response.status.name \
                         for response in record.responses}
        extraction_data[reference][schema_name] =  user_statuses
    extraction_df = pd.DataFrame.from_dict(extraction_data, orient='index', )
    extraction_df.index.name = 'reference'

    extraction_status = references_df.join(extraction_df, on='reference')
    return extraction_status

def get_paper_extractions(paper: pd.Series, dataset: rg.FeedbackDataset, schemas: SchemaStructure, answer: str,
                          field: Optional[str] = None,
                          suggestion: Optional[str] = None,
                          users: Optional[List[rg.User]] = None,
                          statuses=['submitted']) -> PaperExtraction:

    reference = paper.name
    records: List[RemoteFeedbackRecord] = dataset.filter_by(
        metadata_filters=rg.TermsMetadataFilter(
            name='reference',
            values=[reference])).records

    extractions = {}
    durations = {}
    updated_at = {}
    inserted_at = {}
    user_id = {}

    for record in records:
        if record.metadata['reference'] != reference:
            continue

        outputs = get_record_data(
            record, fields=field, answers=[answer, 'duration'] if answer else ['duration'],
            suggestions=[suggestion] if suggestion else [],
            users=users,
            include_user_id=True,
            status=statuses,
        )

        if suggestion in outputs:
            table_json = outputs[suggestion]
        elif answer in outputs and is_json_table(outputs[answer]):
            table_json = outputs[answer]
        elif field in outputs and is_json_table(outputs[field]):
            table_json = outputs[field]
        else:
            table_json = None

        for schema in schemas.schemas:
            if schema.name == record.metadata['type']:
                extractions[schema.name] = json_to_df(table_json, schema=schema)
                durations[schema.name] = outputs.get('duration', None)
                updated_at[schema.name] = max([res.updated_at for res in record.responses], default=record.updated_at)
                inserted_at[schema.name] = record.inserted_at
                user_id[schema.name] = outputs.get('user_id', None)

    return PaperExtraction(
        reference=reference, extractions=extractions, schemas=schemas,
        durations=durations, updated_at=updated_at, inserted_at=inserted_at,
        user_id=user_id)
