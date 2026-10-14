from typing import Any

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table

_EXTRALIT_BORDER_STYLE = "red"


def get_themed_table(title: str, **kwargs: Any) -> Table:
    return Table(title=title, border_style=_EXTRALIT_BORDER_STYLE, **kwargs)


def get_themed_panel(renderable: RenderableType, title: str, success: bool = True, **kwargs: Any) -> Panel:
    if success:
        title = f"[green]{title}"

    return Panel(renderable=renderable, border_style=_EXTRALIT_BORDER_STYLE, title=title, **kwargs)


def echo_in_panel(renderable: RenderableType, title: str, success: bool = True, **kwargs: Any) -> None:
    Console().print(get_themed_panel(renderable, title, success, **kwargs))
