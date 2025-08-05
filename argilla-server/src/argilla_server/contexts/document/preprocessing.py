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

"""Document preprocessing utilities."""

import logging
import os
import tempfile
import time
from io import BytesIO
from uuid import uuid4

try:
    import ocrmypdf

    OCRMYPDF_AVAILABLE = True
except ImportError:
    OCRMYPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


def preprocess_pdf_with_ocrmypdf(file_data: bytes, filename: str) -> bytes:
    """
    Preprocess PDF with OCRmyPDF to add OCR layer and fix orientation.
    Works with bytes data and returns processed bytes, minimizing disk I/O.

    Args:
        file_data: PDF file data as bytes
        filename: Original filename for logging purposes

    Returns:
        Processed PDF data as bytes (or original bytes if processing fails)
    """
    if not OCRMYPDF_AVAILABLE:
        logger.warning("OCRmyPDF not available, skipping preprocessing")
        return file_data

    # Only process PDF files
    if not filename.lower().endswith(".pdf"):
        logger.debug(f"Skipping OCRmyPDF for non-PDF file: {filename}")
        return file_data

    try:
        logger.info(f"Starting OCRmyPDF preprocessing for: {filename}")
        start_time = time.time()

        # Try using BytesIO objects first to minimize disk I/O
        try:
            input_buffer = BytesIO(file_data)
            output_buffer = BytesIO()

            # OCRmyPDF configuration for optimal processing
            ocrmypdf.ocr(
                input_buffer,
                output_buffer,
                language=["eng"],  # Can be configured for other languages
                rotate_pages=True,  # Auto-rotate pages with horizontal text
                deskew=True,  # Fix skewed text
                clean=True,  # Clean up artifacts
                optimize=1,  # Optimize output file size
                pdf_renderer="hocr",  # Use hOCR for better text positioning
                force_ocr=False,  # Only OCR pages that need it
                skip_text=False,  # Don't skip existing text
                redo_ocr=False,  # Don't redo existing OCR
                progress_bar=False,
                quiet=True,
            )

            # Get processed PDF data
            processed_data = output_buffer.getvalue()
            output_buffer.close()
            input_buffer.close()

        except Exception as buffer_error:
            # Fallback to temporary files if BytesIO approach fails
            logger.debug(f"BytesIO approach failed for {filename}, falling back to temp files: {buffer_error}")
            processed_data = _preprocess_pdf_with_temp_files(file_data, filename)

        processing_time = time.time() - start_time
        logger.info(f"OCRmyPDF completed for {filename} in {processing_time:.2f} seconds")

        return processed_data

    except Exception as e:
        logger.error(f"OCRmyPDF preprocessing failed for {filename}: {e}")
        return file_data


def _preprocess_pdf_with_temp_files(file_data: bytes, filename: str) -> bytes:
    """
    Fallback implementation using unique temporary files to avoid concurrency issues.
    """
    input_temp_file = None
    output_temp_file = None

    try:
        # Generate unique identifiers to avoid filename collisions in concurrent jobs
        unique_id = str(uuid4())
        temp_dir = tempfile.gettempdir()

        # Create input temp file with unique identifier
        input_temp_file = tempfile.NamedTemporaryFile(
            suffix=".pdf", prefix=f"ocr_input_{unique_id}_", dir=temp_dir, delete=False
        )
        input_temp_file.write(file_data)
        input_temp_file.flush()
        input_temp_file.close()

        # Create output temp file with unique identifier
        output_temp_file = tempfile.NamedTemporaryFile(
            suffix=".pdf", prefix=f"ocr_output_{unique_id}_", dir=temp_dir, delete=False
        )
        output_temp_file.close()

        # OCRmyPDF configuration for optimal processing
        ocrmypdf.ocr(
            input_temp_file.name,
            output_temp_file.name,
            language=["eng"],  # Can be configured for other languages
            rotate_pages=True,  # Auto-rotate pages with horizontal text
            deskew=True,  # Fix skewed text
            clean=True,  # Clean up artifacts
            optimize=1,  # Optimize output file size
            pdf_renderer="hocr",  # Use hOCR for better text positioning
            force_ocr=False,  # Only OCR pages that need it
            skip_text=False,  # Don't skip existing text
            redo_ocr=False,  # Don't redo existing OCR
            progress_bar=False,
            quiet=True,
        )

        # Read processed PDF data
        with open(output_temp_file.name, "rb") as f:
            processed_data = f.read()

        return processed_data

    finally:
        # Clean up temporary files
        for temp_file in [input_temp_file, output_temp_file]:
            if temp_file is not None:
                try:
                    if hasattr(temp_file, "name"):
                        os.unlink(temp_file.name)
                except OSError as e:
                    logger.warning(f"Failed to clean up temp file: {e}")
