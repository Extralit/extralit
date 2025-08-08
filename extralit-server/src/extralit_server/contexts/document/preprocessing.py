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
import shutil
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Tuple
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

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


def _is_scanned_pdf_bytes(file_data: bytes, method: str = "simple",
                         text_threshold: float = 0.1, sample_pages: int = 5) -> bool:
    """
    Detect if PDF is scanned (image-based) or born-digital based on text content.

    Args:
        file_data: PDF file data as bytes
        method: Detection method - "simple" (no text check) or "density" (text density analysis)
        text_threshold: Text density threshold for density method
        sample_pages: Number of pages to sample

    Returns:
        True if PDF appears to be scanned, False if born-digital
    """
    if not FITZ_AVAILABLE:
        _LOGGER.warning("PyMuPDF not available, assuming PDF is scanned")
        return True

    try:
        doc = fitz.open(stream=file_data, filetype="pdf")

        if len(doc) == 0:
            doc.close()
            return False

        if method == "simple":
            # Simple method: check if any page has extractable text
            pages_to_check = min(sample_pages, len(doc))
            for i in range(pages_to_check):
                text = doc[i].get_text().strip()
                if text:
                    doc.close()
                    return False  # Found text, not scanned
            doc.close()
            return True  # No text found, likely scanned

        elif method == "density":
            # Density method: calculate text density across pages
            total_chars = 0
            total_area = 0
            pages_to_check = min(sample_pages, len(doc))

            for page_num in range(pages_to_check):
                page = doc[page_num]
                text = page.get_text()
                total_chars += len(text.strip())
                total_area += page.rect.width * page.rect.height

            doc.close()

            if total_area == 0:
                return True

            text_density = total_chars / total_area
            is_scanned = text_density < text_threshold

            _LOGGER.debug(f"PDF text density analysis: {total_chars} chars, density: {text_density:.6f}, scanned: {is_scanned}")
            return is_scanned

        else:
            doc.close()
            raise ValueError(f"Unknown detection method: {method}")

    except Exception as e:
        _LOGGER.error(f"Error analyzing PDF for scanned detection: {e}")
        return True  # Assume scanned on error


def _supports_clean() -> bool:
    """Check if 'unpaper' is available on PATH (required for clean=True)."""
    return shutil.which("unpaper") is not None


def _filter_supported_args(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only kwargs supported by ocrmypdf.ocr to avoid version issues."""
    allowed = {
        "language",
        "rotate_pages",
        "rotate_pages_threshold",
        "deskew",
        "clean",
        "optimize",
        "pdf_renderer",
        "force_ocr",
        "skip_text",
        "redo_ocr",
        "progress_bar",
        "output_type",
        "tesseract_timeout",
        "use_threads",
        "jobs",
        "quiet",
    }
    return {k: v for k, v in kwargs.items() if k in allowed}


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
        default=1, description="Optimize output file size (0=none, 1=lossless, 2=lossy, 3=aggressive)"
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

    # Scanned PDF detection settings
    scanned_detection_method: str = Field(
        default="simple",
        description="Method for detecting scanned PDFs: 'simple' (no text check) or 'density' (text density analysis)"
    )

    text_density_threshold: float = Field(
        default=0.1,
        description="Text density threshold for scanned detection (chars per pixel area)"
    )

    sample_pages: int = Field(
        default=5,
        description="Number of pages to sample for scanned detection"
    )

    skip_ocr_for_born_digital: bool = Field(
        default=True,
        description="Skip OCR processing for born-digital PDFs (unless force_ocr is True)"
    )

    # LitServe integration settings
    use_litserve: bool = Field(
        default=False,
        description="Use LitServe endpoint for OCR processing instead of local OCRmyPDF"
    )

    litserve_url: Optional[str] = Field(
        default=None,
        description="LitServe endpoint URL for OCR processing"
    )

    def get_ocrmypdf_args(self) -> Dict[str, Any]:
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
        metadata = {
            "engine": "ocrmypdf",
            "filename": filename,
            "ocr_applied": False,
            "pdf_type": None,
            "used_clean": False,
            "processing_time_seconds": None,
            "notes": [],
        }

        # Handle non-PDF files or disabled preprocessing
        if not filename.lower().endswith(".pdf"):
            metadata["notes"].append("Non-PDF input; skipping preprocessing")
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        if not self.settings.enabled:
            metadata["notes"].append("PDF preprocessing disabled via configuration")
            if self.analyzer:
                layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
                metadata.update(layout_analysis)
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        if not OCRMYPDF_AVAILABLE and not self.settings.use_litserve:
            _LOGGER.warning("OCRmyPDF not available and LitServe not configured, skipping preprocessing")
            metadata["notes"].append("OCRmyPDF not available and LitServe not configured")
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

            # Step 2: Check if PDF is scanned and needs OCR
            is_scanned = _is_scanned_pdf_bytes(
                file_data,
                method=self.settings.scanned_detection_method,
                text_threshold=self.settings.text_density_threshold,
                sample_pages=self.settings.sample_pages
            )

            metadata["pdf_type"] = "scanned" if is_scanned else "born_digital"

            # Skip OCR for born-digital PDFs unless forced
            if not is_scanned and self.settings.skip_ocr_for_born_digital and not self.settings.force_ocr:
                _LOGGER.info(f"📄 Born-digital PDF detected → skipping OCR for {filename}")
                metadata["notes"].append("Skipped OCR (born-digital detected)")
                processing_time = time.time() - start_time
                metadata["processing_time_seconds"] = processing_time
                return PDFProcessingResult(processed_data=file_data, metadata=metadata)

            # Step 3: OCR preprocessing
            _LOGGER.info(f"🧾 {'Scanned' if is_scanned else 'Forced OCR on'} PDF detected → running OCR on {filename}")

            if self.settings.use_litserve and self.settings.litserve_url:
                processed_data = self._preprocess_with_litserve(file_data, filename, metadata)
            else:
                processed_data = self._preprocess_with_ocrmypdf(file_data, filename, metadata)

            processing_time = time.time() - start_time
            metadata["processing_time_seconds"] = processing_time
            metadata["ocr_applied"] = True
            _LOGGER.info(f"PDF preprocessing completed for {filename} in {processing_time:.2f} seconds")

            return PDFProcessingResult(processed_data=processed_data, metadata=metadata)

        except Exception as e:
            _LOGGER.error(f"PDF preprocessing failed for {filename}: {e}")
            metadata["notes"].append(f"Preprocessing failed: {str(e)}")
            processing_time = time.time() - start_time
            metadata["processing_time_seconds"] = processing_time
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

    def _preprocess_with_ocrmypdf(self, file_data: bytes, filename: str, metadata: Dict[str, Any]) -> bytes:
        """
        Preprocess PDF using OCRmyPDF with enhanced error handling and metadata tracking.
        """
        if not OCRMYPDF_AVAILABLE:
            raise RuntimeError("OCRmyPDF not available")

        # Check and adjust clean setting based on unpaper availability
        effective_clean = bool(self.settings.clean and _supports_clean())
        if self.settings.clean and not effective_clean:
            metadata["notes"].append("clean=True requested but 'unpaper' not found; disabling clean")
        metadata["used_clean"] = effective_clean

        # Get OCRmyPDF arguments and apply clean setting
        ocr_args = self.settings.get_ocrmypdf_args()
        ocr_args["clean"] = effective_clean
        ocr_args = _filter_supported_args(ocr_args)

        # Try in-memory processing first
        try:
            input_buffer = BytesIO(file_data)
            output_buffer = BytesIO()

            ocrmypdf.ocr(input_buffer, output_buffer, **ocr_args)

            processed_data = output_buffer.getvalue()
            output_buffer.close()
            input_buffer.close()

            return processed_data

        except Exception as buffer_error:
            metadata["notes"].append(f"In-memory OCR failed; falling back to temp files: {buffer_error}")
            _LOGGER.debug(f"BytesIO approach failed for {filename}, falling back to temp files: {buffer_error}")
            return self._preprocess_with_temp_files(file_data, ocr_args)

    def _preprocess_with_litserve(self, file_data: bytes, filename: str, metadata: Dict[str, Any]) -> bytes:
        """
        Preprocess PDF using LitServe endpoint.
        """
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests library not available for LitServe integration")

        if not self.settings.litserve_url:
            raise RuntimeError("LitServe URL not configured")

        try:
            response = requests.post(
                self.settings.litserve_url,
                files={"file": ("document.pdf", file_data, "application/pdf")},
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200:
                raise RuntimeError(f"LitServe OCR failed with status {response.status_code}: {response.text}")

            metadata["notes"].append("Processed using LitServe endpoint")
            return response.content

        except Exception as e:
            _LOGGER.error(f"LitServe OCR failed for {filename}: {e}")
            metadata["notes"].append(f"LitServe OCR failed: {str(e)}")
            # Fallback to local OCRmyPDF if available
            if OCRMYPDF_AVAILABLE:
                metadata["notes"].append("Falling back to local OCRmyPDF")
                return self._preprocess_with_ocrmypdf(file_data, filename, metadata)
            else:
                raise RuntimeError("LitServe failed and OCRmyPDF not available")

    def _preprocess_with_temp_files(self, file_data: bytes, ocr_args: Dict[str, Any]) -> bytes:
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

            ocrmypdf.ocr(input_temp_file.name, output_temp_file.name, **ocr_args)

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


def preprocess_pdf_bytes_with_ocrmypdf(
    file_data: bytes,
    filename: str = "document.pdf",
    *,
    language: Tuple[str, ...] = ("eng",),
    rotate_pages: bool = True,
    rotate_pages_threshold: float = 2.0,
    deskew: bool = True,
    clean: bool = False,
    optimize: int = 1,
    pdf_renderer: str = "hocr",
    force_ocr: bool = False,
    skip_text: bool = True,
    redo_ocr: bool = False,
    progress_bar: bool = False,
    output_type: str = "pdf",
    tesseract_timeout: int = 0,
    always_run: bool = False,
    use_litserve: bool = False,
    litserve_url: Optional[str] = None,
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Bytes-in → bytes-out OCR preprocessing with OCRmyPDF.

    This function matches the interface from your examples and provides fine-grained control
    over OCRmyPDF settings without requiring environment variable configuration.

    Args:
        file_data: PDF file data as bytes
        filename: Original filename for logging purposes
        language: Languages for OCR processing
        rotate_pages: Auto-rotate pages with horizontal text
        rotate_pages_threshold: Threshold for auto-rotation
        deskew: Fix skewed text
        clean: Use unpaper to clean up artifacts (auto-disabled if unpaper missing)
        optimize: Optimize output (0=none, 1=lossless, 2=lossy, 3=aggressive)
        pdf_renderer: PDF renderer ('hocr', 'sandwich', 'auto')
        force_ocr: Force OCR on all pages
        skip_text: Skip text-based operations
        redo_ocr: Redo OCR on pages with existing OCR
        progress_bar: Show progress bar
        output_type: Output type for OCRmyPDF
        tesseract_timeout: Timeout for Tesseract OCR processing
        always_run: If False, skip OCR for clearly born-digital PDFs
        use_litserve: Use LitServe endpoint instead of local OCRmyPDF
        litserve_url: LitServe endpoint URL

    Returns:
        Tuple of (processed_bytes, metadata_dict)
    """
    # Create custom settings for this call
    settings = PDFPreprocessingSettings(
        enabled=True,
        language=list(language),
        rotate_pages=rotate_pages,
        rotate_pages_threshold=rotate_pages_threshold,
        deskew=deskew,
        clean=clean,
        optimize=optimize,
        pdf_renderer=pdf_renderer,
        force_ocr=force_ocr,
        skip_text=skip_text,
        redo_ocr=redo_ocr,
        progress_bar=progress_bar,
        output_type=output_type,
        tesseract_timeout=tesseract_timeout,
        skip_ocr_for_born_digital=not always_run,
        use_litserve=use_litserve,
        litserve_url=litserve_url,
        enable_analysis=False,  # Disable layout analysis for this function
    )

    # Create preprocessor with custom settings
    preprocessor = PDFPreprocessor(settings)

    # Process the PDF
    result = preprocessor.preprocess(file_data, filename)

    return result.processed_data, result.metadata


def preprocess_file_with_ocrmypdf(
    input_path: Union[str, Path],
    output_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    Path-in → path-out convenience wrapper, mirroring your notebooks.
    Only runs OCR if scanned by default (unless always_run/force_ocr provided).

    Args:
        input_path: Path to input PDF file
        output_path: Path for output PDF (optional, creates temp file if None)
        **kwargs: Additional arguments passed to preprocess_pdf_bytes_with_ocrmypdf

    Returns:
        Path to processed PDF file
    """
    input_path = Path(input_path)

    if output_path is None:
        base = input_path.stem
        output_path = os.path.join(tempfile.gettempdir(), f"{base}_ocr_processed.pdf")

    with open(input_path, "rb") as f:
        data = f.read()

    processed, _meta = preprocess_pdf_bytes_with_ocrmypdf(
        data,
        filename=input_path.name,
        **kwargs
    )

    with open(output_path, "wb") as f:
        f.write(processed)

    return output_path
