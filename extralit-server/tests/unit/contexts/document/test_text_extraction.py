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

"""Tests for TextExtractionMetadata with chunks and the RQ job helper."""

import pytest

from extralit_server.api.schemas.v1.document.metadata import (
    ChunkMetadata,
    DocumentProcessingMetadata,
    TextExtractionMetadata,
)
from extralit_server.jobs.document_jobs import _extract_text_from_result


# ---------------------------------------------------------------------------
# ChunkMetadata / TextExtractionMetadata schema tests
# ---------------------------------------------------------------------------


class TestChunkMetadata:
    def test_create_chunk_metadata(self):
        cm = ChunkMetadata(text="hello", start_index=0, end_index=5, token_count=1)
        assert cm.text == "hello"
        assert cm.start_index == 0

    def test_text_extraction_with_chunks(self):
        chunks = [
            ChunkMetadata(text="chunk1", start_index=0, end_index=6, token_count=1),
            ChunkMetadata(text="chunk2", start_index=6, end_index=12, token_count=1),
        ]
        tem = TextExtractionMetadata(
            markdown="chunk1chunk2",
            extraction_method="external_ocr",
            chunks=chunks,
        )
        assert len(tem.chunks) == 2
        assert tem.chunks[0].text == "chunk1"

    def test_text_extraction_chunks_default_none(self):
        tem = TextExtractionMetadata(markdown="hi", extraction_method="ocr")
        assert tem.chunks is None


class TestUpdateTextExtractionResults:
    def test_updates_metadata(self):
        meta = DocumentProcessingMetadata()
        chunks = [
            {"text": "a", "start_index": 0, "end_index": 1, "token_count": 1},
            {"text": "b", "start_index": 1, "end_index": 2, "token_count": 1},
        ]
        meta.update_text_extraction_results(text="ab", chunks=chunks)
        assert meta.text_extraction_metadata is not None
        assert meta.text_extraction_metadata.markdown == "ab"
        assert len(meta.text_extraction_metadata.chunks) == 2
        assert meta.text_extraction_metadata.extraction_method == "external_ocr"

    def test_roundtrip_serialisation(self):
        meta = DocumentProcessingMetadata()
        chunks = [{"text": "x", "start_index": 0, "end_index": 1, "token_count": 1}]
        meta.update_text_extraction_results(text="x", chunks=chunks)
        dumped = meta.model_dump()
        restored = DocumentProcessingMetadata(**dumped)
        assert restored.text_extraction_metadata.chunks[0].text == "x"


# ---------------------------------------------------------------------------
# _extract_text_from_result helper tests
# ---------------------------------------------------------------------------


class TestExtractTextFromResult:
    def test_empty_dict(self):
        assert _extract_text_from_result({}) == ""

    def test_none(self):
        assert _extract_text_from_result(None) == ""

    def test_markdown_key(self):
        assert _extract_text_from_result({"markdown": "# Title"}) == "# Title"

    def test_text_key(self):
        assert _extract_text_from_result({"text": "hello"}) == "hello"

    def test_content_key(self):
        assert _extract_text_from_result({"content": "body"}) == "body"

    def test_pages_blocks_text(self):
        result = {
            "pages": [
                {"blocks": [{"text": "block1"}, {"text": "block2"}]},
                {"blocks": [{"text": "block3"}]},
            ]
        }
        text = _extract_text_from_result(result)
        assert "block1" in text
        assert "block2" in text
        assert "block3" in text

    def test_pages_blocks_html_stripped(self):
        result = {
            "pages": [{"blocks": [{"html": "<p>hello</p>"}]}]
        }
        text = _extract_text_from_result(result)
        assert "<p>" not in text
        assert "hello" in text

    def test_fallback_stringifies(self):
        result = {"unknown_key": 42}
        text = _extract_text_from_result(result)
        assert "42" in text
