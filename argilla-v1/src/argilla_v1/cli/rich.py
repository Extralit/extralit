#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import TYPE_CHECKING, Any

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from rich.console import RenderableType

# TODO: update colors after consulting it with UI expert
_ARGILLA_BORDER_STYLE = "red"


def get_argilla_themed_table(title: str, **kwargs: Any) -> Table:
    return Table(title=title, border_style=_ARGILLA_BORDER_STYLE, **kwargs)


def get_argilla_themed_panel(renderable: "RenderableType", title: str, success: bool = True, **kwargs: Any) -> Panel:
    if success:
        title = f"[green]{title}"
    return Panel(renderable=renderable, border_style=_ARGILLA_BORDER_STYLE, title=title, **kwargs)


def echo_in_panel(renderable: "RenderableType", title: str, success: bool = True, **kwargs: Any) -> None:
    Console().print(get_argilla_themed_panel(renderable, title, success, **kwargs))


def console_table_to_pandas_df(table: Table) -> pd.DataFrame:
    data = {}
    for col in table.columns:
        data[col.header] = [cell for cell in col.cells]

    return pd.DataFrame.from_dict(data, orient='columns')
