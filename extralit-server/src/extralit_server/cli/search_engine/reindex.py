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
from collections.abc import AsyncGenerator
from typing import Optional
from uuid import UUID

import typer
from rich.progress import Progress
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, DisconnectionError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.cli.rich import echo_in_panel
from extralit_server.database import AsyncSessionLocal, db_retry_policy
from extralit_server.models import Dataset, Record, Response, Suggestion
from extralit_server.search_engine import SearchEngine, get_search_engine


class Reindexer:
    YIELD_PER = 100

    @classmethod
    @db_retry_policy
    async def reindex_dataset(cls, db: AsyncSession, search_engine: SearchEngine, dataset_id: UUID) -> Dataset:
        dataset = (
            await db.execute(
                select(Dataset)
                .filter_by(id=dataset_id)
                .options(
                    selectinload(Dataset.fields),
                    selectinload(Dataset.questions),
                    selectinload(Dataset.metadata_properties),
                    selectinload(Dataset.vectors_settings),
                )
            )
        ).scalar_one()

        await search_engine.delete_index(dataset)
        await search_engine.create_index(dataset)

        return dataset

    @classmethod
    async def reindex_datasets(cls, db: AsyncSession, search_engine: SearchEngine) -> AsyncGenerator[Dataset, None]:
        @db_retry_policy
        async def _get_datasets_batch(offset: int = 0, limit: int = cls.YIELD_PER):
            """Get a batch of datasets with retry logic"""
            return await db.execute(
                select(Dataset)
                .order_by(Dataset.inserted_at.asc())
                .options(
                    selectinload(Dataset.fields),
                    selectinload(Dataset.questions),
                    selectinload(Dataset.metadata_properties),
                    selectinload(Dataset.vectors_settings),
                )
                .offset(offset)
                .limit(limit)
            )

        # Process datasets in batches instead of streaming to avoid long transactions
        offset = 0
        while True:
            try:
                result = await _get_datasets_batch(offset, cls.YIELD_PER)
                datasets = result.scalars().all()

                if not datasets:
                    break

                for dataset in datasets:
                    await search_engine.delete_index(dataset)
                    await search_engine.create_index(dataset)
                    yield dataset

                offset += cls.YIELD_PER

            except (DBAPIError, DisconnectionError) as e:
                # Log error and ensure clean session state
                echo_in_panel(
                    f"Database connection error during dataset batch at offset {offset}: {e}",
                    title="Connection Warning",
                    title_align="left",
                    success=False,
                )
                # Rollback any invalid transaction
                try:
                    await db.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                # Skip this batch and continue
                offset += cls.YIELD_PER
                continue

    @classmethod
    async def reindex_dataset_records(
        cls, db: AsyncSession, search_engine: SearchEngine, dataset: Dataset
    ) -> AsyncGenerator[list[Record], None]:
        @db_retry_policy
        async def _get_records_batch(offset: int = 0, limit: int = cls.YIELD_PER):
            """Get a batch of records with retry logic"""
            return await db.execute(
                select(Record)
                .filter_by(dataset_id=dataset.id)
                .order_by(Record.inserted_at.asc())
                .options(
                    selectinload(Record.responses).selectinload(Response.user),
                    selectinload(Record.suggestions).selectinload(Suggestion.question),
                    selectinload(Record.vectors),
                )
                .offset(offset)
                .limit(limit)
            )

        # Process records in batches instead of streaming to avoid long transactions
        offset = 0
        while True:
            try:
                result = await _get_records_batch(offset, cls.YIELD_PER)
                records = result.scalars().all()

                if not records:
                    break

                # Convert ScalarResult to list for consistency with original API
                records_list = [record for record in records]

                if records_list:  # Only index if we have records
                    await search_engine.index_records(dataset, records_list)
                yield records_list

                offset += cls.YIELD_PER

            except (DBAPIError, DisconnectionError) as e:
                # Log error and ensure clean session state
                echo_in_panel(
                    f"Database connection error during records batch for dataset {dataset.name} at offset {offset}: {e}",
                    title="Connection Warning",
                    title_align="left",
                    success=False,
                )
                # Rollback any invalid transaction
                try:
                    await db.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                # Skip this batch and continue
                offset += cls.YIELD_PER
                continue

    @classmethod
    @db_retry_policy
    async def count_datasets(cls, db: AsyncSession) -> int:
        return (await db.execute(select(func.count(Dataset.id)))).scalar_one()

    @classmethod
    @db_retry_policy
    async def count_dataset_records(cls, db: AsyncSession, dataset: Dataset) -> int:
        return (await db.execute(select(func.count(Record.id)).filter_by(dataset_id=dataset.id))).scalar_one()

    @classmethod
    async def get_all_index_names(cls, search_engine: SearchEngine) -> list[str]:
        index_names = await search_engine.get_all_index_names()
        return index_names


async def _reindex_dataset(db: AsyncSession, search_engine: SearchEngine, progress: Progress, dataset_id: UUID) -> None:
    try:
        dataset = await Reindexer.reindex_dataset(db, search_engine, dataset_id)
    except NoResultFound as e:
        echo_in_panel(
            f"Dataset with id={dataset_id} not found.",
            title="Dataset not found",
            title_align="left",
            success=False,
        )

        raise typer.Exit(code=1) from e

    task = progress.add_task(f"reindexing dataset `{dataset.name}`...", total=1)

    await _reindex_dataset_records(db, search_engine, progress, dataset)

    progress.advance(task)


async def _reindex_datasets(db: AsyncSession, search_engine: SearchEngine, progress: Progress) -> None:
    # Get total count with retry logic
    try:
        total_datasets = await Reindexer.count_datasets(db)
    except Exception as e:
        echo_in_panel(
            f"Failed to count datasets: {e!s}. Proceeding without progress tracking.",
            title="Count Warning",
            title_align="left",
            success=False,
        )
        total_datasets = None

    task = progress.add_task("reindexing datasets...", total=total_datasets)

    async for dataset in Reindexer.reindex_datasets(db, search_engine):
        try:
            await _reindex_dataset_records(db, search_engine, progress, dataset)
        except Exception as e:
            echo_in_panel(
                f"Failed to reindex dataset `{dataset.name}`: {e!s}",
                title="Reindexing Error",
                title_align="left",
                success=False,
            )
            # Rollback any invalid transaction state
            try:
                await db.rollback()
            except Exception:
                pass  # Ignore rollback errors
        finally:
            progress.advance(task)


async def _reindex_dataset_records(
    db: AsyncSession, search_engine: SearchEngine, progress: Progress, dataset: Dataset
) -> None:
    # Get record count with retry logic
    try:
        total_records = await Reindexer.count_dataset_records(db, dataset)
    except Exception as e:
        echo_in_panel(
            f"Failed to count records for dataset {dataset.name}: {e!s}. Proceeding without progress tracking.",
            title="Count Warning",
            title_align="left",
            success=False,
        )
        total_records = None

    task = progress.add_task(
        f"reindexing dataset `{dataset.name}` records...",
        total=total_records,
    )

    try:
        async for records in Reindexer.reindex_dataset_records(db, search_engine, dataset):
            progress.advance(task, advance=len(records))
    except Exception as e:
        echo_in_panel(
            f"Failed to reindex records for dataset {dataset.name}: {e!s}",
            title="Records Reindexing Error",
            title_align="left",
            success=False,
        )
        # Rollback any invalid transaction state
        try:
            await db.rollback()
        except Exception:
            pass  # Ignore rollback errors
        raise  # Re-raise to be handled by caller


async def _reindex(dataset_id: Optional[UUID] = None) -> None:
    async with AsyncSessionLocal() as db:
        async for search_engine in get_search_engine():
            with Progress() as progress:
                if dataset_id is not None:
                    await _reindex_dataset(db, search_engine, progress, dataset_id)
                else:
                    await _reindex_datasets(db, search_engine, progress)


async def list_indexes() -> None:
    async for search_engine in get_search_engine():
        index_names = await Reindexer.get_all_index_names(search_engine)
        for index_name in index_names or []:
            typer.echo(index_name)


def reindex(
    dataset_id: Optional[UUID] = typer.Option(None, help="The id of a dataset to be reindexed"),
) -> None:
    asyncio.run(_reindex(dataset_id))


def list() -> None:
    asyncio.run(list_indexes())


if __name__ == "__main__":
    typer.run(reindex)
