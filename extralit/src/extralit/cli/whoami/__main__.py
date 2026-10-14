import typer
from rich.markdown import Markdown

app = typer.Typer(invoke_without_command=True)


def get_current_user():
    """Get information about the current user.

    Returns:
        User: The current user.

    Raises:
        ValueError: If not logged in.
    """
    from extralit.cli.callback import init_callback

    # Initialize client and get current user
    client = init_callback()

    # Return the current user
    return client.me


@app.callback(help="Show information about the current user")
def whoami() -> None:
    """Display information about the current user."""
    from rich.console import Console

    from extralit.cli.rich import get_themed_panel

    try:
        # Get current user (this will initialize the client)
        user = get_current_user()

        panel = get_themed_panel(
            Markdown(
                f"- **Username**: {user.username}\n"
                f"- **Role**: {user.role}\n"
                f"- **First name**: {user.first_name}\n"
                f"- **Last name**: {user.last_name}\n"
            ),
            title="Current User",
            title_align="left",
        )
        Console().print(panel)
    except ValueError as e:
        panel = get_themed_panel(
            str(e),
            title="Not logged in",
            title_align="left",
            success=False,
        )
        Console().print(panel)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
