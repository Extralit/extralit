from typing import Union, List
import pandas as pd


def singleton(df: pd.DataFrame, *, enabled:bool=True) -> bool:
    if not enabled:
        return True
    
    return df.index.is_unique
