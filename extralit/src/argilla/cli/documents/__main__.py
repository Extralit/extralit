"""Documents CLI commands."""

from argilla.cli.typer_ext import ArgillaTyper

# Import all documents CLI commands
from argilla.cli.documents.list import list_documents
from argilla.cli.documents.add import add_document
from argilla.cli.documents.delete import delete_document

app = ArgillaTyper(help="Manage documents in workspaces", no_args_is_help=True)

# Register all commands
app.command(name="list")(list_documents)
app.command(name="add")(add_document)
app.command(name="delete")(delete_document)

if __name__ == "__main__":
    app()
