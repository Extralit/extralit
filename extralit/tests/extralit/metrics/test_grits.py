import pandas as pd

from extralit.metrics.extraction import grits_from_pandas


def test_identical_dataframes_grits_from_pandas():
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df2 = df1.copy()
    result = grits_from_pandas(df1, df2, format='series')
    assert result.loc[("grits", "top", "f1")] == 1.0
    assert result.loc[("grits", "con", "f1")] == 1.0


def test_different_dataframes_grits_from_pandas():
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df2 = pd.DataFrame({'A': [1, 3], 'B': [2, 4]})
    result = grits_from_pandas(df1, df2, format='series')
    assert result.loc[("grits", "top", "f1")] == 1.0
    assert result.loc[("grits", "con", "f1")] != 1.0


def test_grits_from_pandas_missing_column_in_true_df():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    pred_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
    result = grits_from_pandas(true_df, pred_df, metrics=['con'], format='series', verbose=2)
    assert result.loc[("grits", "con", "f1")] != 1.0
    assert result.loc[("grits", "con", "recall")] == 1.0


def test_grits_from_pandas_missing_column_in_pred_df():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
    pred_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    result = grits_from_pandas(true_df, pred_df, metrics=['con', 'alignment'], verbose=2)
    alignment = result['alignment']
    assert alignment.shape == pred_df.shape
    assert result["grits_con_precision"] == 1.0
    assert result["grits_con_f1"] == 0.8


def test_grits_from_pandas_empty_true_df():
    true_df = pd.DataFrame()
    pred_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    result = grits_from_pandas(true_df, pred_df, metrics=['con'], format='series')
    assert result.loc[("grits", "con", "precision")] == 0.0
    assert result.loc[("grits", "con", "recall")] == 1.0


def test_grits_from_pandas_empty_pred_df():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    pred_df = pd.DataFrame()
    result = grits_from_pandas(true_df, pred_df, metrics=['con'], format='series')
    assert result.loc[("grits", "con", "precision")] == 1.0
    assert result.loc[("grits", "con", "recall")] == 0.0


def test_extra_column_in_pred_df_grits_from_pandas():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    pred_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
    result = grits_from_pandas(true_df, pred_df, format='series')
    assert result.loc[("grits", "top", "f1")] != 1.0
    assert result.loc[("grits", "con", "f1")] != 1.0


def test_grits_from_pandas_missing_row_in_true_df():
    true_df = pd.DataFrame({'A': [1], 'B': [3]})
    pred_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    result = grits_from_pandas(true_df, pred_df, metrics=['con', 'alignment'], verbose=2)
    alignment = result['alignment']
    assert alignment.shape == true_df.shape
    assert result["grits_con_recall"] == 1.0
    assert result["grits_con_f1"] == 0.8


def test_grits_from_pandas_missing_row_in_pred_df():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    pred_df = pd.DataFrame({'A': [1], 'B': [3]})
    result = grits_from_pandas(true_df, pred_df, metrics=['con', 'alignment'], verbose=2)
    alignment = result['alignment']
    assert alignment.shape == pred_df.shape
    assert result["grits_con_precision"] == 1.0
    assert result["grits_con_f1"] == 0.8

def test_identical_dataframes_different_dtypes_grits_from_pandas():
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3.0, 4.0]})
    df2 = pd.DataFrame({'A': ['1', '2'], 'B': ['3', '4']})
    result = grits_from_pandas(df1, df2, format='series')
    assert result.loc[("grits", "top", "f1")] == 1.0
    assert result.loc[("grits", "con", "f1")] == 1.0


def test_grits_from_pandas_with_empty_dataframe():
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df2 = pd.DataFrame()
    result = grits_from_pandas(df1, df2, format='series')
    assert result.loc[("grits", "top", "f1")] == 0.0
    assert result.loc[("grits", "con", "f1")] == 0.0

    result = grits_from_pandas(df2, df1, format='series')
    assert result.loc[("grits", "top", "f1")] == 0.0
    assert result.loc[("grits", "con", "f1")] == 0.0


def test_grits_from_pandas_with_excluded_columns():
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df2 = pd.DataFrame({'A': [1, 2], 'B': [3, 5]})
    result = grits_from_pandas(df1, df2, format='series', exclude_columns=['B'])
    assert result.loc[("grits", "top", "f1")] == 1.0
    assert result.loc[("grits", "con", "f1")] == 1.0


def test_reduce_column_grits_from_pandas():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    pred_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    result = grits_from_pandas(true_df, pred_df, format='series', reduce='column')
    assert result.loc[("grits", "top", "f1"), 'A'] == 1.0
    assert result.loc[("grits", "con", "f1"), 'B'] == 1.0


def test_different_permutation_grits_from_pandas():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]}, index=['x', 'y'])
    pred_df = pd.DataFrame({'B': [4, 3], 'A': [2, 1]}, index=['y', 'x'])
    result = grits_from_pandas(true_df, pred_df, format='series')
    assert result.loc[("grits", "top", "f1")] == 1.0
    assert result.loc[("grits", "con", "f1")] == 1.0


def test_index_columns_grits_from_pandas():
    true_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]}, index=['x', 'y'])
    pred_df = pd.DataFrame({'A': [2, 1], 'B': [4, 3]}, index=['y', 'x'])
    result = grits_from_pandas(true_df, pred_df, format='series', index_columns=['A', 'B'])
    assert result.loc[("grits", "top", "f1")] == 1.0
    assert result.loc[("grits", "con", "f1")] == 1.0


