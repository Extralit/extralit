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

"""Context-aware semantic chunking using chonkie's RecursiveChunker.

Uses ``RecursiveChunker.from_recipe("markdown")`` which applies a hierarchy
of Markdown-aware splitting rules:

1. Markdown headers (``#`` through ``######``), kept attached to subsequent
   text via ``include_delim="next"``.
2. Double newlines (``\\n\\n``) for paragraph boundaries.
3. Single newlines, then sentence-ending punctuation (``.``, ``!``, ``?``).

This produces semantically contiguous chunks aligned with document sections
instead of fixed-size token windows.

See https://docs.chonkie.ai/oss/chunkers/recursive-chunker
"""

from __future__ import annotations

import logging
import re
from typing import Any

from chonkie import RecursiveChunker

_LOGGER = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 2048
DEFAULT_TABLE_CHUNK_SIZE = 900

_TABLE_HEADER_RE = re.compile(r"^\s*Table\s+\d+\b", re.IGNORECASE)
_TABLE_TERM_RE = re.compile(r"\b(?:OR|CI|P|Genotypes|RR|RS|SS)\b")
_TABLE_INTERVAL_RE = re.compile(r"\(D\d+\s*[-–]\s*D\d+\)|\(D\d+\)")


def _is_table_header(text: str) -> bool:
    """Return True if *text* starts with a table heading."""
    return bool(_TABLE_HEADER_RE.match(text.strip()))


def _looks_like_table_continuation(text: str) -> bool:
    """Heuristically identify table-like continuation fragments.

    Scientific PDFs often extract table cells as many short lines. This helper
    flags those chunks so we can keep table header/body together.
    """
    stripped = text.strip()
    if not stripped:
        return False

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) < 4:
        return False

    short_line_count = sum(1 for line in lines if len(line) <= 20)
    numeric_like_count = sum(1 for line in lines if re.search(r"\d|%|±|×|<|>", line))
    has_table_terms = _TABLE_TERM_RE.search(stripped) is not None
    has_intervals = _TABLE_INTERVAL_RE.search(stripped) is not None

    return (short_line_count / len(lines) >= 0.55) and (
        (numeric_like_count / len(lines) >= 0.35) or has_table_terms or has_intervals
    )


def _merge_adjacent_table_chunks(chunks: list[dict[str, Any]], max_table_chunk_size: int) -> list[dict[str, Any]]:
    """Merge table heading + continuation chunks to preserve table context."""
    if not chunks:
        return []

    merged: list[dict[str, Any]] = []
    i = 0

    while i < len(chunks):
        current = dict(chunks[i])

        if _is_table_header(current.get("text", "")) and i + 1 < len(chunks):
            while i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                next_text = next_chunk.get("text", "")
                combined_token_count = current.get("token_count", 0) + next_chunk.get("token_count", 0)

                if combined_token_count > max_table_chunk_size:
                    break

                if not _looks_like_table_continuation(next_text):
                    break

                current["text"] = f"{current.get('text', '')}{next_text}"
                current["end_index"] = next_chunk.get("end_index", current.get("end_index"))
                current["token_count"] = combined_token_count
                i += 1

        merged.append(current)
        i += 1

    return merged


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    merge_table_chunks: bool = True,
    max_table_chunk_size: int = DEFAULT_TABLE_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """Chunk *text* using chonkie's Markdown-aware ``RecursiveChunker``.

    Splits on Markdown headers first, then paragraph breaks, then
    sentences — producing semantically contiguous, section-aligned chunks.

    Returns a list of plain dicts (JSON-serialisable) with keys:
        - ``text``: the chunk content
        - ``start_index``: character start offset in the original text
        - ``end_index``: character end offset in the original text
        - ``token_count``: number of tokens in the chunk
    """
    if not text or not text.strip():
        return []

    chunker = RecursiveChunker.from_recipe(
        "markdown",
        lang="en",
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

    if merge_table_chunks:
        result = _merge_adjacent_table_chunks(result, max_table_chunk_size=max_table_chunk_size)

    _LOGGER.debug(
        "Chunked %d chars into %d chunks (size=%d, merge_table_chunks=%s)",
        len(text), len(result), chunk_size, merge_table_chunks,
    )
    return result
