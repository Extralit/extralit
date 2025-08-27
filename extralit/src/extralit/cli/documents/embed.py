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

"""Embed documents by chunking and creating embeddings for storage in datasets."""

import os
import re
from typing import Any, Optional
from uuid import uuid4

import numpy as np
import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "text-embedding-ada-002")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def parse_sections_with_hierarchy(markdown_text: str) -> list[dict[str, Any]]:
    """Parse markdown into sections preserving hierarchy structure."""
    sections = []
    lines = markdown_text.split("\n")
    current_section = ""
    current_headers = []
    current_page = 1
    section_index = 0

    for line in lines:
        # Check for headers
        header_match = re.match(r"(#+)\s*(.*)", line)
        if header_match:
            # Save previous section if it exists
            if current_section.strip():
                sections.append(
                    {
                        "id": str(uuid4()),
                        "content": current_section.strip(),
                        "metadata": {
                            "chunk_index": section_index,
                            "page_number": current_page,
                            "header": current_headers[-1]["text"] if current_headers else "",
                            "level": current_headers[-1]["level"] if current_headers else 0,
                            "header_hierarchy": [h["text"] for h in current_headers],
                        },
                    }
                )
                section_index += 1
                current_section = ""

            # Update headers stack
            level = len(header_match.group(1))
            header_text = header_match.group(2).strip()
            current_headers = [h for h in current_headers if h["level"] < level]
            current_headers.append({"level": level, "text": header_text})

        # Check for page breaks
        if "---" in line or "Page" in line:
            page_match = re.search(r"(?:Page|page)\s*(\d+)", line)
            if page_match:
                current_page = int(page_match.group(1))

        current_section += line + "\n"

    # Add final section
    if current_section.strip():
        sections.append(
            {
                "id": str(uuid4()),
                "content": current_section.strip(),
                "metadata": {
                    "chunk_index": section_index,
                    "page_number": current_page,
                    "header": current_headers[-1]["text"] if current_headers else "",
                    "level": current_headers[-1]["level"] if current_headers else 0,
                    "header_hierarchy": [h["text"] for h in current_headers],
                },
            }
        )

    return sections


def apply_character_chunking(sections: list[dict[str, Any]], chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    """Apply character-based chunking to sections that exceed chunk_size."""
    chunked_sections = []

    for section in sections:
        content = section["content"]
        if len(content) <= chunk_size:
            chunked_sections.append(section)
            continue

        # Split large sections
        current_pos = 0

        while current_pos < len(content):
            end_pos = min(current_pos + chunk_size, len(content))

            # Find good breaking point
            if end_pos < len(content):
                break_point = content.rfind("\n\n", current_pos, end_pos)
                if break_point == -1:
                    break_point = content.rfind(". ", current_pos, end_pos)
                    if break_point != -1:
                        break_point += 1
                if break_point == -1:
                    break_point = end_pos
            else:
                break_point = end_pos

            chunk_content = content[current_pos:break_point].strip()
            if chunk_content:
                chunked_sections.append(
                    {
                        "id": str(uuid4()),
                        "content": chunk_content,
                        "metadata": {
                            **section["metadata"],
                            "chunk_index": len(chunked_sections),
                        },
                    }
                )

            current_pos = max(current_pos + 1, break_point - overlap)

    return chunked_sections


def chunk_markdown(markdown_text: str, chunk_size: Optional[int] = None, overlap: int = 200) -> list[dict[str, Any]]:
    """
    Modern RAG chunking: section-first, then optional character limits.

    Args:
        markdown_text: The markdown content to chunk
        chunk_size: None to disable character chunking, or max chars per chunk
        overlap: Character overlap between chunks when character chunking is applied

    Returns:
        List of chunk dictionaries with content and metadata
    """
    # First: Parse by sections and preserve hierarchy
    sections = parse_sections_with_hierarchy(markdown_text)

    # Second: Apply character chunking only if chunk_size is provided
    if chunk_size is not None:
        sections = apply_character_chunking(sections, chunk_size, overlap)

    return sections


def create_embedding(text: str, model: Optional[str] = None) -> Optional[list[float]]:
    """
    Create embedding for text using configurable endpoint and model.

    Args:
        text: Text to embed
        model: Embedding model to use (overrides EMBED_MODEL env var)

    Returns:
        List of float values representing the embedding, or None if failed
    """
    if not OPENAI_API_KEY or OPENAI_BASE_URL == "random" or not OPENAI_BASE_URL.startswith("http"):
        # Generate random 1536-dimensional vector (same as text-embedding-ada-002)
        embedding = np.random.rand(1536).tolist()
        return embedding

    from llama_index.embeddings.openai import OpenAIEmbedding

    embed_model = OpenAIEmbedding(model=model or EMBED_MODEL_NAME, api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    # Get embedding
    embedding = embed_model.get_text_embedding(text)
    return embedding


def create_records_from_chunks(document, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Create dataset records from document chunks.

    Args:
        document: Document object with metadata
        chunks: List of chunk dictionaries

    Returns:
        List of record dictionaries ready for dataset logging
    """
    records = []

    for chunk in chunks:
        # Create embedding for chunk content
        embedding = create_embedding(chunk["content"])
        if embedding is None:
            continue

        # Prepare record
        record = {
            "fields": {
                "header": chunk["metadata"]["header"],
                "content": chunk["content"],
            },
            "metadata": {
                "reference": document.reference or str(document.id),
                "doc_id": str(document.id),
                "chunk_index": chunk["metadata"]["chunk_index"],
                "page_number": chunk["metadata"]["page_number"],
                "header": chunk["metadata"]["header"],
                "level": chunk["metadata"]["level"],
                "header_hierarchy": " > ".join(chunk["metadata"]["header_hierarchy"]),
            },
            "vectors": {"content": embedding},
        }

        records.append(record)

    return records


def embed_documents(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    reference: str = typer.Option(..., "--reference", "-r", help="Reference of documents to embed"),
    dataset_name: str = typer.Option("chunks", "--dataset", "-d", help="Dataset name for storing chunks"),
    chunk_size: Optional[int] = typer.Option(
        None, "--chunk-size", help="Maximum characters per chunk, or None for section-only chunking"
    ),
    overlap: int = typer.Option(200, "--overlap", help="Character overlap between chunks"),
    embedding_model: str = typer.Option("text-embedding-ada-002", "--model", help="Embedding model to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview chunks without creating records"),
) -> None:
    """
    Embed documents by chunking and creating embeddings for storage in datasets.

    This command:
    1. Fetches documents with the specified reference from the workspace
    2. Chunks the markdown content using content-aware chunking
    3. Creates embeddings for each chunk using configurable endpoint
    4. Stores the chunks and embeddings in a dataset

    Environment Variables:
        OPENAI_API_KEY: API key for OpenAI/LiteLLM endpoint (optional, uses random vectors if not set)
        OPENAI_BASE_URL: Base URL for embedding API (default: https://api.openai.com/v1)
        EMBED_MODEL: Embedding model to use (default: text-embedding-ada-002)

    Examples:
        # Basic usage with random vectors
        extralit documents embed --workspace research --reference paper-001

        # With custom LiteLLM endpoint
        export OPENAI_BASE_URL="https://litellm.jonnytran.engineer"
        export OPENAI_API_KEY="your-key"
        extralit documents embed --workspace research --reference paper-001

        # Preview chunks without creating embeddings
        extralit documents embed --workspace research --reference paper-001 --dry-run
    """
    console = Console()

    try:
        # Initialize client
        client = Extralit.from_credentials()

        # Get workspace
        workspace_obj = client.workspaces(name=workspace)
        if not workspace_obj:
            panel = get_themed_panel(
                f"Workspace '{workspace}' not found.",
                title="Workspace not found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        documents = workspace_obj.documents(reference=reference)

        if not documents:
            panel = get_themed_panel(
                f"No documents found with reference '{reference}' in workspace '{workspace}'.",
                title="No documents found",
                title_align="left",
                success=False,
            )
            console.print(panel)
            raise typer.Exit(code=1)

        # Get or create dataset
        if not dry_run:
            import extralit as ex

            try:
                dataset = client.datasets(name=dataset_name, workspace=workspace)
            except Exception:
                # Create proper settings for the dataset
                settings = ex.Settings(
                    fields=[ex.TextField(name="content"), ex.TextField(name="header")],
                    metadata=[
                        ex.TermsMetadataProperty(name="reference"),
                        ex.TermsMetadataProperty(name="doc_id"),
                        ex.IntegerMetadataProperty(name="chunk_index"),
                        ex.IntegerMetadataProperty(name="page_number"),
                        ex.TermsMetadataProperty(name="header"),
                        ex.IntegerMetadataProperty(name="level"),
                        ex.TermsMetadataProperty(name="header_hierarchy"),
                    ],
                    vectors=[ex.VectorField(name="content", dimensions=1536)],
                )

                # Create dataset with proper settings
                dataset = ex.Dataset(name=dataset_name, workspace=workspace, settings=settings)
                dataset.create()

        total_chunks = 0
        total_records = 0

        # Process each document
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            doc_task = progress.add_task("Processing documents...", total=len(documents))

            for doc in documents:
                progress.update(doc_task, description=f"Processing {doc.file_name or doc.reference}")

                if not doc.metadata or not doc.metadata.get("text_extraction_metadata", {}).get("markdown"):
                    progress.advance(doc_task)
                    continue

                markdown_content = doc.metadata["text_extraction_metadata"]["markdown"]
                if not markdown_content:
                    progress.advance(doc_task)
                    continue

                # Chunk the markdown content
                chunks = chunk_markdown(markdown_content, chunk_size=chunk_size, overlap=overlap)
                total_chunks += len(chunks)

                if dry_run:
                    # Show minimal preview
                    if chunks:
                        preview = (
                            chunks[0]["content"][:100] + "..."
                            if len(chunks[0]["content"]) > 100
                            else chunks[0]["content"]
                        )
                        typer.echo(f"  Sample chunk: {preview}")
                        typer.echo(f"  Total chunks: {len(chunks)}")
                else:
                    # Create records from chunks
                    records = create_records_from_chunks(doc, chunks)

                    if records:
                        # Log records to dataset
                        dataset.records.log(records)
                        total_records += len(records)

                progress.advance(doc_task)

        # Summary
        if dry_run:
            panel = get_themed_panel(
                f"Dry run completed!\n"
                f"Total documents processed: {len(documents)}\n"
                f"Total chunks created: {total_chunks}\n"
                f"Use --no-dry-run to actually create embeddings and store records.",
                title="Dry Run Summary",
                title_align="left",
                success=True,
            )
        else:
            panel = get_themed_panel(
                f"Embedding completed successfully!\n"
                f"Documents processed: {len(documents)}\n"
                f"Total chunks: {total_chunks}\n"
                f"Records created: {total_records}\n"
                f"Dataset: '{dataset_name}' in workspace '{workspace}'",
                title="Embedding Complete",
                title_align="left",
                success=True,
            )

        console.print(panel)

    except Exception as e:
        panel = get_themed_panel(
            f"Error during embedding process: {e!s}",
            title="Error",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)
