from typing import Optional

import alembic
import typer
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util import CommandError

from extralit_server.database import ALEMBIC_CONFIG_FILE, TAGGED_REVISIONS

from . import utils


def migrate_db(revision: Optional[str] = typer.Option(default="head", help="DB Revision to migrate to")):
    current_revision = utils.get_current_revision(ALEMBIC_CONFIG_FILE)
    revision = TAGGED_REVISIONS.get(revision, revision)

    if revision and current_revision:
        script = ScriptDirectory.from_config(Config(ALEMBIC_CONFIG_FILE))

        try:
            script.walk_revisions(base=current_revision, head=revision).__next__()
            action = "upgrade"
        except CommandError:
            action = "downgrade"

    else:
        revision = revision or "head"
        action = "upgrade"

    alembic_args = ["-c", ALEMBIC_CONFIG_FILE, action, revision]
    typer.echo(f"command: alembic {' '.join(alembic_args)}")

    alembic.config.main(argv=alembic_args)


if __name__ == "__main__":
    typer.run(migrate_db)
