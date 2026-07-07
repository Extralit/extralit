from typer import Typer

from .reindex import list_tables, reindex

app = Typer(help="Commands for the Extralit v2 LanceDB index.", no_args_is_help=True)

app.command(name="list", help="List existing LanceDB index tables.")(list_tables)
app.command(name="reindex", help="Rebuild v2 schema index tables from Postgres.")(reindex)

if __name__ == "__main__":
    app()
