import json
import logging
from typing import Dict, Any, List

import pandas as pd
from json_repair import repair_json


def list_to_str(x):
    if isinstance(x, (list, tuple)):
        if len(x) >= 1:
            return ', '.join(x)
        elif len(x) == 0:
            return None
    return x


def to_df(model, *args, **kwargs) -> pd.DataFrame:
    items = model.dict(exclude_none=True)['items']
    dtypes = generate_dtypes(model, subset=items[0].keys()) if len(items) > 0 else {}
    df = pd.DataFrame(items).astype(dtypes, errors='ignore')

    # Convert any list values to string delimited by comma
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].map(list_to_str)

    zero_value_columns = [col for col in df.columns if df[col].eq(0).all() or df[col].isna().all()]
    df = df.drop(columns=zero_value_columns)

    return df


def generate_dtypes(model, subset: List[str] = None) -> Dict[str, Any]:
    type_mapping = {
        int: 'Int64',
        float: 'Float32',
        str: 'string',
        bool: 'boolean',
    }

    dtypes = {}
    if hasattr(model, 'items') and isinstance(model.items, list) and len(model.items) > 0:
        item_model = model.items[0]
    else:
        item_model = model

    if not hasattr(item_model, '__fields__'):
        return {}

    for name, field in item_model.__fields__.items():
        if subset and name not in subset:
            continue

        python_type = field.outer_type_
        pandas_dtype = type_mapping.get(python_type)
        if pandas_dtype is not None:
            dtypes[name] = pandas_dtype

    return dtypes


def heal_json(json_string: str, return_on_failure='{}') -> str:
    try:
        # Try to parse the JSON string
        json.loads(json_string)
        return json_string

    except json.JSONDecodeError:
        logging.warning(f"Attempting to fix broken JSON: ...{json_string[-100:]}".replace('\n', ''))
        try:
            healed_json_string = repair_json(json_string)
            # Check if the healed JSON string is valid
            json.loads(healed_json_string)
            return healed_json_string
        except Exception as e:
            logging.info(f"Failed to repair JSON: {e}. Returning '{return_on_failure}'.")
            return return_on_failure
