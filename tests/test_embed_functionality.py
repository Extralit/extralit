#!/usr/bin/env python3
"""
Comprehensive test script for the embed functionality.
Tests chunking, embedding creation, and record preparation without requiring CLI.
"""

import os
import sys
from unittest.mock import Mock, patch

# Add the extralit package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "extralit", "src"))


def test_chunking():
    """Test the markdown chunking functionality."""
    print("🧪 Testing markdown chunking...")

    try:
        from extralit.cli.documents.embed import chunk_markdown

        # Test markdown with hierarchical structure
        test_markdown = """# Introduction to Machine Learning
This document provides an overview of machine learning concepts and techniques.

## Supervised Learning
Supervised learning is a type of machine learning where the algorithm learns from labeled training data.

### Classification
Classification algorithms predict discrete categories or classes.

#### Decision Trees
Decision trees are a popular classification algorithm that creates a model in the form of a tree structure.

They work by recursively splitting the data based on feature values to maximize information gain.

#### Support Vector Machines
SVMs find the optimal hyperplane that separates different classes with maximum margin.

### Regression
Regression algorithms predict continuous numerical values.

## Unsupervised Learning
Unsupervised learning finds patterns in data without labeled examples.

### Clustering
Clustering groups similar data points together.

## Deep Learning
Deep learning uses neural networks with multiple layers to learn complex patterns.

### Neural Networks
Neural networks are inspired by the structure of the human brain.

### Convolutional Neural Networks
CNNs are particularly effective for image recognition tasks.
"""

        chunks = chunk_markdown(test_markdown, chunk_size=300, overlap=50)
        print(f"✅ Created {len(chunks)} chunks from test markdown")

        # Verify chunk structure
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"\n📄 Chunk {i + 1}:")
            print(f"  Content length: {len(chunk['content'])} characters")
            print(f"  Header: '{chunk['metadata']['header']}'")
            print(f"  Level: {chunk['metadata']['level']}")
            print(f"  Hierarchy: {' > '.join(chunk['metadata']['header_hierarchy'])}")
            print(f"  Content preview: {chunk['content'][:100]}...")

        if len(chunks) > 3:
            print(f"\n... and {len(chunks) - 3} more chunks")

        return True

    except Exception as e:
        print(f"❌ Chunking test failed: {e}")
        return False


def test_embedding_creation():
    """Test the embedding creation functionality (mocked)."""
    print("\n🧪 Testing embedding creation...")

    try:
        from extralit.cli.documents.embed import create_embedding

        # Mock the OpenAI embedding to avoid requiring API key
        with patch(
            "llama_index.embeddings.openai.OpenAIEmbedding"
        ) as mock_embedding_class:
            # Mock the embedding model instance
            mock_embedding_instance = Mock()
            mock_embedding_instance.get_text_embedding.return_value = [
                0.1,
                0.2,
                0.3,
            ] * 512  # 1536 dimensions
            mock_embedding_class.return_value = mock_embedding_instance

            # Test embedding creation
            test_text = "This is a test text for embedding generation."
            embedding = create_embedding(test_text)

            if embedding and len(embedding) == 1536:
                print(
                    f"✅ Successfully created embedding with {len(embedding)} dimensions"
                )
                print(f"  First 5 values: {embedding[:5]}")
                return True
            else:
                print(
                    f"❌ Embedding creation failed: wrong dimensions {len(embedding) if embedding else 'None'}"
                )
                return False

    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False


def test_record_creation():
    """Test the record creation functionality."""
    print("\n🧪 Testing record creation...")

    try:
        from extralit.cli.documents.embed import create_records_from_chunks

        # Mock document object
        mock_document = Mock()
        mock_document.id = "test-doc-123"
        mock_document.reference = "test-reference"

        # Test chunks
        test_chunks = [
            {
                "id": "chunk-1",
                "content": "This is the first chunk of content from the document.",
                "metadata": {
                    "chunk_index": 0,
                    "page_number": 1,
                    "header": "Introduction",
                    "level": 1,
                    "header_hierarchy": ["Introduction"],
                },
            },
            {
                "id": "chunk-2",
                "content": "This is the second chunk with different content and structure.",
                "metadata": {
                    "chunk_index": 1,
                    "page_number": 1,
                    "header": "Methodology",
                    "level": 2,
                    "header_hierarchy": ["Introduction", "Methodology"],
                },
            },
        ]

        # Mock the embedding creation
        with patch(
            "llama_index.embeddings.openai.OpenAIEmbedding"
        ) as mock_embedding_class:
            mock_embedding_instance = Mock()
            mock_embedding_instance.get_text_embedding.return_value = [
                0.1,
                0.2,
                0.3,
            ] * 512  # 1536 dimensions
            mock_embedding_class.return_value = mock_embedding_instance

            records = create_records_from_chunks(mock_document, test_chunks)

            if records and len(records) == 2:
                print(f"✅ Successfully created {len(records)} records")

                # Verify record structure
                for i, record in enumerate(records):
                    print(f"\n📝 Record {i + 1}:")
                    print(
                        f"  Document reference: {record['fields']['document_reference']}"
                    )
                    print(f"  Chunk index: {record['fields']['chunk_index']}")
                    print(f"  Header: {record['fields']['header']}")
                    print(f"  Content length: {len(record['fields']['content'])}")
                    print(
                        f"  Embedding dimensions: {len(record['vectors']['content_embedding'])}"
                    )

                return True
            else:
                print(
                    f"❌ Record creation failed: expected 2 records, got {len(records) if records else 'None'}"
                )
                return False

    except Exception as e:
        print(f"❌ Record creation test failed: {e}")
        return False


def test_full_workflow():
    """Test the complete workflow integration."""
    print("\n🧪 Testing full workflow integration...")

    try:
        from extralit.cli.documents.embed import (
            chunk_markdown,
            create_records_from_chunks,
        )

        # Sample document content
        sample_markdown = """# Research Paper: AI in Healthcare
This paper explores the applications of artificial intelligence in healthcare.

## Introduction
Artificial intelligence has shown great promise in revolutionizing healthcare delivery.

## Methods
We conducted a comprehensive review of recent AI applications in clinical settings.

### Data Collection
Data was collected from multiple healthcare institutions over a 2-year period.

### Analysis
Statistical analysis was performed using machine learning algorithms.

## Results
Our findings demonstrate significant improvements in diagnostic accuracy.

## Conclusion
AI technologies can substantially enhance healthcare outcomes when properly implemented.
"""

        # Mock document
        mock_document = Mock()
        mock_document.id = "healthcare-ai-paper"
        mock_document.reference = "healthcare-2024"

        # Step 1: Chunk the document
        chunks = chunk_markdown(sample_markdown, chunk_size=400, overlap=100)
        print(f"📄 Step 1: Created {len(chunks)} chunks")

        # Step 2: Create records (with mocked embeddings)
        with patch(
            "llama_index.embeddings.openai.OpenAIEmbedding"
        ) as mock_embedding_class:
            mock_embedding_instance = Mock()
            mock_embedding_instance.get_text_embedding.return_value = [
                0.1,
                0.2,
                0.3,
            ] * 512  # 1536 dimensions
            mock_embedding_class.return_value = mock_embedding_instance

            records = create_records_from_chunks(mock_document, chunks)
            print(f"📝 Step 2: Created {len(records)} records")

            # Step 3: Verify data integrity
            total_content_length = sum(
                len(record["fields"]["content"]) for record in records
            )
            print(
                f"📊 Step 3: Total content length across all records: {total_content_length} characters"
            )

            # Verify all records have embeddings
            records_with_embeddings = sum(
                1 for record in records if "content_embedding" in record["vectors"]
            )
            print(
                f"🔮 Step 4: Records with embeddings: {records_with_embeddings}/{len(records)}"
            )

            if records_with_embeddings == len(records):
                print("✅ Full workflow test successful!")
                return True
            else:
                print("❌ Some records missing embeddings")
                return False

    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        return False


def main():
    """Run all tests and provide summary."""
    print("🚀 Starting comprehensive embed functionality tests...\n")

    # Set mock environment variable for API key check
    os.environ["OPENAI_API_KEY"] = "test-key-for-mocking"

    test_results = {
        "Chunking": test_chunking(),
        "Embedding Creation": test_embedding_creation(),
        "Record Creation": test_record_creation(),
        "Full Workflow": test_full_workflow(),
    }

    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} | {status}")
        if result:
            passed += 1

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The embed functionality is working correctly.")
        print("\nNext steps:")
        print("1. Test with real Extralit workspace and documents")
        print("2. Verify dataset creation and record logging")
        print("3. Test with actual OpenAI API key")
        print("4. Resolve CLI typer compatibility issue if needed")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
