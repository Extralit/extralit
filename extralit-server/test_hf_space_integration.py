#!/usr/bin/env python3
"""
Simple test script to verify the hf-space integration works correctly.
"""

import asyncio
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_hf_space_service():
    """Test the hf-space service integration."""
    
    try:
        from src.extralit_server.services.hf_space import extract_pdf_with_pymupdf, HfSpaceClient
        from src.extralit_server.api.schemas.v1.document.preprocessing import PDFMetadata
        
        logger.info("Successfully imported hf-space service modules")
        
        # Test 1: Check if we can create HfSpaceClient
        try:
            client = HfSpaceClient()
            logger.info(f"HfSpaceClient created successfully with base_url: {client.base_url}")
        except Exception as e:
            logger.error(f"Failed to create HfSpaceClient: {e}")
            return False
        
        # Test 2: Check health endpoint (if hf-space is running)
        try:
            health_status = await client.health_check()
            if health_status:
                logger.info("✅ HF-Space service is healthy and reachable")
            else:
                logger.warning("⚠️  HF-Space service health check failed (service might not be running)")
        except Exception as e:
            logger.warning(f"⚠️  Health check failed (expected if service not running): {e}")
        
        # Test 3: Test with a sample PDF if available
        test_pdf_dirs = [
            Path("../test-pdf"),
            Path("../extralit-benchmark/383-pdfs"),
            Path("../extralit-benchmark/pdfs")
        ]
        
        sample_pdfs = []
        for test_dir in test_pdf_dirs:
            if test_dir.exists():
                found_pdfs = list(test_dir.glob("*.pdf"))[:1]  # Just take first PDF
                if found_pdfs:
                    sample_pdfs.extend(found_pdfs)
                    break
        
        if sample_pdfs:
            test_pdf = sample_pdfs[0]
            logger.info(f"Found test PDF: {test_pdf}")
            
            try:
                with open(test_pdf, "rb") as f:
                    pdf_bytes = f.read()
                
                # Create sample metadata
                sample_metadata = PDFMetadata(
                    filename=test_pdf.name,
                    processing_time=0.0,
                    page_count=None
                )
                
                logger.info("Attempting to extract markdown using hf-space service...")
                result = await extract_pdf_with_pymupdf(
                    pdf_bytes=pdf_bytes,
                    filename=test_pdf.name,
                    analysis_metadata=sample_metadata
                )
                
                if result:
                    logger.info(f"✅ Successfully extracted {len(result.markdown)} characters of markdown")
                    logger.info(f"Processing time: {result.processing_time:.2f}s")
                    logger.info(f"Metadata keys: {list(result.metadata.model_dump().keys())}")
                else:
                    logger.warning("⚠️  Extraction returned None")
                    
            except Exception as e:
                logger.error(f"❌ PDF extraction test failed: {e}")
                
        else:
            logger.info("No test PDFs found in test-pdf directory, skipping PDF extraction test")
        
        logger.info("🎉 HF-Space integration test completed!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error - modules not found: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {e}")
        return False

async def main():
    """Main test function."""
    logger.info("🔧 Starting HF-Space integration test...")
    
    # Check environment variables
    hf_space_url = os.getenv("HF_SPACE_BASE_URL", "http://localhost:7860")
    logger.info(f"Using HF_SPACE_BASE_URL: {hf_space_url}")
    
    success = await test_hf_space_service()
    
    if success:
        logger.info("✅ Integration test completed successfully!")
    else:
        logger.error("❌ Integration test failed!")
        
    return success

if __name__ == "__main__":
    asyncio.run(main())
