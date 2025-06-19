import pandas as pd


def read_markdown_table_to_df(markdown_table: str) -> pd.DataFrame:
    # Split the table into lines
    lines = markdown_table.strip().split('\n')

    # Split each line into columns assuming | as the separator
    rows = [line.split('|')[1:-1] for line in lines if line.startswith('|')]

    # Clean up any whitespace and markdown formatting from the cells
    header = [cell.strip().strip('*_`') for cell in rows.pop(0)]  # Assume first line is the header
    data = [[cell.strip().strip('*_`') for cell in row] for row in rows \
            if not all('-' in cell for cell in row)]

    return pd.DataFrame(data, columns=header)
