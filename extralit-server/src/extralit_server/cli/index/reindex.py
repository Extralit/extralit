"""v2 index reindex CLI — the recovery path for the derived LanceDB index.

A lean twin of `cli/search_engine/reindex.py`: iterate schemas, and for each drop and
repopulate its Lance table from Postgres via `rebuild_schema_index`.
"""

import asyncio
from typing import Optional
from uuid import UUID

import typer
from rich.progress import Progress
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.cli.rich import echo_in_panel
from extralit_server.contexts.v2.index_sync import rebuild_schema_index
from extralit_server.database import AsyncSessionLocal
from extralit_server.index import get_index_engine
from extralit_server.index.base import IndexEngine
from extralit_server.models.v2 import Schema


class Reindexer:
    @classmethod
    async def reindex_schema(cls, db: AsyncSession, engine: IndexEngine, schema_id: UUID) -> int:
        schema = (await db.execute(select(Schema).filter_by(id=schema_id))).scalar_one()
        return await rebuild_schema_index(engine, db, schema)

    @classmethod
    async def reindex_all(cls, db: AsyncSession, engine: IndexEngine) -> int:
        schemas = (await db.execute(select(Schema).order_by(Schema.inserted_at.asc()))).scalars().all()
        for schema in schemas:
            await rebuild_schema_index(engine, db, schema)
        return len(schemas)


async def _reindex(schema_id: Optional[UUID] = None) -> None:
    async with AsyncSessionLocal() as db:
        async for engine in get_index_engine():
            with Progress() as progress:
                if schema_id is not None:
                    task = progress.add_task(f"reindexing schema {schema_id}...", total=1)
                    indexed = await Reindexer.reindex_schema(db, engine, schema_id)
                    progress.advance(task)
                    echo_in_panel(f"Reindexed {indexed} records.", title="Done", title_align="left")
                else:
                    schemas = await Reindexer.reindex_all(db, engine)
                    echo_in_panel(f"Reindexed {schemas} schema table(s).", title="Done", title_align="left")


async def _list_tables() -> None:
    async for engine in get_index_engine():
        for name in await engine.table_names():
            typer.echo(name)


def reindex(
    schema_id: Optional[UUID] = typer.Option(None, help="The id of a single schema to reindex"),
) -> None:
    asyncio.run(_reindex(schema_id))


def list_tables() -> None:
    asyncio.run(_list_tables())
