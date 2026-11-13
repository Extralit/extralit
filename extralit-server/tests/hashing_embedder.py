"""Deterministic, text-dependent embeddings; `TestEmbeddingModel` returns a constant vector."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import xxhash
from pydantic_ai.embeddings import EmbeddingModel, EmbeddingResult, EmbeddingSettings


class HashingEmbeddingModel(EmbeddingModel):
    def __init__(self, dimensions: int) -> None:
        super().__init__()
        self.dimensions = dimensions

    @property
    def model_name(self) -> str:
        return "hashing"

    @property
    def system(self) -> str:
        return "test"

    async def embed(
        self, inputs: str | Sequence[str], *, input_type, settings: EmbeddingSettings | None = None
    ) -> EmbeddingResult:
        texts, _ = self.prepare_embed(inputs, settings)
        vectors = [
            np.random.default_rng(xxhash.xxh64_intdigest(t.encode()))
            .standard_normal(self.dimensions)
            .astype(float)
            .tolist()
            for t in texts
        ]
        return EmbeddingResult(
            embeddings=vectors, inputs=texts, input_type=input_type, model_name=self.model_name, provider_name="test"
        )
