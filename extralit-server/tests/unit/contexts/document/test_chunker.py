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

"""Tests for the chonkie-based text chunker."""

import pytest

from extralit_server.contexts.document.chunker import chunk_text


class TestChunkText:
    """Tests for chunk_text using chonkie RecursiveChunker."""

    def test_empty_string_returns_empty(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_text("   \n\t  ") == []

    def test_short_text_single_chunk(self):
        text = "Hello world. This is a short sentence."
        chunks = chunk_text(text, chunk_size=512)
        assert len(chunks) >= 1
        # The full text should appear in the chunk(s)
        combined = " ".join(c["text"] for c in chunks)
        assert "Hello world" in combined

    def test_chunk_dict_keys(self):
        text = "Some sample text for testing the chunker output format."
        chunks = chunk_text(text, chunk_size=512)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "text" in chunk
            assert "start_index" in chunk
            assert "end_index" in chunk
            assert "token_count" in chunk
            assert isinstance(chunk["text"], str)
            assert isinstance(chunk["start_index"], int)
            assert isinstance(chunk["end_index"], int)
            assert isinstance(chunk["token_count"], int)

    def test_long_text_produces_multiple_chunks(self):
        # Create text that exceeds a single chunk
        text = ("This is a paragraph of text. " * 200)
        chunks = chunk_text(text, chunk_size=64)
        assert len(chunks) > 1

    def test_token_count_positive(self):
        text = "The quick brown fox jumps over the lazy dog."
        chunks = chunk_text(text, chunk_size=512)
        for chunk in chunks:
            assert chunk["token_count"] > 0

    def test_start_end_index_ordering(self):
        text = ("Sentence number one. " * 100)
        chunks = chunk_text(text, chunk_size=32)
        for chunk in chunks:
            assert chunk["start_index"] < chunk["end_index"]

    def test_chunks_are_json_serialisable(self):
        import json

        text = "A simple test for JSON serialisation."
        chunks = chunk_text(text, chunk_size=512)
        # Should not raise
        serialised = json.dumps(chunks)
        assert isinstance(serialised, str)

    def test_custom_chunk_size(self):
        text = ("Word " * 500)
        chunks_small = chunk_text(text, chunk_size=32)
        chunks_large = chunk_text(text, chunk_size=256)
        # Smaller chunk size ⇒ more chunks
        assert len(chunks_small) > len(chunks_large)

    def test_table_header_and_body_are_merged(self):
        text = (
            "Table 2  Evaluation of the association between different genotypes of L119F-GSTe2 and the longevity "
            "of exposed mosquitoes\n\n"
            "Genotypes\n\nRR vs. SS\n\nRR vs. RS\n\nRS vs. SS\n\nR vs. S\n\n"
            "(D2-D5)\n\n(D6-D10)\n\nOR\n\n95% CI\n\nP\n\n"
            "2.6\n\n1.01-2.83\n\n0.02*\n\n"
            "3.04\n\n1.10-2.72\n\n0.004*\n\n"
            "6.47\n\n1.69-5.27\n\n< 0.0001*\n"
        )

        # Force base chunking to split, then verify table-aware merge rejoins it.
        chunks = chunk_text(text, chunk_size=160, merge_table_chunks=True)

        assert len(chunks) == 1
        assert "Table 2" in chunks[0]["text"]
        assert "0.004*" in chunks[0]["text"]

    def test_table_merge_can_be_disabled(self):
        text = (
            "Table 2  Evaluation of the association between different genotypes of L119F-GSTe2 and the longevity "
            "of exposed mosquitoes\n\n"
            "Genotypes\n\nRR vs. SS\n\nRR vs. RS\n\nRS vs. SS\n\nR vs. S\n\n"
            "(D2-D5)\n\n(D6-D10)\n\nOR\n\n95% CI\n\nP\n\n"
            "2.6\n\n1.01-2.83\n\n0.02*\n\n"
            "3.04\n\n1.10-2.72\n\n0.004*\n\n"
            "6.47\n\n1.69-5.27\n\n< 0.0001*\n"
        )

        chunks = chunk_text(text, chunk_size=160, merge_table_chunks=False)

        assert len(chunks) > 1
