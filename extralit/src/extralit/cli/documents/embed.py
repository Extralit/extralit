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

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from extralit.cli.rich import get_themed_panel
from extralit.client import Extralit


def chunk_markdown(markdown_text: str, chunk_size: int = 1000, overlap: int = 200) -> list[dict[str, Any]]:
    """
    Chunk markdown text into segments with proper hierarchy preservation.

    Args:
        markdown_text: The markdown content to chunk
        chunk_size: Maximum characters per chunk
        overlap: Character overlap between chunks

    Returns:
        List of chunk dictionaries with content and metadata
    """
    chunks = []
    lines = markdown_text.split("\n")
    current_chunk = ""
    current_headers = []
    current_page = 1
    chunk_index = 0

    for line in lines:
        # Check for headers
        header_match = re.match(r"(#+)\s*(.*)", line)
        if header_match:
            level = len(header_match.group(1))
            header_text = header_match.group(2).strip()

            # Update headers stack based on level
            current_headers = [h for h in current_headers if h["level"] < level]
            current_headers.append({"level": level, "text": header_text})

        # Check for page breaks (common in PDF extractions)
        if "---" in line or "Page" in line:
            page_match = re.search(r"(?:Page|page)\s*(\d+)", line)
            if page_match:
                current_page = int(page_match.group(1))

        # Add line to current chunk
        current_chunk += line + "\n"

        # Check if chunk is large enough to split
        if len(current_chunk) >= chunk_size:
            # Find a good breaking point (end of paragraph or sentence)
            break_point = current_chunk.rfind("\n\n")
            if break_point == -1:
                break_point = current_chunk.rfind(". ")
                if break_point != -1:
                    break_point += 1
            if break_point == -1:
                break_point = chunk_size

            # Create chunk
            chunk_content = current_chunk[:break_point].strip()
            if chunk_content:
                chunks.append(
                    {
                        "id": str(uuid4()),
                        "content": chunk_content,
                        "metadata": {
                            "chunk_index": chunk_index,
                            "page_number": current_page,
                            "header": current_headers[-1]["text"] if current_headers else "",
                            "level": current_headers[-1]["level"] if current_headers else 0,
                            "header_hierarchy": [h["text"] for h in current_headers],
                        },
                    }
                )
                chunk_index += 1

            # Keep overlap for next chunk
            current_chunk = current_chunk[max(0, break_point - overlap) :]

    # Add final chunk if there's remaining content
    if current_chunk.strip():
        chunks.append(
            {
                "id": str(uuid4()),
                "content": current_chunk.strip(),
                "metadata": {
                    "chunk_index": chunk_index,
                    "page_number": current_page,
                    "header": current_headers[-1]["text"] if current_headers else "",
                    "level": current_headers[-1]["level"] if current_headers else 0,
                    "header_hierarchy": [h["text"] for h in current_headers],
                },
            }
        )

    return chunks


def create_embedding(text: str, model: str = "text-embedding-ada-002") -> Optional[list[float]]:
    """
    Create embedding for text using OpenAI API.

    Args:
        text: Text to embed
        model: OpenAI embedding model to use

    Returns:
        List of float values representing the embedding, or None if failed
    """
    try:
        from llama_index.embeddings.openai import OpenAIEmbedding

        # Initialize OpenAI embedding
        embed_model = OpenAIEmbedding(model=model, api_key=os.getenv("OPENAI_API_KEY"))

        # Get embedding
        embedding = embed_model.get_text_embedding(text)
        return embedding

    except Exception as e:
        print(f"Error creating embedding: {e}")
        return None


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
                "content": chunk["content"],
                "document_reference": document.reference or str(document.id),
                "document_id": str(document.id),
                "chunk_index": chunk["metadata"]["chunk_index"],
                "page_number": chunk["metadata"]["page_number"],
                "header": chunk["metadata"]["header"],
                "level": chunk["metadata"]["level"],
                "header_hierarchy": " > ".join(chunk["metadata"]["header_hierarchy"]),
            },
            "vectors": {"content_embedding": embedding},
        }

        records.append(record)

    return records


def embed_documents(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    reference: str = typer.Option(..., "--reference", "-r", help="Reference of documents to embed"),
    dataset_name: str = typer.Option("chunks", "--dataset", "-d", help="Dataset name for storing chunks"),
    chunk_size: int = typer.Option(1000, "--chunk-size", help="Maximum characters per chunk"),
    overlap: int = typer.Option(200, "--overlap", help="Character overlap between chunks"),
    embedding_model: str = typer.Option("text-embedding-ada-002", "--model", help="OpenAI embedding model"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview chunks without creating records"),
) -> None:
    """
    Embed documents by chunking and creating embeddings for storage in datasets.

    This command:
    1. Fetches documents with the specified reference from the workspace
    2. Chunks the markdown content using content-aware chunking
    3. Creates embeddings for each chunk using OpenAI API
    4. Stores the chunks and embeddings in a dataset
    """
    console = Console()

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY") and not dry_run:
        panel = get_themed_panel(
            "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
            title="Missing API Key",
            title_align="left",
            success=False,
        )
        console.print(panel)
        raise typer.Exit(code=1)

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

        # Fetch documents with the specified reference
        console.print(f"🔍 Fetching documents with reference '{reference}' from workspace '{workspace}'...")
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

        console.print(f"📄 Found {len(documents)} document(s) to process")

        # Get or create dataset
        if not dry_run:
            console.print(f"📊 Checking dataset '{dataset_name}'...")
            try:
                dataset = client.dataset(name=dataset_name, workspace=workspace)
                console.print(f"✅ Using existing dataset '{dataset_name}'")
            except Exception:
                # Dataset doesn't exist, create it
                console.print(f"🆕 Creating new dataset '{dataset_name}'...")
                # Note: Dataset creation might need different API - this is a placeholder
                dataset = client.dataset(name=dataset_name, workspace=workspace)

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

                # Get markdown content
                if not hasattr(doc, "metadata") or not doc.metadata:
                    console.print(f"⚠️  Skipping document {doc.reference}: No metadata available")
                    progress.advance(doc_task)
                    continue

                # Check for text extraction metadata
                if not hasattr(doc.metadata, "text_extraction_metadata") or not doc.metadata.text_extraction_metadata:
                    console.print(f"⚠️  Skipping document {doc.reference}: No text extraction metadata")
                    progress.advance(doc_task)
                    continue

                markdown_content = doc.metadata.text_extraction_metadata.markdown
                if not markdown_content:
                    console.print(f"⚠️  Skipping document {doc.reference}: No markdown content")
                    progress.advance(doc_task)
                    continue

                # Chunk the markdown content
                console.print(f"🔪 Chunking document {doc.reference}...")
                chunks = chunk_markdown(markdown_content, chunk_size=chunk_size, overlap=overlap)

                console.print(f"📝 Created {len(chunks)} chunks for document {doc.reference}")
                total_chunks += len(chunks)

                if dry_run:
                    # Show preview of chunks
                    console.print(f"\n📋 Preview of chunks for {doc.reference}:")
                    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                        preview = chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                        console.print(f"  Chunk {i + 1}: {preview}")
                        console.print(f"    Header: {chunk['metadata']['header']}")
                        console.print(f"    Page: {chunk['metadata']['page_number']}")
                        console.print()

                    if len(chunks) > 3:
                        console.print(f"  ... and {len(chunks) - 3} more chunks")
                else:
                    # Create records from chunks
                    console.print("🔮 Creating embeddings and records...")
                    records = create_records_from_chunks(doc, chunks)

                    if records:
                        # Log records to dataset
                        dataset.records.log(records)
                        console.print(f"✅ Logged {len(records)} records to dataset '{dataset_name}'")
                        total_records += len(records)
                    else:
                        console.print(f"⚠️  No valid records created for document {doc.reference}")

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
