from typer import Typer

from .reindex import list, reindex

app = Typer(help="Commands for Extralit server search engine management", no_args_is_help=True)

app.command(name="list", help="List existing indexes in Elasticsearch.")(list)
app.command(name="reindex", help="Reindex all Extralit entities into search engine.")(reindex)

if __name__ == "__main__":
    app()
