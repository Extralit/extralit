"""`chunks` dataset beside `items`/`pages`, with one nullable vector column per embedding model."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import lance
import pyarrow as pa

from extralit_server.contexts.ocr.layout_store import LayoutStore
from extralit_server.contexts.retrieval.arrow import (
    CHUNK_SCHEMA,
    CHUNKS_DATASET,
    DIMENSIONS_KEY,
    EMBEDDING_MODEL_KEY,
    VECTOR_PREFIX,
    vector_column,
    vector_field,
)

_LOGGER = logging.getLogger("extralit_server.contexts.retrieval.store")

TEXT_INDEX = "chunks_text_idx"
VECTOR_INDEX_TYPE = "IVF_HNSW_FLAT"


class DimensionMismatchError(ValueError):
    """The model already has a vector column of another size or identity."""


def _document_filter(document_id: UUID | str) -> str:
    return f"document_id = '{UUID(str(document_id))}'"


class ChunkStore:
    """Reader and writer of one workspace's chunks. Writers must hold the layout store's lock."""

    def __init__(self, layout: LayoutStore) -> None:
        self.layout = layout
        layout.register_dataset(CHUNKS_DATASET, CHUNK_SCHEMA)

    @classmethod
    def for_workspace(cls, workspace_name: str) -> ChunkStore:
        return cls(LayoutStore.for_workspace(workspace_name))

    def open(self) -> Optional[lance.LanceDataset]:
        return self.layout.open(CHUNKS_DATASET)

    def source(self):
        return self.layout.source(CHUNKS_DATASET)

    # --- chunks --------------------------------------------------------------------------------

    def replace_chunks(self, document_id: UUID | str, table: pa.Table) -> None:
        """Make the document's chunks exactly `table`; unchanged `chunk_id`s keep their vectors."""
        condition = _document_filter(document_id)
        dataset = self.open()
        if dataset is None:
            lance.write_dataset(
                table, self.layout.uri(CHUNKS_DATASET), mode="create", storage_options=self.layout.storage_options
            )
        else:
            (
                dataset.merge_insert("chunk_id")
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .when_not_matched_by_source_delete(condition)
                .execute(table)
            )
        self.ensure_inverted_index()
        self._optimize()

    def ensure_inverted_index(self) -> None:
        dataset = self.open()
        if dataset is None or dataset.count_rows() == 0:
            return
        if TEXT_INDEX not in {index["name"] for index in dataset.list_indices()}:
            dataset.create_scalar_index("text", "INVERTED", name=TEXT_INDEX)

    def _optimize(self) -> None:
        dataset = self.open()
        if dataset is not None:
            dataset.optimize.optimize_indices()

    # --- vectors -------------------------------------------------------------------------------

    def vector_columns(self) -> dict[str, str]:
        """Embedding model -> column, read from field metadata."""
        dataset = self.open()
        if dataset is None:
            return {}
        columns = {}
        for field in dataset.schema:
            if field.name.startswith(VECTOR_PREFIX) and field.metadata:
                columns[field.metadata[EMBEDDING_MODEL_KEY.encode()].decode()] = field.name
        return columns

    def upsert_vectors(self, model: str, table: pa.Table) -> None:
        """Store `table`'s `chunk_id` + `vector__{slug}` column; only existing chunks are updated."""
        column = vector_column(model)
        if column not in table.column_names or "chunk_id" not in table.column_names:
            raise ValueError(f"Expected columns 'chunk_id' and {column!r}")
        vectors = table.schema.field(column).type
        if not pa.types.is_fixed_size_list(vectors):
            raise ValueError(f"{column!r} must be a fixed-size list of float32")
        dimensions = vectors.list_size

        dataset = self.open()
        if dataset is None:
            raise ValueError("No chunks have been written yet")

        existing = dataset.schema.get_field_index(column)
        if existing == -1:
            dataset.add_columns(pa.schema([vector_field(model, dimensions)]))
        else:
            metadata = dataset.schema.field(existing).metadata or {}
            stored_model = metadata.get(EMBEDDING_MODEL_KEY.encode(), b"").decode()
            stored_dimensions = metadata.get(DIMENSIONS_KEY.encode(), b"").decode()
            if stored_model != model or stored_dimensions != str(dimensions):
                raise DimensionMismatchError(
                    f"{column} holds {stored_model!r} at {stored_dimensions} dimensions, "
                    f"got {model!r} at {dimensions}; drop the column first"
                )

        payload = table.select(["chunk_id", column]).cast(
            pa.schema([CHUNK_SCHEMA.field("chunk_id"), vector_field(model, dimensions)])
        )
        dataset.merge_insert("chunk_id").when_matched_update_all().execute(payload)
        self._ensure_vector_index(column)
        self._optimize()

    def _ensure_vector_index(self, column: str) -> None:
        dataset = self.open()
        name = f"{column}_idx"
        if name in {index["name"] for index in dataset.list_indices()}:
            return
        if dataset.count_rows(filter=f"{column} IS NOT NULL") == 0:
            return
        dataset.create_index(column, VECTOR_INDEX_TYPE, name=name, num_partitions=1)

    def unembedded(self, model: str, document_id: Optional[UUID | str] = None) -> pa.Table:
        """`chunk_id`, `document_id` and `embed_text` of chunks that `model` has not embedded yet."""
        dataset = self.open()
        columns = ["chunk_id", "document_id", "embed_text"]
        if dataset is None:
            return pa.Table.from_pylist([], schema=CHUNK_SCHEMA).select(columns)
        column = vector_column(model)
        conditions = [f"{column} IS NULL"] if column in dataset.schema.names else []
        if document_id is not None:
            conditions.append(_document_filter(document_id))
        return dataset.to_table(columns=columns, filter=" AND ".join(conditions) or None)

    def drop_vector_column(self, model: str) -> None:
        dataset = self.open()
        column = vector_column(model)
        if dataset is not None and column in dataset.schema.names:
            dataset.drop_columns([column])
