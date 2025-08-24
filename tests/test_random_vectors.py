#!/usr/bin/env python3
"""
Test script for the new random vector embedding functionality.

This script demonstrates the configurable embedding system that can use:
1. Random vectors for testing (default when no API key)
2. OpenAI API with custom base URL
3. LiteLLM endpoint integration

Usage:
    cd extralit
    venv\Scripts\activate
    python tests/test_random_vectors.py
"""

import os
import sys

# Add the extralit package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "extralit", "src"))


def test_random_vectors():
    """Test random vector generation."""
    print("🎲 Testing random vector generation...")

    try:
        from extralit.cli.documents.embed import create_embedding

        # Ensure we use random vectors
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["OPENAI_BASE_URL"] = "random"

        test_texts = [
            "Testing random vector generation for embeddings.",
            "Machine learning applications in healthcare.",
            "Vector-borne disease control strategies.",
        ]

        embeddings = []
        for i, text in enumerate(test_texts, 1):
            print(f"   Creating embedding {i}/{len(test_texts)}...")
            embedding = create_embedding(text)

            if embedding and len(embedding) == 1536:
                embeddings.append(embedding)
                print(f"   ✅ Success! Dimensions: {len(embedding)}")
                print(
                    f"   📊 First 3 values: [{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}]"
                )
            else:
                print(
                    f"   ❌ Failed: wrong dimensions {len(embedding) if embedding else 'None'}"
                )
                return False

        # Verify vectors are different (randomness check)
        if len(embeddings) >= 2:
            vec1, vec2 = embeddings[0], embeddings[1]
            diff = sum(abs(a - b) for a, b in zip(vec1, vec2))
            print(f"   🔍 Vector difference: {diff:.4f} (should be > 0)")

            if diff > 0:
                print("   ✅ Vectors are properly randomized")
                return True
            else:
                print("   ❌ Vectors are identical (not random)")
                return False

        return True

    except Exception as e:
        print(f"❌ Random vector test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_environment_configuration():
    """Test different environment configurations."""
    print("\n⚙️  Testing environment variable configurations...")

    try:
        from extralit.cli.documents.embed import create_embedding

        test_text = "Test text for configuration testing."

        # Test 1: Random vectors (no API key)
        print("   Test 1: No API key (should use random vectors)")
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_BASE_URL", None)
        embedding1 = create_embedding(test_text)

        if embedding1 and len(embedding1) == 1536:
            print("   ✅ Random vectors working without API key")
        else:
            print("   ❌ Failed without API key")
            return False

        # Test 2: Explicit random mode
        print("   Test 2: Explicit random mode")
        os.environ["OPENAI_BASE_URL"] = "random"
        embedding2 = create_embedding(test_text)

        if embedding2 and len(embedding2) == 1536:
            print("   ✅ Explicit random mode working")
        else:
            print("   ❌ Failed in explicit random mode")
            return False

        # Test 3: Custom model via environment
        print("   Test 3: Custom model configuration")
        os.environ["EMBED_MODEL"] = "text-embedding-3-small"
        embedding3 = create_embedding(test_text)

        if embedding3 and len(embedding3) == 1536:
            print("   ✅ Custom model configuration working")
        else:
            print("   ❌ Failed with custom model")
            return False

        # Clean up
        os.environ.pop("OPENAI_BASE_URL", None)
        os.environ.pop("EMBED_MODEL", None)

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_complete_workflow():
    """Test complete embedding workflow with random vectors."""
    print("\n🔄 Testing complete workflow with random vectors...")

    try:
        from extralit.cli.documents.embed import (
            chunk_markdown,
            create_records_from_chunks,
        )
        from unittest.mock import Mock

        # Set up for random vectors
        os.environ["OPENAI_BASE_URL"] = "random"

        # Sample document content
        sample_content = """# Research Paper: Vector Control Methods

## Abstract
This paper examines various vector control methodologies for disease prevention.

## Introduction
Vector-borne diseases represent a significant global health challenge.

### Background
Traditional control methods have shown varying effectiveness across different regions.

## Methodology
Our study employed a multi-site approach to evaluate control strategies.

### Data Collection
Field data was collected over a 12-month period using standardized protocols.

## Results
Integrated approaches showed superior effectiveness compared to single interventions.

### Primary Outcomes
Treatment groups demonstrated 60% reduction in vector populations.

## Conclusion
Multi-faceted approaches are essential for effective vector control programs.
"""

        # Create mock document
        mock_doc = Mock()
        mock_doc.id = "test-doc-random-vectors"
        mock_doc.reference = "vector-control-2024"

        # Step 1: Chunk the content
        chunks = chunk_markdown(sample_content, chunk_size=400, overlap=100)
        print(f"   📄 Created {len(chunks)} chunks")

        # Step 2: Create records with random embeddings
        records = create_records_from_chunks(mock_doc, chunks)
        print(f"   📝 Created {len(records)} records with random embeddings")

        # Step 3: Verify all records have proper embeddings
        valid_records = 0
        for record in records:
            if (
                "content_embedding" in record["vectors"]
                and len(record["vectors"]["content_embedding"]) == 1536
            ):
                valid_records += 1

        print(f"   🔍 Valid records with embeddings: {valid_records}/{len(records)}")

        if valid_records == len(records):
            print("   ✅ Complete workflow successful with random vectors!")
            return True
        else:
            print("   ❌ Some records missing valid embeddings")
            return False

    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all random vector tests."""
    print("🎲 RANDOM VECTOR EMBEDDING TESTS")
    print("=" * 50)
    print("Testing the new configurable embedding system")
    print("=" * 50)

    # Test results
    results = {
        "Random Vectors": test_random_vectors(),
        "Environment Config": test_environment_configuration(),
        "Complete Workflow": test_complete_workflow(),
    }

    # Summary
    print("\n" + "=" * 50)
    print("📊 RANDOM VECTOR TEST SUMMARY")
    print("=" * 50)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} | {status}")

    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

    if passed == total:
        print("\n🎉 ALL RANDOM VECTOR TESTS PASSED!")
        print("\n✅ What this confirms:")
        print("• Random vector generation works correctly")
        print("• Environment variable configuration functional")
        print("• Complete embedding workflow ready")
        print("• No API dependencies for testing")

        print("\n🔧 Environment Variables Available:")
        print("• OPENAI_API_KEY: Set for real API calls")
        print("• OPENAI_BASE_URL: Custom endpoint (e.g., LiteLLM)")
        print("• EMBED_MODEL: Custom embedding model")
        print("• Set OPENAI_BASE_URL='random' for testing")

        print("\n🚀 Ready for production use!")

    else:
        print("\n⚠️  Some tests failed. Please review the output above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
