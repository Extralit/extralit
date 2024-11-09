import pandas as pd


def assert_frame_equal(df1, df2, ignore_index=True, **kwargs):
    if ignore_index:
        df1 = df1.reset_index(drop=True)
        df2 = df2.reset_index(drop=True)
    pd.testing.assert_frame_equal(df1, df2, **kwargs)


assert_frame_equal.__doc__ = pd.testing.assert_frame_equal.__doc__
