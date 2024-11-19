import logging
from typing import Union, List, Dict

import pandas as pd
import pandera as pa
from llama_index.core import Response

_LOGGER = logging.getLogger(__name__)

def convert_response_to_dataframe(response: Response) -> pd.DataFrame:
    try:
        df: pd.DataFrame = response.response.to_df()
    except AttributeError as ae:
        _LOGGER.error(
            f"""Failed to convert response to DataFrame: {ae}
            Response: {response.response}
            Source nodes: {len(response.source_nodes)}
            """)
        df = pd.DataFrame()
    return df


def generate_reference_columns(df: pd.DataFrame, schema: pa.DataFrameSchema):
    if schema.index is None:
        return df

    index_names = [index.name.lower() for index in schema.index.indexes] \
        if hasattr(schema.index, 'indexes') else []
    for index_name in index_names:
        if index_name not in df.columns:
            df[index_name] = 'NOTMATCHED'
    if index_names:
        df = df.set_index(index_names, verify_integrity=False)
    return df


def filter_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop columns that have the same value in all rows.
    """
    if len(df) > 1:
        return df.dropna(axis='columns', how='all').loc[:, (df.astype(str).nunique() > 1)]
    else:
        return df


def stringify_lists(obj: Union[List, Dict], conjunction='or') -> str:
    if isinstance(obj, dict):
        items = list(obj)
    elif isinstance(obj, list):
        items = obj
    else:
        return obj.__repr__()

    if len(items) > 2:
        repr_str = ', '.join(str(item) for item in items[:-1]) + f', {conjunction} ' + str(items[-1])
    else:
        repr_str = ', '.join(str(item) for item in items)

    return repr_str
