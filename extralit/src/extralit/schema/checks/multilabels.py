from typing import List

import pandas as pd


def is_valid_list_str(values: List[str]):
    if not isinstance(values, list): return True

    return all(isinstance(val, str) and val and \
               val.strip() == val and not val.startswith('and ') \
               for val in values)


def multiselect(series: pd.Series, *, delimiter=',', isin: List[str] = None):
    """ Check that the values in the series are valid lists of strings. """
    split_values = series.str.split(r'\s*'+delimiter+r'\s*', regex=True)
    checks = split_values.apply(is_valid_list_str)

    if isinstance(isin, (set, list)) and isin:
        checks = checks & split_values.apply(lambda x: all(is_valid_list_str(x) and set(x).issubset(isin)))

    return checks


