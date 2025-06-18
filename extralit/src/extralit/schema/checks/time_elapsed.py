import pandas as pd
from pandera.typing import DataFrame


def check_time_difference(
        df: DataFrame, *, field: str = None,
        start_year: str, start_month: str,
        end_year: str, end_month: str,
        unit: str = "months",
        margin: float = 1):
    """
    Check if the `field` column correctly represents the time difference
    between start_year (and start_month) and end_year (and end_month) in months.
    """
    start_dates = pd.to_datetime(df[start_year].astype(str) + '-' + df[start_month].astype(str),
                                 format='%Y-%m',
                                 yearfirst=True,
                                 errors='coerce')
    end_dates = pd.to_datetime(df[end_year].astype(str) + '-' + df[end_month].astype(str),
                               format='%Y-%m',
                               yearfirst=True,
                               errors='coerce')
    calculated_time_elapsed = (end_dates - start_dates).dt.days

    if unit == 'months':
        calculated_time_elapsed /= 30.44  # Average days per month

    # Allow a small margin of error due to average days per month approximation
    checks = df[field].isna() | calculated_time_elapsed.isna() | ((calculated_time_elapsed - df[field]).abs() <= margin)

    return checks


