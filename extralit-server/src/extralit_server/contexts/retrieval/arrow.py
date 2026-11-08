"""Arrow schemas of the `chunks` dataset."""

from __future__ import annotations

import re

import pyarrow as pa

CHUNKS_DATASET = "chunks"
VECTOR_PREFIX = "vector__"
EMBEDDING_MODEL_KEY = "embedding_model"
DIMENSIONS_KEY = "dimensions"

CHUNK_SCHEMA = pa.schema(
    [
        ("chunk_id", pa.string()),
        ("document_id", pa.string()),
        ("reference", pa.string()),
        ("ordinal", pa.int32()),
        ("kind", pa.dictionary(pa.int8(), pa.string())),
        ("text", pa.string()),
        ("embed_text", pa.string()),
        ("headings", pa.list_(pa.string())),
        ("item_refs", pa.list_(pa.string())),
        ("page_start", pa.int32()),
        ("page_end", pa.int32()),
        ("chunker_fingerprint", pa.string()),
    ]
)


def model_slug(model: str) -> str:
    """Column-safe form of a pydantic-ai model string."""
    return re.sub(r"[^0-9a-z]+", "_", model.lower()).strip("_")


def vector_column(model: str) -> str:
    return f"{VECTOR_PREFIX}{model_slug(model)}"


def vector_field(model: str, dim: int) -> pa.Field:
    """Nullable `fixed_size_list<f32, dim>` column for `model`, tagged with what it holds."""
    return pa.field(
        vector_column(model),
        pa.list_(pa.field("item", pa.float32()), dim),
        nullable=True,
        metadata={EMBEDDING_MODEL_KEY: model, DIMENSIONS_KEY: str(dim)},
    )
