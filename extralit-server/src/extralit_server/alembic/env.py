import logging
import time
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.exc import OperationalError

from extralit_server.database import database_url_sync
from extralit_server.models.base import DatabaseModel
from extralit_server.models.database import *  # noqa

logger = logging.getLogger(__name__)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Overwrites the SQLAlchemy URL getting it from extralit database_url settings
config.set_main_option("sqlalchemy.url", database_url_sync())

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = DatabaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Retry configuration for connection errors (e.g., Supabase connection limits)
MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # seconds
MAX_BACKOFF = 30  # seconds


def is_connection_error(exc: Exception) -> bool:
    """Check if the exception is a connection-related error that should be retried."""
    error_msg = str(exc).lower()
    connection_error_patterns = [
        "maxclientsinsessionmode",
        "max clients reached",
        "pool_size",
        "connection refused",
        "connection reset",
        "connection timed out",
        "too many connections",
        "remaining connection slots are reserved",
        "sorry, too many clients already",
    ]
    return any(pattern in error_msg for pattern in connection_error_patterns)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    Includes retry logic for connection pooler limits (e.g., Supabase).

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Retry loop for connection errors (common with Supabase/PgBouncer limits)
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            with connectable.connect() as connection:
                context.configure(connection=connection, target_metadata=target_metadata)

                with context.begin_transaction():
                    context.run_migrations()
            return  # Success, exit the retry loop

        except OperationalError as exc:
            last_exception = exc
            if is_connection_error(exc) and attempt < MAX_RETRIES - 1:
                backoff = min(INITIAL_BACKOFF * (2**attempt), MAX_BACKOFF)
                logger.warning(
                    f"Database connection error (attempt {attempt + 1}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {backoff} seconds..."
                )
                time.sleep(backoff)
            else:
                raise

    # If we exhausted all retries
    if last_exception:
        raise last_exception


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
