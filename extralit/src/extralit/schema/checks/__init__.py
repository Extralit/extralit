import pandas as pd
import pandera as pa
from pandera.extensions import register_check_method

from .consistency import check_less_than, check_greater_than, check_between
from .multilabels import is_valid_list_str, multiselect
from .suggestion import suggestion
from .time_elapsed import check_time_difference
from .dataframe import singleton


def register_check_methods() -> None:
    """
    Register Pandera check methods for various check functions, ensuring no duplicate in registered check names.
    """
    if check_less_than.__name__ not in pa.Check:
        register_check_method(
            statistics=["columns_a", "columns_b", "or_equal"],
            supported_types=pd.DataFrame,
            check_type='vectorized'
        )(check_less_than)

    if check_greater_than.__name__ not in pa.Check:
        register_check_method(
            statistics=["columns_a", "columns_b", "or_equal"],
            supported_types=pd.DataFrame,
            check_type='vectorized'
        )(check_greater_than)

    if check_between.__name__ not in pa.Check:
        register_check_method(
            statistics=['columns_target', "columns_lower", "columns_upper", "or_equal"],
            supported_types=pd.DataFrame,
            check_type='vectorized'
        )(check_between)

    if check_greater_than.__name__ not in pa.Check:
        register_check_method(
            statistics=["col_a", "col_b", "or_equal"])(check_greater_than)

    if multiselect.__name__ not in pa.Check:
        register_check_method(statistics=["delimiter", "isin"])(multiselect)

    if suggestion.__name__ not in pa.Check:
        register_check_method(statistics=["values"])(suggestion)

    if check_time_difference.__name__ not in pa.Check:
        register_check_method(
            statistics=['field', "start_year", "start_month", "end_year", "end_month", "unit", "margin"],
            check_type='vectorized')(check_time_difference)
        
    if singleton.__name__ not in pa.Check:
        register_check_method(
            statistics=['enabled'],
            check_type='vectorized')(singleton)

register_check_methods()

__all__ = ['is_valid_list_str', 'multiselect', 'suggestion', 'check_time_difference', 'check_less_than',
           'check_greater_than', 'check_between', 'singleton', 'register_check_methods']
