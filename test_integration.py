#!/usr/bin/env python3
"""
Simple integration test for hf-space PyMuPDF extraction service.
"""

import asyncio
import sys
from pathlib import Path

# Add the extralit-server source to the path
sys.path.insert(0, str(Path(__file__).parent / "extralit-server" / "src"))

from extralit_server.services.hf_space import extract_pdf_with_pymupdf


async def test_hf_space_integration():
    """Test the hf-space integration with a sample PDF."""
    
    print("🧪 Testing hf-space PyMuPDF integration...")
    
    # Find a test PDF
    test_pdf_paths = [
        Path("../extralit-benchmark/383-pdfs").glob("*.pdf"),
        Path("../test-pdf").glob("*.pdf"),
        Path(".").glob("**/*.pdf")
    ]
    
    test_pdf = None
    for path_glob in test_pdf_paths:
        for pdf_file in path_glob:
            if pdf_file.exists() and pdf_file.stat().st_size > 0:
                test_pdf = pdf_file
                break
        if test_pdf:
            break
    
    if not test_pdf:
        print("❌ No test PDF found")
        return False
    
    print(f"📄 Using test PDF: {test_pdf}")
    
    try:
        # Read PDF bytes
        pdf_bytes = test_pdf.read_bytes()
        print(f"📊 PDF size: {len(pdf_bytes)} bytes")
        
        # Test analysis metadata
        analysis_metadata = {
            "processing_settings": {"test": True},
            "language_detected": ["en"],
            "filename": test_pdf.name
        }
        
        # Call the extraction service
        print("🚀 Calling PyMuPDF extraction service...")
        result = await extract_pdf_with_pymupdf(
            pdf_bytes=pdf_bytes,
            filename=test_pdf.name,
            analysis_metadata=analysis_metadata
        )
        
        if result:
            markdown, metadata = result
            print("✅ Extraction successful!")
            print(f"📝 Markdown length: {len(markdown)} characters")
            print(f"📈 Metadata: {metadata}")
            print(f"🔍 First 200 chars of markdown:")
            print(markdown[:200] + "..." if len(markdown) > 200 else markdown)
            return True
        else:
            print("❌ Extraction returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing health check...")
    
    try:
        from extralit_server.services.hf_space import HfSpaceClient, HfSpaceSettings
        
        settings = HfSpaceSettings()
        async with HfSpaceClient(settings) as client:
            health = await client.health_check()
            if health:
                print("✅ Health check passed")
                return True
            else:
                print("❌ Health check failed")
                return False
                
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("🔬 Starting hf-space integration tests...\n")
    
    # Test health check first
    health_ok = await test_health_check()
    print()
    
    if health_ok:
        # Test actual extraction
        extraction_ok = await test_hf_space_integration()
        print()
        
        if extraction_ok:
            print("🎉 All tests passed! Integration is working correctly.")
            return 0
        else:
            print("💥 Extraction test failed.")
            return 1
    else:
        print("💥 Health check failed. Is the hf-space server running?")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
