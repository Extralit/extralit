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

"""Document text chunking using chonkie's RecursiveChunker.

See https://docs.chonkie.ai/oss/chunkers/recursive-chunker
"""

from __future__ import annotations

import logging
from typing import Any

from chonkie import RecursiveChunker

_LOGGER = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """Chunk *text* using chonkie's ``RecursiveChunker``.

    Returns a list of plain dicts (JSON-serialisable) with keys:
        - ``text``: the chunk content
        - ``start_index``: character start offset in the original text
        - ``end_index``: character end offset in the original text
        - ``token_count``: number of tokens in the chunk
    """
    if not text or not text.strip():
        return []

    chunker = RecursiveChunker(
        chunk_size=chunk_size,
    )

    chunks = chunker.chunk(text)

    result: list[dict[str, Any]] = []
    for chunk in chunks:
        result.append({
            "text": chunk.text,
            "start_index": chunk.start_index,
            "end_index": chunk.end_index,
            "token_count": chunk.token_count,
        })

    _LOGGER.debug(
        "Chunked %d chars into %d chunks (size=%d)",
        len(text), len(result), chunk_size,
    )
    return result
