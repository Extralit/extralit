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

"""Markdown-aware document chunking with chonkie's `RecursiveChunker`.

The splitting hierarchy is configuration, not code: it is read from a YAML file
(`chunking_rules.yaml` next to this module, or `settings.chunking_rules_path`) into chonkie's
`RecursiveRules`, so splitting runs in chonkie rather than in Python loops over the text.

Tables need no special casing. Chunks are cut from the Markdown export of the canonical
`DoclingDocument`, where the layout parser has already identified each table and docling renders
it as one contiguous block of rows. The rules split at blank lines before rows, so a table stays
whole unless it alone is larger than `chunk_size`.

See https://docs.chonkie.ai/oss/chunkers/recursive-chunker
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from chonkie import RecursiveChunker, RecursiveRules
from docling_core.types.doc import DoclingDocument
from pydantic import BaseModel, Field

from extralit_server.settings import settings

_LOGGER = logging.getLogger(__name__)

DEFAULT_RULES_PATH = Path(__file__).with_name("chunking_rules.yaml")


class ChunkerConfig(BaseModel):
    """What a chunking rules YAML file holds."""

    tokenizer: str = Field("character", description="chonkie tokenizer name; `character` counts characters")
    chunk_size: int = Field(2048, gt=0, description="Maximum tokens per chunk")
    min_characters_per_chunk: int = Field(24, ge=1, description="Shortest piece kept as a split of its own")
    rules: dict[str, Any] = Field(..., description="chonkie `RecursiveRules.from_dict` payload")


def rules_path() -> Path:
    """The configured rules file, falling back to the one shipped with the server."""
    configured = settings.chunking_rules_path
    return Path(configured) if configured else DEFAULT_RULES_PATH


@lru_cache(maxsize=8)
def load_config(path: Path) -> ChunkerConfig:
    """Parse and validate a rules file. Cached: the file is read once per process."""
    with open(path, encoding="utf-8") as f:
        return ChunkerConfig.model_validate(yaml.safe_load(f))


@lru_cache(maxsize=8)
def get_chunker(path: Path, chunk_size: Optional[int] = None) -> RecursiveChunker:
    """Build the chunker for a rules file once; chonkie chunkers are stateless between calls."""
    config = load_config(path)
    return RecursiveChunker(
        tokenizer=config.tokenizer,
        chunk_size=chunk_size or config.chunk_size,
        rules=RecursiveRules.from_dict(config.rules),
        min_characters_per_chunk=config.min_characters_per_chunk,
    )


def chunk_text(
    text: str,
    *,
    chunk_size: Optional[int] = None,
    path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Chunk Markdown `text` with the configured recursive rules.

    Args:
        text: Markdown to split.
        chunk_size: Overrides the rules file's `chunk_size`.
        path: Rules file; defaults to `rules_path()`.

    Returns:
        JSON-serialisable dicts with `text`, `start_index` and `end_index` (character offsets
        into `text`) and `token_count`, in document order.
    """
    if not text or not text.strip():
        return []

    chunker = get_chunker(path or rules_path(), chunk_size)
    return [
        {
            "text": chunk.text,
            "start_index": chunk.start_index,
            "end_index": chunk.end_index,
            "token_count": chunk.token_count,
        }
        for chunk in chunker.chunk(text)
    ]


def document_markdown(doc: DoclingDocument) -> str:
    """Body content as Markdown, rendered by docling: page headers and footers are furniture and
    stay out, tables become Markdown tables, pictures leave no placeholder text behind."""
    return doc.export_to_markdown(image_placeholder="")


def chunk_document(
    doc: DoclingDocument,
    *,
    chunk_size: Optional[int] = None,
    path: Optional[Path] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Render `doc` to Markdown and chunk it.

    Returns the Markdown alongside the chunks, because chunk offsets index into it.
    """
    markdown = document_markdown(doc)
    chunks = chunk_text(markdown, chunk_size=chunk_size, path=path)
    _LOGGER.debug(f"Chunked {len(markdown)} chars of {doc.name!r} into {len(chunks)} chunks")
    return markdown, chunks
