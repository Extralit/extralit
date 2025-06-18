import pandas as pd


def unmatched_join_keys(df: pd.DataFrame, other: pd.DataFrame, key: str) -> pd.Series:
    """
    Count the number of unmatched keys in the `df` DataFrame compared to the `other` DataFrame.
    """
    if key in df.columns:
        merged_df = df.merge(other, 
                            on=key, 
                            how='left', indicator=True)
        a_unmatched_keys = merged_df[merged_df['_merge'] == 'left_only'][key]

    else:
        merged_df = df.merge(other, 
                            left_index=df.index.name==key, 
                            right_index=other.index.name==key, 
                            how='left', indicator=True)
        
        a_unmatched_keys = merged_df[merged_df['_merge'] == 'left_only'].index

    return a_unmatched_keys.drop_duplicates()