#!/usr/bin/env python3
"""
Simple embedding test to debug the issue.
"""

import os
import sys

# Add the extralit package to the path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "extralit", "extralit", "src")
)


def test_embedding_simple():
    """Simple test for embedding creation."""
    print("🧪 Testing embedding creation (simple)...")

    try:
        # Set mock API key
        os.environ["OPENAI_API_KEY"] = "test-key"

        from extralit.cli.documents.embed import create_embedding

        # Test with a simple text
        test_text = "This is a test."
        print(f"Testing with text: '{test_text}'")

        # Try to create embedding
        embedding = create_embedding(test_text)

        if embedding is None:
            print("❌ Embedding is None")
        else:
            print(f"✅ Embedding created with {len(embedding)} dimensions")
            print(f"First 5 values: {embedding[:5]}")

    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback

        traceback.print_exc()


def test_llama_index_import():
    """Test if llama-index components can be imported."""
    print("\n🧪 Testing llama-index imports...")

    try:
        from llama_index.embeddings.openai import OpenAIEmbedding

        print("✅ Successfully imported OpenAIEmbedding")

        # Try to create instance
        OpenAIEmbedding(model="text-embedding-ada-002", api_key="test-key")
        print("✅ Successfully created OpenAIEmbedding instance")

    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ General error: {e}")


if __name__ == "__main__":
    test_llama_index_import()
    test_embedding_simple()
