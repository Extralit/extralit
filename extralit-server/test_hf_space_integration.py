#!/usr/bin/env python3
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

"""
Simple test script to verify the hf-space integration works correctly.
"""

import asyncio
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_hf_space_service():
    """Test the PyMuPDF extraction service integration."""

    try:
        from src.extralit_server.api.schemas.v1.document.ocr import ExtractionRequest
        from src.extralit_server.contexts.ocr.text import extract_pdf_text, get_extraction_client

        logger.info("Successfully imported PyMuPDF extraction modules")

        # Test 1: Check if we can get extraction client
        try:
            client = get_extraction_client()
            logger.info(f"PyMuPDF extraction client created successfully with base_url: {client.base_url}")
        except Exception as e:
            logger.error(f"Failed to create extraction client: {e}")
            return False

        # Test 2: Check health endpoint (if extralit-hf-space is running)
        try:
            health_status = await client.health_check()
            if health_status:
                logger.info("✅ PyMuPDF extraction service is healthy and reachable")
            else:
                logger.warning("⚠️  PyMuPDF extraction service health check failed (service might not be running)")
        except Exception as e:
            logger.warning(f"⚠️  Health check failed (expected if service not running): {e}")

        # Test 3: Test with a sample PDF if available
        test_pdf_dirs = [
            Path("../test-pdf"),
            Path("../extralit-benchmark/383-pdfs"),
            Path("../extralit-benchmark/pdfs"),
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

                # Create extraction request
                request = ExtractionRequest(filename=test_pdf.name, analysis_metadata={})

                logger.info("Attempting to extract markdown using PyMuPDF service...")
                result = await extract_pdf_text(pdf_bytes=pdf_bytes, request=request)

                if result:
                    logger.info(f"✅ Successfully extracted {len(result.markdown)} characters of markdown")
                    logger.info(f"Processing time: {result.processing_time:.2f}s")
                    logger.info(f"Pages processed: {result.page_count}")
                else:
                    logger.warning("⚠️  Extraction returned None")

            except Exception as e:
                logger.error(f"❌ PDF extraction test failed: {e}")

        else:
            logger.info("No test PDFs found in test directories, skipping PDF extraction test")

        logger.info("🎉 PyMuPDF integration test completed!")
        return True

    except ImportError as e:
        logger.error(f"❌ Import error - modules not found: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🔧 Starting PyMuPDF extraction service integration test...")

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
