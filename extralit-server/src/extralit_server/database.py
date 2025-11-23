# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from collections import OrderedDict
from collections.abc import AsyncGenerator, Generator
from typing import TypeVar

from sqlalchemy import create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import IsolationLevel
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

import extralit_server
from extralit_server.settings import settings

try:
    import asyncpg

    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _log_connection_pool_status():
    """Log current database connection pool status for debugging."""
    try:
        if settings.database_is_postgresql:
            # Log async engine pool status
            pool = async_engine.pool
            # SQLAlchemy async pool does not expose sync Pool API (size, checkedin, etc.)
            logger.info(f"Async connection pool status: class={pool.__class__.__name__}, repr={pool}")

            # Log sync engine pool status
            sync_pool = sync_engine.pool
            logger.info(
                f"Sync connection pool status: "
                f"pool_size={sync_pool.size}, "
                f"checkedin={sync_pool.checkedin()}, "
                f"checkedout={sync_pool.checkedout()}, "
                f"overflow={sync_pool.overflow()}, "
                f"invalid={sync_pool.invalid}"
            )
        else:
            logger.info("Using SQLite database (no connection pooling)")
    except Exception as e:
        logger.warning(f"Failed to log connection pool status: {e}")


ALEMBIC_CONFIG_FILE = os.path.normpath(os.path.join(os.path.dirname(extralit_server.__file__), "alembic.ini"))
TAGGED_REVISIONS = OrderedDict(
    {
        "1.7": "1769ee58fbb4",
        "1.8": "ae5522b4c674",
        "1.11": "3ff6484f8b37",
        "1.13": "1e629a913727",
        "1.17": "84f6b9ff6076",
        "1.18": "bda6fe24314e",
        "1.28": "ca7293c38970",
        "0.2.0": "7552df94427a",  # Extralit v0.2.0
        "2.0": "237f7c674d74",
        "2.4": "660d6c6b3360",  # Extralit v0.3.0
        "2.5": "580a6553186f",
        "0.6.0": "7d6b33203390",  # Extralit v0.6.0
    }
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


def database_url_sync() -> str:
    """
    Returns a "sync" version of the configured database URL. This may be useful in cases we don't need
    an asynchronous connection, like running database migration inside the alembic script.
    """
    database_url = make_url(settings.database_url)
    return settings.database_url.replace(f"+{database_url.get_driver_name()}", "")


sync_engine = create_engine(database_url_sync(), **settings.database_engine_args)

async_engine = create_async_engine(settings.database_url, **settings.database_engine_args)

SyncSessionLocal = scoped_session(sessionmaker(autocommit=False, expire_on_commit=False, bind=sync_engine))

AsyncSessionLocal = async_sessionmaker(autocommit=False, expire_on_commit=False, bind=async_engine)


def get_sync_db() -> Generator[Session, None, None]:
    db = SyncSessionLocal()

    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async for db in _get_async_db():
        yield db


async def _get_async_db(isolation_level: IsolationLevel | None = None) -> AsyncGenerator[AsyncSession, None]:
    db: AsyncSession = AsyncSessionLocal()

    if isolation_level is not None:
        await db.connection(execution_options={"isolation_level": isolation_level})

    try:
        yield db
    finally:
        await db.close()


def is_db_connection_error(exception):
    """Custom filter to only retry on actual connection loss, not bad SQL syntax."""
    error_msg = str(exception).lower()

    # Check for standard SQLAlchemy connection errors
    if isinstance(
        exception, OperationalError | DBAPIError | DisconnectionError | TimeoutError | ConnectionRefusedError | OSError
    ):
        return True

    # Check for asyncpg-specific connection errors
    if ASYNCPG_AVAILABLE and asyncpg is not None:
        try:
            if isinstance(exception, asyncpg.exceptions.InternalServerError):
                if (
                    "MaxClientsInSessionMode" in error_msg
                    or "max clients reached" in error_msg
                    or "pool_size" in error_msg
                ):
                    return True
        except AttributeError:
            pass

    # Check for other connection-related error messages
    if any(
        msg in error_msg
        for msg in [
            "connection was closed",
            "connection does not exist",
            "connection timed out",
            "connection refused",
            "connection reset",
            "broken pipe",
            "network is unreachable",
            "no route to host",
            "connection aborted",
            "queuepool limit",  # Pool exhaustion
            "timeout 30.00",  # Pool timeout
            "errno 111",  # Connection refused errno
            "errno 110",  # Connection timed out errno
        ]
    ):
        return True

    return False


def before_retry_log_and_pool_status(retry_state):
    """Log both retry attempt and connection pool status."""
    before_sleep_log(logger, logging.WARNING)(retry_state)
    _log_connection_pool_status()


# Reusable decorator
db_retry_policy = retry(
    # Retry only on connection errors using custom filter
    retry=is_db_connection_error,
    # Wait 0.1s, then 0.2s, then 0.4s... up to 2 seconds
    wait=wait_exponential(multiplier=0.1, min=0.1, max=2),
    # Stop after 3 attempts
    stop=stop_after_attempt(3),
    # Log before retrying and check pool status
    before_sleep=before_retry_log_and_pool_status,
)
