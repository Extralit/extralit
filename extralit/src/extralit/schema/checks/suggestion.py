import logging
from typing import Dict, Optional

import pandas as pd

_LOGGER = logging.getLogger(__name__)

def suggestion(series: pd.Series, values: Dict[str, Optional[Dict[str, str]]]):
    mask = series.isin(values) | series.isna()
    if not mask.all():
        print(f"INFO: Some `{series.name}` values were not in the suggested values: {series[~mask].unique()}")
        _LOGGER.info(f"Some `{series.name}` values were not in the suggested values: {series[~mask].unique()}")

    return True
