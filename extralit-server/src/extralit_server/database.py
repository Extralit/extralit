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

import asyncio
import logging
import os
from collections import OrderedDict
from collections.abc import AsyncGenerator, Callable, Generator
from functools import wraps
from typing import TypeVar

from sqlalchemy import create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import IsolationLevel
from sqlalchemy.exc import DBAPIError, DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

import extralit_server
from extralit_server.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

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


def retry_db_operation(max_retries: int = 3, delay: float = 0.1, backoff: float = 2.0):
    """
    Decorator to retry database operations on connection failures.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (DBAPIError, DisconnectionError) as e:
                    last_exception = e

                    # Check if this is a connection-related error
                    error_msg = str(e).lower()
                    if any(
                        msg in error_msg
                        for msg in [
                            "connection was closed",
                            "connection does not exist",
                            "connection timed out",
                            "connection refused",
                            "connection reset",
                            "broken pipe",
                        ]
                    ):
                        if attempt < max_retries:
                            logger.warning(
                                f"Database connection error on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                                f"Retrying in {current_delay:.2f}s..."
                            )
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                            continue

                    # Re-raise non-connection errors immediately
                    raise
                except Exception:
                    # Re-raise non-database errors immediately
                    raise

            # If all retries failed, raise the last exception
            if last_exception:
                logger.error(f"Database operation failed after {max_retries + 1} attempts: {last_exception}")
                raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
