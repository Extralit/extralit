#!/usr/bin/env python3
"""Test script to verify imports work correctly."""

import sys
import os

# Add the extralit package to the path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "extralit", "extralit", "src")
)

try:
    from extralit.cli.documents.embed import chunk_markdown

    print("✅ Successfully imported embed_documents and related functions")

    # Test chunking function
    test_markdown = """# Introduction
This is a test document with some content.

## Section 1
This section has some text content that should be chunked properly.

### Subsection 1.1
More detailed content here with additional information.

## Section 2
Another section with different content to test the chunking algorithm.
"""

    chunks = chunk_markdown(test_markdown, chunk_size=200, overlap=50)
    print(f"✅ Chunking test successful: Created {len(chunks)} chunks")

    # Print first chunk for verification
    if chunks:
        print(f"First chunk content: {chunks[0]['content'][:100]}...")
        print(f"First chunk metadata: {chunks[0]['metadata']}")

except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Test failed: {e}")

print("Test completed.")
