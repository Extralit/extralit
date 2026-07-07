import typer

from .database import app as database_app
from .index import app as index_app
from .search_engine import app as search_engine_app
from .start import start
from .worker import worker

app = typer.Typer(help="Commands for Extralit server management", no_args_is_help=True)

app.add_typer(database_app, name="database")
app.add_typer(index_app, name="index")
app.add_typer(search_engine_app, name="search-engine")
app.command(name="worker", help="Starts rq workers")(worker)
app.command(name="start", help="Starts the Extralit server")(start)

if __name__ == "__main__":
    app()
