import pandas as pd

from extralit.metrics import utils
from tests.extralit.utils import assert_frame_equal


def test_harmonize_columns_with_identical_dataframes():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    result1, result2 = utils.harmonize_columns(df1, df2)
    assert_frame_equal(result1, df1)
    assert_frame_equal(result2, df2)


def test_harmonize_columns_with_different_column_order():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'b': [3, 4], 'a': [1, 2]})
    result1, result2 = utils.harmonize_columns(df1, df2)
    assert_frame_equal(result1, df1)
    assert_frame_equal(result2, df1)


def test_reorder_rows_with_identical_dataframes():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    result1, result2 = utils.reorder_rows(df1, df2)
    assert_frame_equal(result1, df1)
    assert_frame_equal(result2, df2)


def test_reorder_rows_with_different_row_order():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [2, 1], 'b': [4, 3]})
    result1, result2 = utils.reorder_rows(df1, df2, verbose=True)
    assert_frame_equal(result1, df1)
    assert_frame_equal(result2, df1)


def test_convert_metrics_to_df_with_series_format():
    metrics = {'a_b': 1.0, 'c_d': 2.0}
    result = utils.convert_metrics_to_df(metrics, 'series')
    expected = pd.Series(metrics)
    expected.index = expected.index.str.split('_', n=2, expand=True)
    pd.testing.assert_series_equal(result, expected)


def test_convert_metrics_to_df_with_dataframe_format():
    metrics = {'a_b': 1.0, 'c_d': 2.0}
    result = utils.convert_metrics_to_df(metrics, 'dataframe')
    expected = pd.Series(metrics).to_frame()
    expected.index = expected.index.str.split('_', n=2, expand=True)
    assert_frame_equal(result, expected)


def test_most_similar_columns_with_identical_dataframes():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    result = utils.most_similar_columns(df1, df2)
    assert result == ['a', 'b']


def test_most_similar_columns_with_different_dataframes():
    df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    df2 = pd.DataFrame({'a': [1, 2], 'c': [3, 4]})
    result = utils.most_similar_columns(df1, df2)
    assert result == ['a']
