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

"""Tests for the YAML-configured chonkie chunker."""

import json
from pathlib import Path

import pytest
from docling_core.types.doc import ContentLayer, DocItemLabel, DoclingDocument, TableCell, TableData

from extralit_server.contexts.document import chunker
from extralit_server.contexts.document.chunker import (
    DEFAULT_RULES_PATH,
    chunk_document,
    chunk_text,
    load_config,
    rules_path,
)

SENTENCE = "The odds ratio for the resistant genotype was elevated in every cohort. "


def table_document() -> DoclingDocument:
    rows = [["Genotype", "OR", "95% CI"], ["RR", "2.6", "1.01-2.83"], ["RS", "3.04", "1.10-2.72"]]
    cells = [
        TableCell(
            text=value,
            start_row_offset_idx=r,
            end_row_offset_idx=r + 1,
            start_col_offset_idx=c,
            end_col_offset_idx=c + 1,
            column_header=r == 0,
        )
        for r, row in enumerate(rows)
        for c, value in enumerate(row)
    ]
    doc = DoclingDocument(name="doc")
    doc.add_heading("Results", level=1)
    doc.add_text(label=DocItemLabel.TEXT, text=SENTENCE * 12)
    doc.add_table(data=TableData(num_rows=3, num_cols=3, table_cells=cells))
    doc.add_text(label=DocItemLabel.PAGE_FOOTER, text="Journal footer 2024", content_layer=ContentLayer.FURNITURE)
    doc.add_text(label=DocItemLabel.TEXT, text=SENTENCE * 12)
    return doc


class TestRulesConfig:
    def test_shipped_rules_file_validates(self):
        config = load_config(DEFAULT_RULES_PATH)

        assert config.tokenizer == "character"
        assert config.chunk_size > 0
        assert config.rules["levels"][0]["include_delim"] == "next"

    def test_rules_path_defaults_to_the_shipped_file(self, monkeypatch):
        monkeypatch.setattr(chunker.settings, "chunking_rules_path", None)

        assert rules_path() == DEFAULT_RULES_PATH

    def test_rules_path_follows_settings(self, monkeypatch, tmp_path):
        custom = tmp_path / "rules.yaml"
        monkeypatch.setattr(chunker.settings, "chunking_rules_path", str(custom))

        assert rules_path() == custom

    def test_a_custom_rules_file_changes_the_split(self, tmp_path):
        # Only a blank-line level: sentences inside one paragraph are never split apart.
        custom = tmp_path / "rules.yaml"
        custom.write_text(
            "chunk_size: 64\nmin_characters_per_chunk: 1\nrules:\n  levels:\n"
            '    - delimiters: ["\\n\\n"]\n'
            "    - whitespace: true\n"
        )
        text = "First block.\n\nSecond block."

        chunks = chunk_text(text, path=Path(custom))

        assert "".join(c["text"] for c in chunks) == text

    def test_an_invalid_rules_file_is_rejected(self, tmp_path):
        custom = tmp_path / "rules.yaml"
        custom.write_text("chunk_size: 0\nrules: {}\n")

        with pytest.raises(ValueError):
            load_config(Path(custom))


class TestChunkText:
    @pytest.mark.parametrize("text", ["", "   \n\t  "])
    def test_blank_text_has_no_chunks(self, text):
        assert chunk_text(text) == []

    def test_chunks_are_json_serialisable_dicts(self):
        chunks = chunk_text("Some sample text for testing the chunker output format.")

        assert chunks
        assert set(chunks[0]) == {"text", "start_index", "end_index", "token_count"}
        json.dumps(chunks)

    def test_offsets_index_into_the_source_text(self):
        text = "# Title\n\n" + SENTENCE * 80 + "\n\n## Methods\n\n" + SENTENCE * 40

        chunks = chunk_text(text, chunk_size=400)

        assert len(chunks) > 1
        assert all(text[c["start_index"] : c["end_index"]] == c["text"] for c in chunks)
        assert "".join(c["text"] for c in chunks) == text

    def test_chunks_respect_chunk_size(self):
        chunks = chunk_text(SENTENCE * 100, chunk_size=300)

        assert all(c["token_count"] <= 300 for c in chunks)

    def test_smaller_chunk_size_gives_more_chunks(self):
        text = SENTENCE * 100

        assert len(chunk_text(text, chunk_size=200)) > len(chunk_text(text, chunk_size=1000))

    def test_long_paragraphs_split_at_sentence_ends(self):
        chunks = chunk_text(SENTENCE * 40, chunk_size=800)

        assert len(chunks) > 1
        assert all(c["text"].endswith(". ") for c in chunks)

    def test_a_heading_opens_the_chunk_of_its_section(self):
        text = SENTENCE * 20 + "\n## Methods\n\n" + SENTENCE * 20

        chunks = chunk_text(text, chunk_size=1500)

        assert any(c["text"].startswith("\n## Methods") for c in chunks)

    def test_an_inline_hash_is_not_a_heading(self):
        text = (SENTENCE * 10) + "We used sample #3 and C# tooling. " + (SENTENCE * 10)

        chunks = chunk_text(text, chunk_size=1000)

        assert not any(c["text"].startswith(("#3", "# tooling")) for c in chunks)


class TestChunkDocument:
    def test_a_table_stays_in_one_chunk(self):
        markdown, chunks = chunk_document(table_document(), chunk_size=800)

        table_chunks = [c for c in chunks if "| Genotype" in c["text"]]
        assert len(table_chunks) == 1
        assert "1.10-2.72" in table_chunks[0]["text"]
        assert "| Genotype" in markdown

    def test_offsets_index_into_the_returned_markdown(self):
        markdown, chunks = chunk_document(table_document(), chunk_size=800)

        assert all(markdown[c["start_index"] : c["end_index"]] == c["text"] for c in chunks)

    def test_furniture_is_left_out(self):
        markdown, chunks = chunk_document(table_document())

        assert "Journal footer" not in markdown
        assert not any("Journal footer" in c["text"] for c in chunks)

    def test_heading_is_rendered_as_markdown(self):
        markdown, _ = chunk_document(table_document())

        assert markdown.startswith("# Results") or markdown.startswith("## Results")
