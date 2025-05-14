# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING, List, Optional, Union
import traceback


from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from argilla._resource import Resource
    from argilla._models._documents import Document
    from argilla._models._files import ObjectMetadata

    try:
        import pandas as pd
        import pandera as pa
    except ImportError:
        pass


def get_argilla_themed_panel(
    renderable: RenderableType,
    title: Optional[Union[str, Text]] = None,
    title_align: str = "center",
    success: bool = True,
    exception: Optional[Exception] = None,
    debug: bool = False,
) -> Panel:
    """
    Returns a rich panel with Argilla theme.

    Args:
        renderable: The content to display
        title: The title of the panel
        title_align: The alignment of the title
        success: If True, use success style; if False, use error style
        exception: Optional exception to include in the panel
        debug: If True and exception is provided, include a minimal stack trace

    Returns:
        A rich panel with Argilla theme
    """
    content = renderable

    if exception is not None and debug:
        # Get exception type and message
        exc_type = type(exception).__name__
        exc_msg = str(exception)

        # Get traceback frames
        tb = traceback.extract_tb(exception.__traceback__)
        # Get just the first and last frames for a minimal trace
        if len(tb) > 1:
            minimal_tb = [tb[0], tb[-1]]
        else:
            minimal_tb = tb

        trace_str = f"\n\n[bold]Exception:[/bold] {exc_type}: {exc_msg}\n\n[bold]Debug trace:[/bold]\n"
        for frame in minimal_tb:
            file, line, func, code = frame
            trace_str += f"File '{file}', line {line}, in {func}\n  {code}\n"

        if isinstance(content, str):
            content = f"{content}{trace_str}"
        else:
            content = [content, Text.from_markup(trace_str)]

    return Panel(
        renderable=content,
        title=title,
        title_align=title_align,
        border_style="green" if success else "red",
        padding=1,
    )


def console_table_to_pandas_df(table: Table) -> "pd.DataFrame":
    """
    Converts a rich table to a pandas DataFrame.

    Args:
        table: The rich table to convert

    Returns:
        A pandas DataFrame
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required to convert a table to a DataFrame. Install it with pip install pandas")

    headers = [column.header for column in table.columns]
    rows = []
    for row in table.rows:
        rows.append([cell.renderable if hasattr(cell, "renderable") else str(cell) for cell in row.cells])

    return pd.DataFrame(rows, columns=headers)


def print_rich_table(
    resources: List[Union["Resource", "pa.DataFrameSchema", "ObjectMetadata", "Document"]],
    columns: Optional[List[str]] = None,
    title: Optional[str] = None,
    return_table: bool = False,
) -> Optional[Table]:
    """
    Prints resources in a rich formatted table.

    Args:
        resources: List of resources to display
        columns: Optional list of columns to display. If None, uses default columns.
        title: Optional title for the table. If None, uses the resource_type.
        return_table: If True, return the table instead of printing it.

    Returns:
        The table object if return_table is True, otherwise None.
    """
    if not resources:
        if not return_table:
            Console().print("No resources found")
        return None

    resource_type = type(resources[0]).__name__
    if hasattr(resources[0], "__class__") and hasattr(resources[0].__class__, "__name__"):
        resource_type = resources[0].__class__.__name__

    title = title or resource_type + "s"
    table = Table(title=title, show_lines=False)

    column_configs = {
        "Dataset": {
            "columns": ["ID", "Name", "Workspace", "Creation Date", "Last Activity Date"],
            "getters": {
                "ID": lambda r: str(r.id),
                "Name": lambda r: r.name,
                "Workspace": lambda r: r.workspace.name,
                "Creation Date": lambda r: r.inserted_at.isoformat(sep=" ") if r.inserted_at else "",
                "Last Activity Date": lambda r: r._model.last_activity_at.isoformat(sep=" ")
                if r._model.last_activity_at
                else "",
            },
            "styles": {
                "ID": "cyan",
                "Name": "green",
                "Workspace": "yellow",
                "Creation Date": "magenta",
                "Last Activity Date": "blue",
            },
        },
        "User": {
            "columns": ["ID", "Username", "First Name", "Last Name", "Role", "Creation Date"],
            "getters": {
                "ID": lambda r: str(r.id),
                "Username": lambda r: r.username,
                "First Name": lambda r: r.first_name,
                "Last Name": lambda r: r.last_name,
                "Role": lambda r: r.role,
                "Creation Date": lambda r: r.inserted_at.isoformat(sep=" ") if r.inserted_at else "",
            },
            "styles": {
                "ID": "cyan",
                "Username": "green",
                "First Name": "yellow",
                "Last Name": "yellow",
                "Role": "magenta",
                "Creation Date": "blue",
            },
        },
        "Workspace": {
            "columns": ["ID", "Name", "Creation Date", "Last Update Date"],
            "getters": {
                "ID": lambda r: str(r.id),
                "Name": lambda r: r.name,
                "Creation Date": lambda r: r.inserted_at.isoformat(sep=" ") if r.inserted_at else "",
                "Last Update Date": lambda r: r.updated_at.isoformat(sep=" ") if r.updated_at else "",
            },
            "styles": {
                "ID": "cyan",
                "Name": "green",
                "Creation Date": "magenta",
                "Last Update Date": "blue",
            },
        },
        "ObjectMetadata": {
            "columns": ["Object Name", "Size", "Last Modified", "Version ID", "Content Type"],
            "getters": {
                "Object Name": lambda r: r.object_name,
                "Size": lambda r: r.size,
                "Last Modified": lambda r: r.last_modified.isoformat() if r.last_modified else "",
                "Version ID": lambda r: r.version_id,
                "Content Type": lambda r: r.content_type,
            },
            "styles": {
                "Object Name": "cyan",
                "Size": "green",
                "Last Modified": "yellow",
                "Version ID": "magenta",
                "Content Type": "blue",
            },
        },
        "Document": {
            "columns": ["ID", "URL", "PMID", "DOI", "Created", "Updated"],
            "getters": {
                "ID": lambda r: str(r.id),
                "URL": lambda r: r.url,
                "PMID": lambda r: r.pmid,
                "DOI": lambda r: r.doi,
                "Created": lambda r: r.inserted_at.isoformat(sep=" ") if r.inserted_at else "",
                "Updated": lambda r: r.updated_at.isoformat(sep=" ") if r.updated_at else "",
            },
            "styles": {
                "ID": "cyan",
                "URL": "green",
                "PMID": "yellow",
                "DOI": "magenta",
                "Created": "blue",
                "Updated": "blue",
            },
        },
        "DataFrameSchema": {
            "columns": ["Name", "Description", "Columns", "Checks"],
            "getters": {
                "Name": lambda r: r.name,
                "Description": lambda r: r.description.strip().replace("\n", " ") if hasattr(r, "description") else "",
                "Columns": lambda r: len(r.columns) if hasattr(r, "columns") else 0,
                "Checks": lambda r: len(r.checks) if hasattr(r, "checks") else 0,
            },
            "styles": {
                "Name": "green",
                "Description": "yellow",
                "Columns": "cyan",
                "Checks": "magenta",
            },
        },
    }

    config = column_configs.get(resource_type, {})
    display_columns = columns or config.get("columns", [])
    getters = config.get("getters", {})
    styles = config.get("styles", {})

    for column in display_columns:
        table.add_column(
            column,
            justify="center" if column != "Name" else "left",
            style=styles.get(column, "white"),
        )

    for resource in resources:
        row_values = []
        for column in display_columns:
            getter = getters.get(column)
            if getter:
                try:
                    value = getter(resource)
                except (AttributeError, KeyError):
                    value = ""
            else:
                try:
                    value = getattr(resource, column.lower().replace(" ", "_"), "")
                except AttributeError:
                    value = ""
            row_values.append(str(value))

        table.add_row(*row_values)

    if return_table:
        return table
    else:
        Console().print(table)
        return None
