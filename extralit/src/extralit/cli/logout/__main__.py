import typer

app = typer.Typer(invoke_without_command=True)


def remove_credentials():
    """Remove stored credentials."""
    from extralit.client.login import ExtralitCredentials

    try:
        ExtralitCredentials.remove()
    except FileNotFoundError:
        # If credentials don't exist, that's fine
        pass

    return True


@app.callback(help="Logout from an Extralit Server")
def logout(force: bool = typer.Option(False, help="Force the logout even if the server cannot be reached")) -> None:
    """Logout from an Extralit Server by removing stored credentials."""
    from rich.console import Console

    from extralit.cli.callback import init_callback
    from extralit.cli.rich import get_themed_panel

    if not force:
        try:
            init_callback()
        except Exception:
            panel = get_themed_panel(
                "Could not connect to the Extralit Server. Use --force to logout anyway.",
                title="Connection error",
                title_align="left",
                success=False,
            )
            Console().print(panel)
            raise typer.Exit(code=1)

    # Remove the credentials
    remove_credentials()

    # Show success message
    panel = get_themed_panel(
        "Logged out successfully from Extralit server!",
        title="Logout",
        title_align="left",
    )
    Console().print(panel)


if __name__ == "__main__":
    app()
