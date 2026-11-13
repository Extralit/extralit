from __future__ import annotations

import pytest
from pydantic_ai import Embedder
from pydantic_ai.embeddings import TestEmbeddingModel

from extralit_server.contexts.retrieval.embedding import embed_documents, get_embedder
from extralit_server.contexts.retrieval.settings import RetrievalSettings


def test_empty_model_gives_no_embedder():
    assert get_embedder(RetrievalSettings(embedding_model="")) is None


def test_dimensions_and_passthrough_settings_reach_the_embedder():
    embedder = get_embedder(
        RetrievalSettings(
            embedding_model="test",
            embedding_dimensions=32,
            embedding_settings={"extra_headers": {"x": "1"}},
        )
    )

    assert embedder._settings == {"truncate": True, "extra_headers": {"x": "1"}, "dimensions": 32}


@pytest.mark.asyncio
async def test_documents_are_embedded_in_batches_in_order():
    calls = []

    class Recording(TestEmbeddingModel):
        async def embed(self, inputs, *, input_type, settings=None):
            calls.append(list(inputs))
            return await super().embed(inputs, input_type=input_type, settings=settings)

    vectors = await embed_documents(Embedder(Recording(dimensions=4)), list("abcde"), batch_size=2)

    assert calls == [["a", "b"], ["c", "d"], ["e"]]
    assert len(vectors) == 5 and len(vectors[0]) == 4
