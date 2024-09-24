import io
import logging
from collections import defaultdict
from typing import Optional, List, Dict, Union, Literal

import pandas as pd

from extralit.extraction.models.paper import PaperExtraction
from extralit.metrics.grits import grits_from_html
from extralit.metrics.utils import harmonize_columns, reorder_rows, convert_metrics_to_df


def grits_from_batch(
    true_batch: Dict[str, PaperExtraction],
    pred_batch: Dict[str, PaperExtraction],
    exclude_columns: List[str] = [],
    pairwise=False,
    index_names: List[str] = ['Reference', 'Schema', 'Field'],
    compute_mean: Optional[str] = None,
    **kwargs
) -> pd.DataFrame:
    metrics = defaultdict(lambda: {})

    if pairwise:
        for true_key in true_batch:
            for pred_key in pred_batch:
                true_extractions = true_batch[true_key]
                pred_extractions = pred_batch[pred_key]
                if not pred_extractions or not true_extractions:
                    continue

                outputs = grits_paper(true_extractions, pred_extractions, exclude_columns=exclude_columns, **kwargs)
                if outputs:
                    metrics[(true_key, pred_key)] = pd.concat({str(k): v for k, v in outputs.items()}, axis=1).T
    else:
        for batch in set(true_batch) & set(pred_batch):
            true_extractions = true_batch[batch]
            pred_extractions = pred_batch[batch]
            if not pred_extractions or not true_extractions:
                continue

            if isinstance(true_extractions, PaperExtraction):
                outputs = grits_paper(true_extractions, pred_extractions, exclude_columns=exclude_columns, **kwargs)
                metrics[batch] = pd.concat({str(k): v for k, v in outputs.items()}, axis=1).T
            elif isinstance(true_extractions, list) and isinstance(true_extractions[0], pd.DataFrame):
                outputs = grits_multi_tables(true_extractions, pred_extractions, **kwargs)
                metrics[batch] = outputs
            else:
                raise ValueError(f"Invalid type for true_extractions: {type(true_extractions)}")


    metrics_df = pd.concat(metrics, axis=0)
    metrics_df.index.names = index_names[:metrics_df.index.nlevels]

    if compute_mean:
        aggregated = metrics_df.groupby(compute_mean).mean()
        return aggregated

    return metrics_df


def grits_paper(
    true_extractions: PaperExtraction,
    pred_extractions: PaperExtraction,
    exclude_columns=['Site'],
    verbose=False,
    metrics: List[Literal['top', 'con', 'upper_bound', 'alignment']] = ['con'],
    **kwargs
) -> Dict[str, Union[pd.Series, Dict[str, float]]]:
    exclude_columns = exclude_columns or []

    output = {}

    for schema_name in true_extractions.schemas.ordering:
        if schema_name not in true_extractions:
            output[schema_name] = None
            continue

        schema_deps = true_extractions.schemas.upstream_dependencies[schema_name]
        if any(schema_name not in pred_extractions for schema_name in schema_deps):
            logging.warning(f"Missing extractions for {schema_deps} in {pred_extractions.__repr__()}")

        ref_columns = [
            col for dep in schema_deps \
            for col in true_extractions.schemas.index_names(dep) + true_extractions.schemas.columns(dep)]

        output[schema_name] = grits_from_pandas(
            true_extractions.get_joined_data(schema_name),
            pred_extractions.get_joined_data(schema_name) if schema_name in pred_extractions else pd.DataFrame(),
            index_columns=ref_columns,
            only_columns=true_extractions.schemas.columns(schema_name),
            exclude_columns=exclude_columns + ref_columns,
            metrics=metrics, format='series', verbose=verbose, **kwargs)

    return output


def grits_from_pandas(true_df: pd.DataFrame,
                      pred_df: pd.DataFrame,
                      index_columns: Optional[List[str]] = None,
                      only_columns: Optional[List[str]] = None,
                      exclude_columns: Optional[List[str]] = None,
                      metrics: List[Literal['top', 'con', 'upper_bound', 'alignment']] = ['top', 'con'],
                      reduce: Literal['table', 'column'] = 'table',
                      format: Literal['series', 'dataframe', 'None'] = None,
                      nan_value='NA',
                      verbose=False, ) -> pd.Series:
    """
    Grid Table Similarity (GriTS) evaluation metric for data extraction task.

    Args:
        true_df (pd.DataFrame): Ground truth table.
        pred_df (pd.DataFrame): Predicted table.
        index_columns (list): List of columns to sort both true_df and pred_df to the same row ordering.
        only_columns (list): List of columns to include in evaluation.
        exclude_columns (list): List of columns to exclude from evaluation.
        metrics (list): List of metrics to compute. Subset of {'top', 'con', 'upper_bound'}.
        reduce (str): One of {'table', 'column'}.
        format (str): Output format. One of {None, 'series', 'dataframe'}.
        verbose (bool): For debugging purposes, return preprocessed dataframes before
            they're passed into `grits_from_html`.
    """
    true_df = true_df.copy().dropna(axis='columns', how='all').dropna(axis=0, how='all')
    pred_df = pred_df.copy().dropna(axis='columns', how='all').dropna(axis=0, how='all')

    if isinstance(exclude_columns, pd.Index):
        exclude_columns = exclude_columns.tolist()
    exclude_columns = exclude_columns or []

    true_df, pred_df = harmonize_columns(true_df, pred_df)
    true_df, pred_df = reorder_rows(true_df, pred_df, index_columns=index_columns, verbose=verbose)

    # Drop columns not applicable for the schema
    if exclude_columns is not None:
        true_df = true_df.drop(columns=exclude_columns, errors='ignore')
        pred_df = pred_df.drop(columns=exclude_columns, errors='ignore')

    if only_columns is not None:
        true_df = true_df.filter(only_columns, axis='columns')
        pred_df = pred_df.filter(only_columns, axis='columns')

    if nan_value:
        true_df = true_df.loc[:, (true_df != nan_value).any(axis=0)]
        pred_df = pred_df.loc[:, (pred_df != nan_value).any(axis=0)]

    to_html_args = dict(
        index=False,
        na_rep='',
        float_format=lambda x: '%.0f' % x if x == round(x) else '%.2f' % x
    )

    if verbose:
        print('\ngrits_from_pandas debug:\n', 'only_columns', only_columns or true_df.columns.tolist())

    if reduce == 'table':
        true_html = true_df.to_html(**to_html_args)
        pred_html = pred_df.to_html(**to_html_args)

        outputs = grits_from_html(true_html, pred_html, metrics=metrics)
        outputs = convert_metrics_to_df(outputs, format)

    elif reduce == 'column':
        outputs = {}
        for col in true_df.columns.difference(exclude_columns or []):
            true_html = true_df[[col]].to_html(**to_html_args)
            pred_html = pred_df[[col]].to_html(**to_html_args)
            outputs[col] = convert_metrics_to_df(grits_from_html(true_html, pred_html, metrics=metrics),
                                                 format='series')

        outputs = pd.concat(outputs, axis=1)
    else:
        raise ValueError(f"Invalid value for reduce: {reduce}")

    if verbose >= 2:
        outputs['true_df'], outputs['pred_df'] = true_df, pred_df

    return outputs


def grits_multi_tables(true_tables: List[Union[pd.DataFrame, str]], pred_tables: List[Union[pd.DataFrame, str]],
                       only_common_columns=True,
                       **kwargs) -> pd.DataFrame:
    results: Dict[str, pd.Series] = defaultdict(dict)

    for i, (true_df, pred_df) in enumerate(zip(true_tables, pred_tables)):
        try:
            if isinstance(true_df, pd.DataFrame):
                if only_common_columns:
                    only_columns = true_df.columns.intersection(pred_df.columns).difference(kwargs.get('index_columns', [])).tolist()
                    kwargs.pop('only_columns', None)
                else:
                    only_columns = kwargs.pop('only_columns', None)

                results[i] = grits_from_pandas(true_df, pred_df, format='series',
                                               only_columns=only_columns, **kwargs)

            elif isinstance(true_df, str):
                metrics = grits_from_html(
                    pd.read_html(io.StringIO(true_df))[0].to_html(index=False, na_rep=''),
                    pd.read_html(io.StringIO(pred_df))[0].to_html(index=False, na_rep=''),
                    **kwargs)
                results[i] = convert_metrics_to_df(metrics, format='series')

        except Exception as e:
            logging.error(f"Failed to compute metrics for index {i}. \n{e}")
            results[i] = None

    if not {str(k): v for k, v in results.items() if v is not None}:
        return pd.DataFrame()

    metrics_df = pd.concat(results, axis=1).T
    return metrics_df
