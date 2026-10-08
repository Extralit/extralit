from extralit.cli.files.delete import delete_file
from extralit.cli.files.download import download_file
from extralit.cli.files.list import list_files
from extralit.cli.files.upload import upload_file
from extralit.cli.typer_ext import ExtralitTyper

app = ExtralitTyper(help="Manage files in workspaces", no_args_is_help=True)

# Register all commands
app.command(name="list")(list_files)
app.command(name="upload")(upload_file)
app.command(name="download")(download_file)
app.command(name="delete")(delete_file)

if __name__ == "__main__":
    app()
