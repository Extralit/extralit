"""Retrieval configuration, read from `EXTRALIT_RETRIEVAL_*`."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXTRALIT_RETRIEVAL_", extra="ignore")

    # A pydantic-ai model string such as "openai:text-embedding-3-small"; empty means full-text search only.
    embedding_model: str = ""
    embedding_dimensions: Optional[int] = Field(default=None, gt=0)
    # Provider-specific `EmbeddingSettings` fields, as JSON in the environment.
    embedding_settings: dict[str, Any] = Field(default_factory=dict)
    embedding_batch_size: int = Field(default=64, gt=0)
    rrf_k: int = Field(default=60, gt=0)
    candidate_k: int = Field(default=50, gt=0)
