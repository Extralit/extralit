from typing import List, Union, Optional

import pandas as pd
import pandera as pa
from rapidfuzz import process, fuzz


def get_unique_index(df: pd.DataFrame, group_columns: List[str],
                     prefix='', suffix='', n_digits=2) -> pd.DataFrame:
    if not isinstance(group_columns, list):
        group_columns = list(group_columns)

    non_na_cols = df.dropna(axis=1, how='all').columns
    group_columns = [col for col in group_columns if col in non_na_cols]

    counter_series = enumerate_group_id(df, group_columns)
    counter_ids = counter_series.map(lambda x: f'{prefix}{int(x):0{n_digits}}{suffix}').sort_index()

    assert counter_ids.index.size == df.index.size

    return counter_ids


def enumerate_group_id(df: pd.DataFrame, group_columns: List[str], start=1) -> pd.Series:
    non_na_cols = df.dropna(axis=1, how='all').columns
    valid_group_columns = [col for col in group_columns if col in non_na_cols]
    if not valid_group_columns:
        return pd.Series(index=df.index + start if df.index.dtype == int else df.index, dtype=str).fillna('0')

    # Create a string representation of each row for the valid group columns
    group_strs = df[valid_group_columns].astype(str).apply(lambda row: '-'.join(row), axis=1)

    # Create a dictionary that maps each unique group string to a unique number, in the order they first appear
    group_to_number = {group_str: i for i, group_str in enumerate(pd.unique(group_strs), start=start)}

    # Map each group string in group_strs to its corresponding number
    ngroup = group_strs.map(group_to_number)

    return ngroup


def get_prefix(schema: pa.DataFrameSchema):
    if schema.index is not None:
        if schema.index.checks:
            if 'string' in schema.index.checks[0].statistics:
                return schema.index.checks[0].statistics['string']

    return schema.name[0]


def assign_unique_index(
    df: pd.DataFrame,
    schema: pa.DataFrameSchema,
    index_name: str = "reference",
    prefix: Optional[str] = '',
    suffix: str = '',
    n_digits=2,
    drop_duplicates=False
) -> pd.DataFrame:
    """
    Assign unique reference keys to each entity in `df` of the `model` schema, by enumerating the unique entities.

    Args:
        df: pandas.DataFrame
        schema: Model definition
        index_name: Index name, default 'reference'
        prefix: Prefix
        suffix: Suffix
        n_digits: number of digits to enumerate
        drop_duplicates: Drop duplicate indices

    Returns:
        pd.DataFrame
    """
    # if df.index.name == name or name in df.index.names:
    #     return df

    index = pd.Series(range(1, len(df) + 1)).map(lambda x: f'{prefix}{int(x):0{n_digits}}{suffix}')
    df.index = pd.Index(index, name=index_name)

    if drop_duplicates:
        df = df[~df.index.duplicated()]
    assert not df.index.isna().any()
    return df


def map_items_to_references(items: Union[pd.Series, pd.DataFrame], reference_items: pd.DataFrame,
                            threshold: float = 80) -> List[str]:
    """
    Map `items` to `reference_items` using fuzzy matching.
    Args:
        items: pd.Series
            A series of items in dict to be mapped to `reference_items`
        reference_items:  pd.DataFrame
            A DataFrame with reference items

    Returns:
        List of indices of `reference_items` that best match each item in items
    """
    if isinstance(items, pd.Series):
        assert (items.map(type) == dict).all(), f'given items must be a pd.Series with dict values'
        items_df: pd.DataFrame = items.apply(pd.Series)
        dtypes = reference_items.dtypes.drop(reference_items.columns.difference(items_df.columns))
        items_df = items_df.astype(dtypes, errors='ignore')
    elif isinstance(items, pd.DataFrame):
        items_df = items
    else:
        raise ValueError(f'items must be a pd.Series or pd.DataFrame, given {type(items)}')

    joint_columns = items_df.columns.intersection(reference_items.columns)

    reference_mapping = [None for _ in range(len(items))]
    for idx, item_row in items_df.iterrows():
        # Concatenate item values into a single string for comparison, considering only the columns present in items_df
        item_str = " ".join([str(item_row[col]) for col in joint_columns if item_row[col] is not None])

        # Concatenate each row in reference_items into a single string, considering the same subset of columns
        reference_strs = reference_items[joint_columns].apply(lambda row: " ".join(row.astype(str)), axis=1)

        if not item_str.strip():
            continue

        # Find the best match for item_str in reference_strs using fuzzy search
        best_match, score, _ = process.extractOne(item_str, reference_strs, scorer=fuzz.WRatio)

        # Consider a match if the score is above a certain threshold
        if score > threshold:
            reference_index = reference_strs[reference_strs == best_match].index[0]
            reference_mapping[idx] = reference_index

    return reference_mapping
