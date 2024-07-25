import warnings
from typing import Dict, Any, Union

import pandas as pd
import pandera as pa


def check_data_types(schema: Union[pa.DataFrameModel, pa.DataFrameSchema]) -> Dict[str, str]:
    dataframe_schema = schema.to_schema() if hasattr(schema, 'to_schema') else schema
    dtypes_dict = dataframe_schema.dtypes
    type_classification = {}

    for column, pa_dtype in dtypes_dict.items():
        dtype = str(pa_dtype)

        if dtype in [int, 'int', 'int32', 'int64', 'Int32', 'Int64', float, 'float', 'float32', 'float64']:
            type_classification[column] = 'numeric'
        elif dtype in [str, 'str', 'object']:
            type_classification[column] = 'string'
        else:
            type_classification[column] = 'unknown'
            warnings.warn(f'Unknown data type for column {column}: {dtype}')

    return type_classification


def replace_na_values(df: pd.DataFrame, schema: Union[pa.DataFrameModel, pa.DataFrameSchema],
                      to_replace: Dict[str, Dict[Any, Any]]) -> pd.DataFrame:
    dtype_to_replace = {}

    for col, dclass in check_data_types(schema).items():
        if to_replace and col in to_replace:
            dtype_to_replace[col] = to_replace[col]
        elif dclass == 'numeric':
            dtype_to_replace[col] = {'NA': 0, 'nan': 0, 'NaN': 0, 'None': 0, '': 0}
        elif dclass == 'string':
            dtype_to_replace[col] = {'NA': None, '': None}
        else:
            # If the data type is unknown, we don't want to replace anything
            pass
    
    replaced_na_df = df.replace(dtype_to_replace)
    return replaced_na_df



def stage_for_validate(df: pd.DataFrame,
                       schema: Union[pa.DataFrameModel, pa.DataFrameSchema],
                       to_replace: Dict[str, Dict]=None,
                       prefix_index_name: str = 'publication_ref',
                       ) -> pd.DataFrame:
    """
    Replace NA values in a dataframe with a value that is appropriate for the data type of the column.

    :param df: Pandas dataframe
    :param schema: Pandera dataframe itnrecal
    :param to_replace: Dictionary of values to replace. Keys are column names, values are dictionaries of values to replace.
    :return: Pandas dataframe with NA values replaced
    """
    dataframe_schema = schema.to_schema() if hasattr(schema, 'to_schema') else schema

    # df = prepend_reference_to_index_level(df, dataframe_schema, prefix_index_name)
    df = replace_na_values(df, dataframe_schema, to_replace)

    return df


