import typer

from .migrate import migrate_db
from .revisions import revisions
from .users import app as users_app

app = typer.Typer(help="Commands for Extralit server database management", no_args_is_help=True)

app.add_typer(users_app, name="users")
app.command(name="migrate", help="Run database migrations.")(migrate_db)
app.command(name="revisions", help="Show available revisions.")(revisions)

if __name__ == "__main__":
    app()
