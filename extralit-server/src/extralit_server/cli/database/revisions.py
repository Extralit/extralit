import alembic.config
import typer

from extralit_server.database import ALEMBIC_CONFIG_FILE, TAGGED_REVISIONS

from . import utils


def revisions():
    current_revision = utils.get_current_revision(ALEMBIC_CONFIG_FILE, verbose=True)

    typer.echo("")
    typer.echo("Tagged revisions")
    typer.echo("-----------------")
    for version, revision in TAGGED_REVISIONS.items():
        typer.echo(f"• {version} (revision: {revision!r})")

    typer.echo("")
    typer.echo("Alembic revisions")
    typer.echo("-----------------")
    alembic.config.main(argv=["-c", ALEMBIC_CONFIG_FILE, "history"])

    typer.echo("")
    typer.echo("Current revision")
    typer.echo("----------------")
    typer.echo(current_revision)


if __name__ == "__main__":
    typer.run(revisions)
