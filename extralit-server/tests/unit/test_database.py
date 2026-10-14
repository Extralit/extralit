import pytest
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import text


@pytest.mark.asyncio
class TestDatabase:
    async def test_sqlite_pragma_settings(self, db: AsyncSession):
        if db.bind.dialect.name != sqlite.dialect.name:
            return

        assert (await db.execute(text("PRAGMA foreign_keys"))).scalar() == 1
