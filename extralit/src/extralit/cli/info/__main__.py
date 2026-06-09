import typer
from rich.console import Console
from rich.markdown import Markdown

from extralit.cli.callback import init_callback
from extralit.cli.rich import get_themed_panel

app = typer.Typer(invoke_without_command=True)


@app.callback(help="Displays information about the Extralit client and server")
def info() -> None:
    """Display information about the Extralit client and server."""
    try:
        from extralit import __version__ as version
    except ImportError:
        version = "2.0.0"

    client = init_callback()

    panel = get_themed_panel(
        Markdown(f"Connected to {client.api_url}\n- **Client version:** {version}\n"),
        title="Extralit Info",
        title_align="left",
    )

    Console().print(panel)


if __name__ == "__main__":
    app()
