import json
import logging
from typing import Optional, Dict

import argilla as rg
import pandera as pa

__all__ = ['update_table_schema', 'update_record_table_schema']


def update_table_schema(table_json_str: str, schema_json: Dict, reference: str, schema_name: str) -> str:
    table_json = json.loads(table_json_str)

    if reference:
        table_json['reference'] = reference

    table_json['validation'] = schema_json

    return json.dumps(table_json)


def update_record_table_schema(record: rg.FeedbackRecord, schema: pa.DataFrameSchema,
                               field: str, answer: Optional[str] = None) -> rg.FeedbackRecord:
    reference = record.metadata.get('reference')
    schema_name = record.metadata['type']
    assert schema_name == schema.name, f"Schema name `{schema_name}` does not match the schema provided."

    schema_json = json.loads(schema.to_json())

    try:
        record.fields[field] = update_table_schema(record.fields[field], schema_json=schema_json, reference=reference,
                                                   schema_name=schema_name)
    except Exception as e:
        logging.error(
            f'Unable to update {schema_name} schema for field `{field}` or answer `{answer}` in {record.metadata["reference"]}. \n{e}')
        raise e

    ### Update tables in responses (doesn't yet update in argilla backend)
    # for i, response in enumerate(record.responses):
    #     if answer not in response.values:
    #         continue
    #     elif not is_json_table(response.values[answer].value):
    #         continue
    #
    #     record.responses[i].values[answer].value = update_table_schema(
    #         response.values[answer].value, schema_json=schema_json, reference=reference,
    #         schema_name=schema_name)

    return record
