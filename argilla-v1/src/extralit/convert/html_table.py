import html
import io
import logging
import re
from collections import defaultdict
from typing import Union

import pandas as pd
from bs4 import BeautifulSoup

from extralit.convert.text import remove_markdown_from_string


def html_table_to_json(s: str) -> str:
    if not isinstance(s, io.StringIO):
        s = io.StringIO(s)

    df = html_to_df(s, convert_spanning_rows=False)
    df.columns = df.columns.astype(str).str.replace('.', '')

    df_json = df.to_json(orient='table',
                         index=bool(df.index.name) or len(df.index.names) > 1)
    return df_json


def html_to_df(
    s: Union[io.StringIO, str],
    flatten_columns=True, convert_spanning_rows=False, remove_markdown=False, rename_duplicate_columns=True
) -> pd.DataFrame:
    if not isinstance(s, io.StringIO):
        s = io.StringIO(s.replace('</p><p>', '<br>'))

    df = pd.read_html(s)[0]
    df_str_cols = df.select_dtypes(include=['O', 'string'])
    df.loc[:, df_str_cols.columns] = df_str_cols.map(
        lambda x: html.unescape(x.strip()) if isinstance(x, str) else x, na_action='ignore')

    if isinstance(df.columns, pd.MultiIndex):
        new_columns = [tuple(re.sub(r'\.\d+$', '', level) for level in levels) \
                       for levels in df.columns]
        df.columns = pd.MultiIndex.from_tuples(new_columns)

    df.columns = df.columns.map(
        lambda column: re.sub(r'Unnamed: \d+', 'Variable', column) \
            if isinstance(column, str) else column)

    if flatten_columns:
        df.columns = flatten_multilevel_columns(df.columns)

    if convert_spanning_rows:
        df = convert_spanning_rows_to_group_column(df, new_column='Group')

    if rename_duplicate_columns:
        df.columns = rename_to_unique_columns(df.columns)

    if remove_markdown:
        df = remove_markdown_from_data_frame(df)

    return df


def convert_spanning_rows_to_group_column(df: pd.DataFrame, new_column='Group') -> pd.DataFrame:
    # These rows have the same value across all columns
    mask = df.iloc[:, :].apply(lambda row: row.nunique() == 1, axis=1)
    spanning_rows = df[mask]
    mask_consecutive = (mask.groupby((~mask).cumsum()).transform('size') * mask > 1)

    if spanning_rows.empty:
        return df
    elif mask[0] is False or any(mask_consecutive):
        logging.info(
            f"Skipping pivot of spanning rows, since the first row is not spanning or there are multiple consecutive spans.")
        return df

    if new_column in df.columns:
        new_column = 'Subgroup'

    # Determine group names and the range of rows they span
    last_spanning_row_index = 0
    for index, row in spanning_rows.iterrows():
        if last_spanning_row_index is not None:
            # Assign group name to the range of rows between the last and current spanning rows
            group_name = df.iloc[last_spanning_row_index, 0]
            df.loc[last_spanning_row_index + 1:index - 1, new_column] = group_name
        last_spanning_row_index = index

    # Add the last group if there's any data after the last spanning row
    if last_spanning_row_index is not None and last_spanning_row_index + 1 < len(df):
        group_name = df.iloc[last_spanning_row_index, 0]
        df.loc[last_spanning_row_index + 1:, new_column] = group_name

    # Remove the spanning rows
    df = df[~mask].reset_index(drop=True)

    # Reorder columns to have new_column as the first column
    df.insert(0, new_column, df.pop(new_column))

    return df


def flatten_multilevel_columns(columns: Union[pd.MultiIndex, pd.Index], sep=' - ') -> pd.Index:
    if isinstance(columns, pd.MultiIndex):
        new_columns = columns.map(
            lambda levels: sep.join(list(dict.fromkeys(str(level) for level in levels if level)) \
                                        if isinstance(levels, tuple) else str(levels)))
    else:
        new_columns = columns

    return new_columns


def rename_to_unique_columns(columns: Union[pd.Index, pd.MultiIndex]) -> Union[pd.Index, pd.MultiIndex]:
    column_counts = defaultdict(int)

    if isinstance(columns, pd.MultiIndex):
        new_columns = []
        for levels in columns:
            if levels in column_counts:
                column_counts[levels] += 1
                if column_counts[levels] > 1:
                    levels[-1] = f"{levels[-1]}.{column_counts[levels]}"
            else:
                column_counts[levels] = 0

            new_columns.append(tuple(levels))

        return pd.MultiIndex.from_tuples(new_columns)

    else:
        new_columns = []
        column_counts = {}
        for col in columns:
            if col in column_counts:
                column_counts[col] += 1
                new_column = f"{col}.{column_counts[col]}"
            else:
                column_counts[col] = 0
                new_column = col
            new_columns.append(new_column)

        return pd.Index(new_columns)


def remove_markdown_from_data_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.map(remove_markdown_from_string)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = pd.MultiIndex.from_tuples(
            [tuple(remove_markdown_from_string(label) for label in col) for col in df.columns], names=df.columns.names
        )
    else:
        df.columns = [remove_markdown_from_string(col) for col in df.columns]

    return df


def remove_html_styles(html_str):
    style_pattern = r'\s*style="[^"]*"'
    html_str = re.sub(style_pattern, '', html_str)

    class_pattern = r'\s*class="[^"]*"'
    html_str = re.sub(class_pattern, '', html_str)

    tag_pattern = r'<\/?span[^>]*>|<\/?em[^>]*>'
    html_str = re.sub(tag_pattern, '', html_str)

    return html_str


def fix_llmsherpa_html_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    if not soup.table:
        return html

    # Ensure <thead> exists. If not, wrap the first <tr> in <thead>
    if not soup.thead:
        for th in soup.find_all('th'):
            if not th.find_parent('thead'):
                thead = soup.new_tag('thead')
                th.wrap(thead)

    # Convert <td> to <th> in <thead>
    if soup.thead:
        for td in soup.thead.find_all('td'):
            td.name = 'th'

    # Ensure <tbody> exists for the remaining rows
    if not soup.tbody and soup.thead:
        tbody = soup.new_tag('tbody')
        # Exclude rows already inside <thead>
        for tr in soup.table.find_all('tr', recursive=False):
            if tr not in soup.thead:
                tbody.append(tr)
        soup.table.append(tbody)

    return str(soup)


def llmsherpa_html_to_df(html: io.StringIO):
    html = fix_llmsherpa_html_table(html)
    df = pd.read_html(io.StringIO(html) if not isinstance(html, io.StringIO) else html)[0]
    # df = df.dropna(axis='columns', how='all')

    columns = df.columns.to_frame()
    columns = columns.fillna('Unnamed')
    df.columns = pd.MultiIndex.from_frame(columns)

    df.columns = rename_to_unique_columns(df.columns)

    return df
