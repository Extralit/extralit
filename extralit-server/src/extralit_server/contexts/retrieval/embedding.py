"""Embedder construction and batching over `pydantic_ai.Embedder`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

from extralit_server.contexts.retrieval.settings import RetrievalSettings


def get_embedder(settings: RetrievalSettings) -> Optional[Embedder]:
    """The configured embedder, or None when only full-text search is wanted."""
    if not settings.embedding_model:
        return None
    options: dict[str, Any] = {"truncate": True, **settings.embedding_settings}
    if settings.embedding_dimensions is not None:
        options["dimensions"] = settings.embedding_dimensions
    return Embedder(settings.embedding_model, settings=EmbeddingSettings(**options))


async def embed_documents(embedder: Embedder, texts: Sequence[str], batch_size: int) -> list[list[float]]:
    """Embed `texts` in order, `batch_size` per provider call (pydantic-ai does not batch)."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        result = await embedder.embed_documents(list(texts[start : start + batch_size]))
        vectors.extend(list(map(float, vector)) for vector in result.embeddings)
    return vectors
