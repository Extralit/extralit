from typing import Union, List

import pandas as pd

from extralit.schema.checks.utils import make_same_length_arguments


def check_less_than(df: pd.DataFrame, *,
                    columns_a: Union[str, List[str]],
                    columns_b: Union[str, List[str]],
                    or_equal: Union[bool, List[str]] = False) -> pd.Series:
    """
    Check if the values of columns in `col_a` are less than the values of columns in `col_b`.

    Args:
        df: pd.DataFrame, required
            The DataFrame to check.
        columns_a: str or List[str], required
            The column name or list of column names to compare.
        columns_b: str or List[str], required
            The column name or list of column names to compare.
        or_equal: bool or List[bool], default=False
            If True, the comparison will be inclusive.
    """
    columns_a, columns_b, or_equal = make_same_length_arguments(columns_a, columns_b, or_equal)
    assert len(columns_a) == len(columns_b) == len(or_equal), \
        f"Input lists must have the same length, given {len(columns_a)}, {len(columns_b)}, {len(or_equal)}"

    checks = pd.Series([True] * len(df), index=df.index)
    for a, b, oe in zip(columns_a, columns_b, or_equal):
        if oe:
            check = df[a] <= df[b]
        else:
            check = df[a] < df[b]
        checks = checks & check.fillna(True)

    return checks


def check_greater_than(df: pd.DataFrame, *,
                       columns_a: Union[str, List[str]],
                       columns_b: Union[str, List[str]],
                       or_equal: Union[bool, List[str]] = False) -> pd.Series:
    """
    Check if the values of columns in `col_a` are greater than the values of columns in `col_b`.

    Args:
        df: pd.DataFrame, required
            The DataFrame to check.
        columns_a: str or List[str], required
            The column name or list of column names to compare.
        columns_b: str or List[str], required
            The column name or list of column names to compare.
        or_equal: bool or List[bool], default=False
            If True, the comparison will be inclusive.

    """
    columns_a, columns_b, or_equal = make_same_length_arguments(columns_a, columns_b, or_equal)
    assert len(columns_a) == len(columns_b) == len(or_equal), \
        f"Input lists must have the same length, given {len(columns_a)}, {len(columns_b)}, {len(or_equal)}"

    checks = pd.Series([True] * len(df), index=df.index)
    for a, b, oe in zip(columns_a, columns_b, or_equal):
        if oe:
            check = df[a] >= df[b]
        else:
            check = df[a] > df[b]
        checks = checks & check.fillna(True)
    return checks


def check_between(df: pd.DataFrame, *,
                  columns_target: Union[str, List[str]],
                  columns_lower: Union[str, List[str]],
                  columns_upper: Union[str, List[str]],
                  or_equal: Union[bool, List[str]] = True) -> pd.Series:
    """
    Check if the values of columns in `col_a` are between the values of columns in `col_b` and `col_c`.

    Args:
        df: pd.DataFrame, required
            The DataFrame to check.
        columns_target: str or List[str], required
            The column name or list of column names to compare.
        columns_lower: str or List[str], required
            The column name or list of column names to compare with `column` to be lower.
        columns_upper: str or List[str], required
            The column name or list of column names to compare.
        or_equal: bool or List[bool], default=False
            If True, the comparison will be inclusive.

    """
    columns_target, columns_lower, columns_upper, or_equal = make_same_length_arguments(
        columns_target, columns_lower, columns_upper, or_equal)
    assert len(columns_target) == len(columns_lower) == len(columns_upper) == len(or_equal), \
        f"Input lists must have the same length, given {len(columns_target)}, {len(columns_lower)}, {len(columns_upper)}, {len(or_equal)}"

    checks = pd.Series([True] * len(df), index=df.index)
    for col, lower, upper, oe in zip(columns_target, columns_lower, columns_upper, or_equal):
        if oe:
            check = (df[col] >= df[lower]) & (df[col] <= df[upper])
        else:
            check = (df[col] > df[lower]) & (df[col] < df[upper])
        checks = checks & check.fillna(True)

    return checks
