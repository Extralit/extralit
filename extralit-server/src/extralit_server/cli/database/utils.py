import io

from alembic import command
from alembic.config import Config


def get_current_revision(alembic_config_file: str, verbose: bool = False) -> str:
    output_buffer = io.StringIO()
    alembic_cfg = Config(alembic_config_file, stdout=output_buffer)

    command.current(alembic_cfg, verbose=verbose)
    command_result = output_buffer.getvalue().strip()

    if verbose:
        return command_result
    return command_result.split(" ")[0]
