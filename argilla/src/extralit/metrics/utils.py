import logging
from typing import Tuple, List, Dict, Union, Literal

import numpy as np
import pandas as pd
from natsort import index_natsorted

_LOGGER = logging.getLogger(__name__)

def harmonize_columns(true_df: pd.DataFrame, pred_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ensure the same column ordering by aligning the columns of the dataframes and converting all columns to the same dtypes.
    Args:
        true_df:
        pred_df:

    Returns:

    """
    if not true_df.shape[1] or not pred_df.shape[1]:
        return true_df, pred_df

    # Convert all columns to same dtypes
    concat_iterables_fn = lambda x: ','.join(map(str, x)) if isinstance(x, (list, set, np.ndarray)) else x
    true_df = true_df.map(concat_iterables_fn)
    pred_df = pred_df.map(concat_iterables_fn)
    pred_df = pred_df.astype(
        true_df.dtypes.drop(index=true_df.columns.difference(pred_df.columns)),
        errors='ignore')

    extra_columns = pred_df.columns.difference(true_df.columns)
    pred_df = pred_df.reindex(columns=true_df.columns.intersection(pred_df.columns).append(extra_columns))

    return true_df, pred_df


def is_numeric_dtype(series: pd.Series) -> bool:
    return np.issubdtype(series.dtype, np.number)


def natural_sort_key_generator(s: pd.Series) -> np.ndarray:
    fill_value = -999999 if is_numeric_dtype(s) else 'zzz'
    return np.argsort(index_natsorted(s.fillna(fill_value)))


def reorder_rows(
    true_df: pd.DataFrame, pred_df: pd.DataFrame, index_columns: List[str] = None, verbose=False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ensure the same row orders by determining the columns for sorting

    Args:
        true_df:
        pred_df:
        index_columns: default None. If provided, these columns will be prioritized for sorting before other columns in the dataframes.
        verbose:
    """
    sort_columns = []
    if index_columns is not None and len(index_columns):
        index_columns = true_df.columns.intersection(pred_df.columns).intersection(index_columns)
        if index_columns.size:
            sort_columns.extend(most_similar_columns(pred_df[index_columns], true_df[index_columns]))
    common_columns = most_similar_columns(pred_df, true_df)

    if common_columns:
        sort_columns.extend(common_columns)

    if sort_columns:
        true_df = true_df.sort_values(by=sort_columns, key=natural_sort_key_generator)
        pred_df = pred_df.sort_values(by=sort_columns, key=natural_sort_key_generator)

    if verbose:
        _LOGGER.info(f'sort_columns: {sort_columns}')

    return true_df, pred_df


def convert_metrics_to_df(
    metrics: Dict[str, float],
    format: Literal['series', 'dataframe'] = 'series',
    n_levels=2
) -> Union[pd.Series, pd.DataFrame]:
    if format in {'series', 'dataframe'}:
        metrics = pd.Series(metrics)
        metrics.index = metrics.index.str.split('_', n=n_levels, expand=True)
        if format == 'dataframe':
            metrics = metrics.to_frame()

    return metrics


def most_similar_columns(pred_df: pd.DataFrame, true_df: pd.DataFrame) -> List[str]:
    intersecting_columns = {
        col: len(set(true_df[col]) & set(pred_df[col])) \
        for col in true_df.columns.intersection(pred_df.columns) \
        if true_df[col].nunique() > 1 and pred_df[col].nunique() > 1}

    # If dtypes of intersecting columns are different, give warning
    for col in intersecting_columns:
        if true_df[col].dtype != pred_df[col].dtype:
            _LOGGER.warning(f"\nColumn {col} has different dtypes: {true_df[col].dtype} and {pred_df[col].dtype}")

    if not intersecting_columns:
        return []

    intersecting_columns = sorted(intersecting_columns.items(), key=lambda x: x[1], reverse=True)
    intersecting_columns = [col for col, _ in intersecting_columns]

    return intersecting_columns
