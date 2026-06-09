from typer import Typer

from .create import create
from .create_default import create_default
from .migrate import migrate
from .update import update

app = Typer(help="Commands for user management using the database connection", no_args_is_help=True)

app.command(name="create_default", help="Creates default users and workspaces in the Extralit database.")(
    create_default
)
app.command(name="create", help="Creates a user and add it to the Extralit database.", no_args_is_help=True)(create)
app.command(name="update", help="Updates the user's role into the Extralit database.", no_args_is_help=True)(update)
app.command(name="migrate")(migrate)


if __name__ == "__main__":
    app()
