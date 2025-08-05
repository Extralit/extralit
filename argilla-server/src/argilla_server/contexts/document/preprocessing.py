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
from typing import List, Optional
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings

try:
    import ocrmypdf

    OCRMYPDF_AVAILABLE = True
except ImportError:
    OCRMYPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFPreprocessingSettings(BaseSettings):
    """
    PDF preprocessing settings that can be configured via environment variables.

    All settings have the PREPROCESSING_ prefix.
    """

    enabled: bool = Field(
        default=True, description="Enable PDF preprocessing with OCRmyPDF. Set to False to disable all processing."
    )

    language: List[str] = Field(
        default=["eng"], description="List of languages for OCR processing (e.g., ['eng', 'spa', 'fra'])"
    )

    rotate_pages: bool = Field(default=True, description="Auto-rotate pages with horizontal text")

    deskew: bool = Field(default=True, description="Fix skewed text")

    clean: bool = Field(default=True, description="Clean up artifacts")

    optimize: int = Field(
        default=1, description="Optimize output file size (0=none, 1=lossless, 2=lossy, 3=aggressive)"
    )

    pdf_renderer: str = Field(default="hocr", description="PDF renderer: 'auto', 'hocr', 'sandwich'")

    force_ocr: bool = Field(default=False, description="Force OCR on all pages, even if they already have text")

    skip_text: bool = Field(default=False, description="Skip text-based operations (OCR only for images)")

    redo_ocr: bool = Field(default=False, description="Redo OCR on pages that already have OCR")

    progress_bar: bool = Field(default=False, description="Show progress bar during processing")

    quiet: bool = Field(default=True, description="Suppress OCRmyPDF output messages")

    class Config:
        env_prefix = "PREPROCESSING_"


class PDFPreprocessor:
    """
    PDF preprocessor that uses OCRmyPDF for rotation, OCR, and optimization.

    Can be configured with environment variables using the PDFPreprocessingSettings.
    """

    def __init__(self, settings: Optional[PDFPreprocessingSettings] = None):
        """
        Initialize the PDF preprocessor.

        Args:
            settings: Optional PDFPreprocessingSettings instance. If None, loads from environment.
        """
        self.settings = settings or PDFPreprocessingSettings()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if not self.settings.enabled:
            self.logger.info("PDF preprocessing is disabled via configuration")
        elif not OCRMYPDF_AVAILABLE:
            self.logger.warning("OCRmyPDF not available, PDF preprocessing will be skipped")

    def preprocess(self, file_data: bytes, filename: str) -> bytes:
        """
        Preprocess PDF with OCRmyPDF using configured settings.

        Args:
            file_data: PDF file data as bytes
            filename: Original filename for logging purposes

        Returns:
            Processed PDF data as bytes (or original bytes if processing fails/disabled)
        """
        if not self.settings.enabled:
            self.logger.debug(f"PDF preprocessing disabled, skipping: {filename}")
            return file_data

        if not OCRMYPDF_AVAILABLE:
            self.logger.warning("OCRmyPDF not available, skipping preprocessing")
            return file_data

        if not filename.lower().endswith(".pdf"):
            return file_data

        try:
            start_time = time.time()
            self.logger.info(f"Starting OCRmyPDF preprocessing for: {filename}")

            try:
                input_buffer = BytesIO(file_data)
                output_buffer = BytesIO()

                ocrmypdf.ocr(
                    input_buffer,
                    output_buffer,
                    language=self.settings.language,
                    rotate_pages=self.settings.rotate_pages,
                    deskew=self.settings.deskew,
                    clean=self.settings.clean,
                    optimize=self.settings.optimize,
                    pdf_renderer=self.settings.pdf_renderer,
                    force_ocr=self.settings.force_ocr,
                    skip_text=self.settings.skip_text,
                    redo_ocr=self.settings.redo_ocr,
                    progress_bar=self.settings.progress_bar,
                    quiet=self.settings.quiet,
                )

                processed_data = output_buffer.getvalue()
                output_buffer.close()
                input_buffer.close()

            except Exception as buffer_error:
                self.logger.debug(f"BytesIO approach failed for {filename}, falling back to temp files: {buffer_error}")
                processed_data = self._preprocess_with_temp_files(file_data, filename)

            processing_time = time.time() - start_time
            self.logger.info(f"OCRmyPDF completed for {filename} in {processing_time:.2f} seconds")

            return processed_data

        except Exception as e:
            self.logger.error(f"OCRmyPDF preprocessing failed for {filename}: {e}")
            return file_data

    def _preprocess_with_temp_files(self, file_data: bytes, filename: str) -> bytes:
        """
        Fallback implementation using unique temporary files to avoid concurrency issues.
        """
        input_temp_file = None
        output_temp_file = None

        try:
            unique_id = str(uuid4())
            temp_dir = tempfile.gettempdir()

            input_temp_file = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix=f"ocr_input_{unique_id}_", dir=temp_dir, delete=False
            )
            input_temp_file.write(file_data)
            input_temp_file.flush()
            input_temp_file.close()

            output_temp_file = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix=f"ocr_output_{unique_id}_", dir=temp_dir, delete=False
            )
            output_temp_file.close()

            ocrmypdf.ocr(
                input_temp_file.name,
                output_temp_file.name,
                language=self.settings.language,
                rotate_pages=self.settings.rotate_pages,
                deskew=self.settings.deskew,
                clean=self.settings.clean,
                optimize=self.settings.optimize,
                pdf_renderer=self.settings.pdf_renderer,
                force_ocr=self.settings.force_ocr,
                skip_text=self.settings.skip_text,
                redo_ocr=self.settings.redo_ocr,
                progress_bar=self.settings.progress_bar,
                quiet=self.settings.quiet,
            )

            with open(output_temp_file.name, "rb") as f:
                processed_data = f.read()

            return processed_data

        finally:
            for temp_file in [input_temp_file, output_temp_file]:
                if temp_file is not None:
                    try:
                        if hasattr(temp_file, "name"):
                            os.unlink(temp_file.name)
                    except OSError as e:
                        self.logger.warning(f"Failed to clean up temp file: {e}")


# Global preprocessor instance (can be configured via environment variables)
pdf_preprocessor = PDFPreprocessor()


def preprocess_pdf_with_ocrmypdf(file_data: bytes, filename: str) -> bytes:
    """
    Preprocess PDF with OCRmyPDF to add OCR layer and fix orientation.

    This function provides backward compatibility by using the global pdf_preprocessor instance.
    For new code, consider using PDFPreprocessor directly for better configuration control.

    Args:
        file_data: PDF file data as bytes
        filename: Original filename for logging purposes

    Returns:
        Processed PDF data as bytes (or original bytes if processing fails)
    """
    return pdf_preprocessor.preprocess(file_data, filename)
