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

try:
    from extralit_server.contexts.document.analysis import PDFAnalyzer, PDFProcessingResult

    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False

_LOGGER = logging.getLogger(__name__)


class PDFPreprocessingSettings(BaseSettings):
    """
    PDF preprocessing settings that can be configured via environment variables.

    All settings have the PREPROCESSING_ prefix.
    """

    class Config:
        env_prefix = "PREPROCESSING_"

    enabled: bool = Field(
        default=True, description="Enable PDF preprocessing with OCRmyPDF. Set to False to disable all processing."
    )

    language: List[str] = Field(
        default=["eng"], description="List of languages for OCR processing (e.g., ['eng', 'spa', 'fra'])"
    )

    rotate_pages: bool = Field(default=True, description="Auto-rotate pages with horizontal text")

    rotate_pages_threshold: float = Field(
        default=2.0,
        description="Threshold for auto-rotation",
    )

    deskew: bool = Field(default=False, description="Fix skewed text")

    clean: bool = Field(default=True, description="Use `unpaper` to clean up artifacts")

    optimize: int = Field(
        default=0, description="Optimize output file size (0=none, 1=lossless, 2=lossy, 3=aggressive)"
    )

    pdf_renderer: str = Field(default="hocr", description="PDF renderer: 'auto', 'hocr', 'sandwich'")

    force_ocr: bool = Field(default=False, description="Force OCR on all pages, even if they already have text")

    tesseract_timeout: int = Field(
        default=0, description="Timeout for Tesseract OCR processing in seconds (0 to skip Tesseract OCR)"
    )

    skip_text: bool = Field(default=True, description="Skip text-based operations (OCR only for images)")

    redo_ocr: bool = Field(default=False, description="Redo OCR on pages that already have OCR")

    progress_bar: bool = Field(default=False, description="Show progress bar during processing")

    enable_analysis: bool = Field(default=True, description="Enable PDF layout analysis and margin detection")

    output_type: str = Field(
        default="pdf",
        description="Output type for OCRmyPDF. Set to 'pdf' to skip PDF/A conversion.",
    )

    fast_web_view: int = Field(
        default=999999,
        description="Fast web view optimization. Set to 999999 to disable fast web view optimization.",
    )

    skip_big: bool = Field(
        default=True,
        description="Skip large images if some pages have large images.",
    )

    jobs: int = Field(
        default=1,
        description="Number of worker processes to use for OCR. Set to 1 for Docker containers with limited CPU to avoid oversubscription.",
    )

    def get_ocrmypdf_args(self) -> dict:
        """
        Get OCRmyPDF arguments as a dictionary for use with **kwargs.

        Returns:
            Dictionary of OCRmyPDF arguments excluding input/output parameters.
        """
        return {
            "language": self.language,
            "rotate_pages": self.rotate_pages,
            "rotate_pages_threshold": self.rotate_pages_threshold,
            "deskew": self.deskew,
            "clean": self.clean,
            "optimize": self.optimize,
            "pdf_renderer": self.pdf_renderer,
            "force_ocr": self.force_ocr,
            "skip_text": self.skip_text,
            "tesseract_timeout": self.tesseract_timeout,
            "redo_ocr": self.redo_ocr,
            "progress_bar": self.progress_bar,
            "output_type": self.output_type,
            "fast_web_view": self.fast_web_view,
            "skip_big": self.skip_big,
            "jobs": self.jobs,
        }


class PDFPreprocessor:
    """
    PDF preprocessor that uses OCRmyPDF for rotation, OCR, and optimization.
    Also performs layout analysis to extract margin and structure information.

    Can be configured with environment variables using the PDFPreprocessingSettings.
    """

    def __init__(self, settings: Optional[PDFPreprocessingSettings] = None):
        """
        Initialize the PDF preprocessor.

        Args:
            settings: Optional PDFPreprocessingSettings instance. If None, loads from environment.
        """
        self.settings = settings or PDFPreprocessingSettings()

        # Initialize analyzer if available and enabled
        if self.settings.enable_analysis and ANALYSIS_AVAILABLE:
            self.analyzer = PDFAnalyzer()
        else:
            self.analyzer = None
            if self.settings.enable_analysis and not ANALYSIS_AVAILABLE:
                _LOGGER.warning("PDF analysis is enabled but dependencies are not available")

        if not self.settings.enabled:
            _LOGGER.info("PDF preprocessing is disabled via configuration")
        elif not OCRMYPDF_AVAILABLE:
            _LOGGER.warning("OCRmyPDF not available, PDF preprocessing will be skipped")

    def preprocess(self, file_data: bytes, filename: str) -> PDFProcessingResult:
        """
        Preprocess PDF with OCRmyPDF and analyze layout structure.

        Args:
            file_data: PDF file data as bytes
            filename: Original filename for logging purposes

        Returns:
            PDFProcessingResult containing processed data and layout analysis metadata
        """
        metadata = {}

        # Handle non-PDF files or disabled preprocessing
        if not filename.lower().endswith(".pdf"):
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        if not self.settings.enabled:
            if self.analyzer:
                layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
                metadata.update(layout_analysis)
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        if not OCRMYPDF_AVAILABLE:
            _LOGGER.warning("OCRmyPDF not available, skipping preprocessing")
            # Still run analysis on original data if enabled and available
            if self.analyzer:
                layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
                metadata.update(layout_analysis)
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        try:
            start_time = time.time()

            # Step 1: Analyze original PDF layout (if enabled and available)
            if self.analyzer:
                layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
                metadata.update(layout_analysis)

            # Step 2: OCR preprocessing
            try:
                input_buffer = BytesIO(file_data)
                output_buffer = BytesIO()

                ocrmypdf.ocr(input_buffer, output_buffer, **self.settings.get_ocrmypdf_args())

                processed_data = output_buffer.getvalue()
                output_buffer.close()
                input_buffer.close()

            except Exception as buffer_error:
                _LOGGER.debug(f"BytesIO approach failed for {filename}, falling back to temp files: {buffer_error}")
                processed_data = self._preprocess_with_temp_files(file_data, filename)

            processing_time = time.time() - start_time
            metadata["processing_time_seconds"] = processing_time
            print(metadata)
            _LOGGER.info(f"PDF preprocessing completed for {filename} in {processing_time:.2f} seconds")

            return PDFProcessingResult(processed_data=processed_data, metadata=metadata)

        except Exception as e:
            _LOGGER.error(f"PDF preprocessing failed for {filename}: {e}")
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

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

            ocrmypdf.ocr(input_temp_file.name, output_temp_file.name, **self.settings.get_ocrmypdf_args())

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
                        _LOGGER.warning(f"Failed to clean up temp file: {e}")


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
    result = pdf_preprocessor.preprocess(file_data, filename)
    return result.processed_data
