"""Workspace-scoped Lance datasets for extracted layout.

One `items`/`pages` dataset per workspace, so a corpus-wide question is a single scan instead of a
glob over one small object per document. A document's rows are deleted before they are appended,
which is what keeps a re-parse from leaving two vintages behind — and because that is two commits,
every writer holds the workspace lock across the pair.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from contextlib import asynccontextmanager, contextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

import lance
import pyarrow as pa
from anyio import to_thread
from lance.commit import CommitConflictError

from extralit_server.contexts.files import ObjectStorage
from extralit_server.contexts.ocr.arrow import ITEM_SCHEMA, PAGE_SCHEMA
from extralit_server.jobs.queues import REDIS_CONNECTION

if TYPE_CHECKING:
    import duckdb

_LOGGER = logging.getLogger("extralit_server.contexts.ocr.layout_store")

LAYOUT_PREFIX = "layout"
ITEMS_DATASET = "items"
PAGES_DATASET = "pages"
COMPACT_FRAGMENT_THRESHOLD = 32
# Bounds how much settled data a compaction rewrites, at the cost of more files per workspace.
TARGET_ROWS_PER_FRAGMENT = 250_000
# Long enough that a running query never loses its files; the canonical JSON is the real history.
CLEANUP_OLDER_THAN = timedelta(minutes=15)
# Must outlast a compaction, which is the longest thing done under the lock.
LOCK_TTL_SECONDS = 600
LOCK_WAIT_SECONDS = 300
REPLACE_ATTEMPTS = 3

_SCHEMAS = {ITEMS_DATASET: ITEM_SCHEMA, PAGES_DATASET: PAGE_SCHEMA}

# Lance's SQL type names for `add_columns`; anything else needs a real migration, not a NULL fill.
_SQL_TYPES = {
    pa.string(): "string",
    pa.bool_(): "boolean",
    pa.int8(): "tinyint",
    pa.int16(): "smallint",
    pa.int32(): "int",
    pa.int64(): "bigint",
    pa.float32(): "float",
    pa.float64(): "double",
}


def layout_root(workspace_name: str) -> tuple[str, Optional[dict[str, str]]]:
    """Root of the workspace's datasets, resolved exactly like every other artifact of it."""
    storage = ObjectStorage()
    return storage.lance_uri(workspace_name, LAYOUT_PREFIX), storage.lance_storage_options()


def _document_filter(document_id: UUID | str) -> str:
    """A UUID round-trip is the whole sanitisation — nothing else reaches the filter string."""
    return f"document_id = '{UUID(str(document_id))}'"


class LayoutStore:
    """Reader and writer of one workspace's layout datasets.

    Writers must hold `locked()`/`locked_sync()`: replacing a document is a delete commit followed
    by an append commit, and two interleaved replaces would otherwise drop or double rows. Lance's
    own commit conflict detection is the belt to that lock's braces.
    """

    def __init__(self, root_uri: str, storage_options: Optional[dict[str, str]] = None) -> None:
        self.root_uri = root_uri.rstrip("/")
        self.storage_options = storage_options
        self._lock_depth = 0
        self._lock = None

    @classmethod
    def for_workspace(cls, workspace_name: str) -> LayoutStore:
        return cls(*layout_root(workspace_name))

    def uri(self, name: str) -> str:
        return f"{self.root_uri}/{name}.lance"

    def items_uri(self) -> str:
        return self.uri(ITEMS_DATASET)

    def pages_uri(self) -> str:
        return self.uri(PAGES_DATASET)

    # --- locking -------------------------------------------------------------------------------

    def _acquire(self) -> None:
        if self._lock_depth == 0:
            # The resolved root, not the display name: a renamed workspace must not fork the lock.
            lock = REDIS_CONNECTION.lock(
                f"extralit:layout:{self.root_uri}",
                timeout=LOCK_TTL_SECONDS,
                blocking_timeout=LOCK_WAIT_SECONDS,
                thread_local=False,
            )
            if not lock.acquire():
                raise TimeoutError(f"Timed out waiting for the layout lock on {self.root_uri}")
            self._lock = lock
        self._lock_depth += 1

    def _release(self) -> None:
        self._lock_depth -= 1
        if self._lock_depth == 0 and self._lock is not None:
            lock, self._lock = self._lock, None
            try:
                lock.release()
            except Exception as error:
                # Expired by TTL, or already taken over: the write itself has already committed.
                _LOGGER.warning(f"Could not release the layout lock on {self.root_uri}: {error}")

    @contextmanager
    def locked_sync(self) -> Iterator[None]:
        """Serialize this workspace's writers. Reentrant per store instance."""
        self._acquire()
        try:
            yield
        finally:
            self._release()

    @asynccontextmanager
    async def locked(self):
        """`locked_sync` for async callers; acquisition blocks, so it happens off the event loop."""
        await to_thread.run_sync(self._acquire)
        try:
            yield
        finally:
            await to_thread.run_sync(self._release)

    # --- writes --------------------------------------------------------------------------------

    def open(self, name: str) -> Optional[lance.LanceDataset]:
        try:
            return lance.dataset(self.uri(name), storage_options=self.storage_options)
        except (ValueError, FileNotFoundError):
            return None

    def _write(self, name: str, data: pa.Table, mode: str) -> int:
        return lance.write_dataset(data, self.uri(name), mode=mode, storage_options=self.storage_options).version

    def _add_missing_columns(self, dataset: lance.LanceDataset, schema: pa.Schema) -> lance.LanceDataset:
        """Widen a dataset written under an older schema; new columns are NULL for the rows already there."""
        missing = [field for field in schema if field.name not in dataset.schema.names]
        if not missing:
            return dataset
        dataset.add_columns({field.name: f"CAST(NULL AS {_SQL_TYPES[field.type]})" for field in missing})
        return lance.dataset(dataset.uri, storage_options=self.storage_options)

    def _replace_one(self, name: str, document_id: UUID | str, data: pa.Table) -> int:
        dataset = self.open(name)
        if dataset is None:
            try:
                return self._write(name, data, mode="create")
            except OSError:
                # Another worker created it between the open and the write; join it instead.
                dataset = lance.dataset(self.uri(name), storage_options=self.storage_options)

        dataset = self._add_missing_columns(dataset, data.schema)
        dataset.delete(_document_filter(document_id))
        if data.num_rows == 0:
            return lance.dataset(self.uri(name), storage_options=self.storage_options).version
        return self._write(name, data, mode="append")

    def replace_document(self, document_id: UUID | str, items: pa.Table, pages: pa.Table) -> dict[str, int]:
        """Swap this document's rows for `items`/`pages`. Caller must hold the workspace lock."""
        versions = {}
        for name, data in ((ITEMS_DATASET, items), (PAGES_DATASET, pages)):
            for attempt in range(1, REPLACE_ATTEMPTS + 1):
                try:
                    versions[f"{name}_version"] = self._replace_one(name, document_id, data)
                    break
                except CommitConflictError:
                    # Retry the delete and the append together; half a replace is a corrupt vintage.
                    if attempt == REPLACE_ATTEMPTS:
                        raise
                    _LOGGER.warning(f"Commit conflict on {self.uri(name)}, retrying the whole replace")
        return versions

    def delete_document(self, document_id: UUID | str) -> None:
        """Drop this document's rows. Caller must hold the workspace lock."""
        condition = _document_filter(document_id)
        for name in (ITEMS_DATASET, PAGES_DATASET):
            dataset = self.open(name)
            if dataset is not None:
                dataset.delete(condition)

    # --- reads ---------------------------------------------------------------------------------

    def _read(
        self,
        name: str,
        document_id: UUID | str,
        columns: Optional[Sequence[str]] = None,
        where: Optional[str] = None,
    ) -> pa.Table:
        condition = _document_filter(document_id)
        projection = list(columns) if columns else None
        dataset = self.open(name)
        if dataset is None:
            empty = pa.Table.from_pylist([], schema=_SCHEMAS[name])
            return empty.select(projection) if projection else empty
        return dataset.to_table(filter=f"({condition}) AND ({where})" if where else condition, columns=projection)

    def load_items(self, document_id: UUID | str, columns=None, where: Optional[str] = None) -> pa.Table:
        return self._read(ITEMS_DATASET, document_id, columns=columns, where=where)

    def load_pages(self, document_id: UUID | str, columns=None, where: Optional[str] = None) -> pa.Table:
        return self._read(PAGES_DATASET, document_id, columns=columns, where=where)

    def source(self, name: str) -> Any:
        """The dataset, or an empty table of the right schema when nothing has been written yet."""
        dataset = self.open(name)
        return dataset if dataset is not None else pa.Table.from_pylist([], schema=_SCHEMAS[name])

    # --- maintenance ---------------------------------------------------------------------------

    def maybe_compact(self) -> None:
        """Best effort: a failed compaction must never fail the extraction that triggered it."""
        for name in (ITEMS_DATASET, PAGES_DATASET):
            try:
                dataset = self.open(name)
                if dataset is None or len(dataset.get_fragments()) <= COMPACT_FRAGMENT_THRESHOLD:
                    continue
                # `compact_files` advances the handle in place, so cleanup sees the new version.
                dataset.optimize.compact_files(target_rows_per_fragment=TARGET_ROWS_PER_FRAGMENT)
                dataset.cleanup_old_versions(older_than=CLEANUP_OLDER_THAN)
            except Exception as error:
                _LOGGER.warning(f"Layout compaction of {name} at {self.root_uri} failed: {error}")


@contextmanager
def duckdb_connection(workspaces: Sequence[str]) -> Iterator[duckdb.DuckDBPyConnection]:
    """`items` and `pages` as DuckDB views over one or more workspaces.

    Lance datasets take the projection and the filter, so `select label, count(*)` never reads the
    text column. Aggregating N workspaces is a loop over their roots, not a catalog.
    """
    import duckdb

    connection = duckdb.connect()
    try:
        for name in (ITEMS_DATASET, PAGES_DATASET):
            branches = []
            for index, workspace_name in enumerate(workspaces):
                alias = f"_{name}_{index}"
                connection.register(alias, LayoutStore.for_workspace(workspace_name).source(name))
                branches.append(f"select * from {alias}")
            connection.execute(f"create view {name} as {' union all '.join(branches)}")
        yield connection
    finally:
        connection.close()
