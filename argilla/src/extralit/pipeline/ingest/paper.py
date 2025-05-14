from typing import List, Optional
from collections import defaultdict

import argilla as rg
import pandas as pd

from extralit.convert.json_table import json_to_df, is_json_table
from extralit.extraction.models.paper import PaperExtraction
from extralit.extraction.models.schema import SchemaStructure
from extralit.pipeline.ingest.record import get_record_data


def get_paper_extraction_status(references: List[str], schemas: SchemaStructure,
                              paper_dataset: rg.Dataset,
                              extraction_dataset: rg.Dataset = None,
                              preprocessing_dataset: rg.Dataset = None) -> pd.DataFrame:
    assert schemas.singleton_schema is not None, "Document schema must be given in the schemas."

    # Get workspace users
    workspace = paper_dataset.workspace
    users = workspace.users
    users_id_to_username = {u.id: u.username for u in users}

    # Query paper records
    query = rg.Query(
        filter=rg.Filter([
            ("metadata.reference", "in", references)
        ])
    )
    paper_records = list(paper_dataset.records(query=query))

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
        user_statuses = {users_id_to_username.get(response.user_id, 'NA'): response.status
                        for responses in record.responses.values()
                        for response in responses}
        values[document_schema.name] = user_statuses
        metadata.update(values)
        references_data.append(metadata)

    references_df = pd.DataFrame(references_data).set_index('reference')

    if extraction_dataset:
        # Query extraction records
        query = rg.Query(
            filter=rg.Filter([
                ("metadata.reference", "in", references)
            ])
        )
        extraction_records = list(extraction_dataset.records(query=query))

        extraction_schemas = schemas.schemas
        extraction_data = defaultdict(dict)
        for record in extraction_records:
            schema_name = record.metadata['type']
            reference = record.metadata['reference']
            user_statuses = {users_id_to_username.get(response.user_id, 'NA'): response.status
                           for responses in record.responses.values()
                           for response in responses}
            extraction_data[reference][schema_name] = user_statuses
        extraction_df = pd.DataFrame.from_dict(extraction_data, orient='index')
        extraction_df.index.name = 'reference'

        extraction_status = references_df.join(extraction_df, on='reference')
        return extraction_status

    return references_df


def get_paper_extractions(paper: pd.Series, dataset: rg.Dataset, schemas: SchemaStructure, answer: str,
                         field: Optional[str] = None,
                         suggestion: Optional[str] = None,
                         users: Optional[List[rg.User]] = None,
                         statuses=['submitted']) -> PaperExtraction:

    reference = paper.name

    # Query records
    query = rg.Query(
        filter=rg.Filter([
            ("metadata.reference", "==", reference)
        ])
    )
    records = list(dataset.records(query=query))

    extractions = {}
    durations = {}
    updated_at = {}
    inserted_at = {}
    user_id = {}

    for record in records:
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
                # Get latest update timestamp from all responses
                response_timestamps = [response.updated_at
                                    for responses in record.responses.values()
                                    for response in responses]
                updated_at[schema.name] = max(response_timestamps) if response_timestamps else record.updated_at
                inserted_at[schema.name] = record.inserted_at
                user_id[schema.name] = outputs.get('user_id', None)

    return PaperExtraction(
        reference=reference, extractions=extractions, schemas=schemas,
        durations=durations, updated_at=updated_at, inserted_at=inserted_at,
        user_id=user_id)
