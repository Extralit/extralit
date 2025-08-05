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
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings

try:
    pass

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from pdf2image import convert_from_bytes
    from PIL import ImageChops
    from PIL.Image import Image as PILImage

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import ocrmypdf

    OCRMYPDF_AVAILABLE = True
except ImportError:
    OCRMYPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PDFProcessingResult:
    """
    Result of PDF preprocessing containing both processed data and analysis metadata.
    """

    processed_data: bytes
    metadata: Dict


class PDFAnalyzer:
    """
    Analyzes PDF layout structure to detect margins, headers, footers, and other regions.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze_pdf_layout(self, pdf_data: bytes, filename: str) -> Dict:
        """
        Analyze PDF layout to extract margin and region information.

        Args:
            pdf_data: PDF file data as bytes
            filename: Filename for logging

        Returns:
            Dictionary containing layout analysis metadata
        """
        if not (PDF2IMAGE_AVAILABLE and CV2_AVAILABLE):
            self.logger.warning("PDF analysis requires pdf2image and cv2, skipping layout analysis")
            return {"analysis_available": False, "error": "Missing dependencies"}

        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_data, dpi=150)  # Lower DPI for analysis
            if not images:
                return {"analysis_available": False, "error": "No pages found"}

            self.logger.info(f"Analyzing layout for {filename} with {len(images)} pages")

            # Analyze layout
            layout_data = self._analyze_page_layout(images)

            return {
                "analysis_available": True,
                "total_pages": len(images),
                "page_dimensions": {"width": images[0].size[0], "height": images[0].size[1]} if images else {},
                **layout_data,
            }

        except Exception as e:
            self.logger.error(f"PDF layout analysis failed for {filename}: {e}")
            return {"analysis_available": False, "error": str(e)}

    def _analyze_page_layout(self, images: List[PILImage]) -> Dict:
        """
        Analyze page layout by comparing pages to find common regions.
        """
        if len(images) < 2:
            return self._analyze_single_page(images[0]) if images else {}

        # Use first page as reference, compare with others
        reference_img = images[0].convert("RGB")
        margin_data = []

        for i in range(1, min(len(images), 5)):  # Analyze up to 5 pages for efficiency
            compare_img = images[i].convert("RGB")
            page_margins = self._compare_pages_for_margins(reference_img, compare_img)
            if page_margins:
                margin_data.append(page_margins)

        # Aggregate margin data
        if margin_data:
            return self._aggregate_margin_data(margin_data, reference_img.size)
        else:
            return self._analyze_single_page(reference_img)

    def _compare_pages_for_margins(self, reference: PILImage, compare: PILImage) -> Optional[Dict]:
        """
        Compare two pages to identify common regions (headers, footers, margins).
        """
        try:
            # Ensure same size
            if reference.size != compare.size:
                compare = compare.resize(reference.size)

            # Compute difference and create sameness mask
            diff = ImageChops.difference(reference, compare)
            sameness_mask = ImageChops.invert(diff.convert("L"))

            # Find horizontal bands (potential headers/footers)
            horizontal_bands = self._find_horizontal_bands(sameness_mask)

            # Classify regions
            regions = self._classify_regions(horizontal_bands, reference.size)

            return regions

        except Exception as e:
            self.logger.debug(f"Page comparison failed: {e}")
            return None

    def _find_horizontal_bands(
        self, mask: PILImage, min_height: int = 15, min_ratio: float = 0.95
    ) -> List[Tuple[int, int]]:
        """
        Find horizontal bands of similar content across pages.
        """
        mask_np = np.array(mask.convert("L"))
        h, w = mask_np.shape

        # Calculate row-wise similarity
        row_sums = np.sum(mask_np == 255, axis=1) / w
        same_rows = row_sums >= min_ratio

        # Find contiguous bands
        bands = []
        start = None

        for i, is_same in enumerate(same_rows):
            if is_same and start is None:
                start = i
            elif not is_same and start is not None:
                if i - start >= min_height:
                    bands.append((start, i))
                start = None

        # Handle band that extends to end
        if start is not None and h - start >= min_height:
            bands.append((start, h))

        return bands

    def _classify_regions(self, bands: List[Tuple[int, int]], page_size: Tuple[int, int]) -> Dict:
        """
        Classify horizontal bands into headers, footers, and margins.
        """
        width, height = page_size
        regions = {"header_bands": [], "footer_bands": [], "estimated_margins": {}}

        for start_y, end_y in bands:
            band_center = (start_y + end_y) / 2
            band_height = end_y - start_y

            # Classify based on position
            if band_center < height * 0.25:  # Top 25%
                regions["header_bands"].append({"start_y": start_y, "end_y": end_y, "height": band_height})
            elif band_center > height * 0.75:  # Bottom 25%
                regions["footer_bands"].append({"start_y": start_y, "end_y": end_y, "height": band_height})

        # Estimate margins based on bands
        regions["estimated_margins"] = self._estimate_margins_from_bands(regions, page_size)

        return regions

    def _estimate_margins_from_bands(self, regions: Dict, page_size: Tuple[int, int]) -> Dict:
        """
        Estimate page margins based on detected bands.
        """
        width, height = page_size
        margins = {
            "top": 0,
            "bottom": 0,
            "left": 50,  # Default estimates
            "right": 50,
        }

        # Calculate top margin from header bands
        if regions["header_bands"]:
            max_header_end = max(band["end_y"] for band in regions["header_bands"])
            margins["top"] = max_header_end

        # Calculate bottom margin from footer bands
        if regions["footer_bands"]:
            min_footer_start = min(band["start_y"] for band in regions["footer_bands"])
            margins["bottom"] = height - min_footer_start

        # Convert to relative percentages for consistency
        return {
            "top_px": margins["top"],
            "bottom_px": margins["bottom"],
            "left_px": margins["left"],
            "right_px": margins["right"],
            "top_percent": (margins["top"] / height) * 100,
            "bottom_percent": (margins["bottom"] / height) * 100,
            "left_percent": (margins["left"] / width) * 100,
            "right_percent": (margins["right"] / width) * 100,
        }

    def _aggregate_margin_data(self, margin_data: List[Dict], page_size: Tuple[int, int]) -> Dict:
        """
        Aggregate margin data from multiple page comparisons.
        """
        # Average the margin estimates
        all_margins = [data.get("estimated_margins", {}) for data in margin_data if data.get("estimated_margins")]

        if not all_margins:
            return self._analyze_single_page_size(page_size)

        # Calculate average margins
        avg_margins = {}
        for key in [
            "top_px",
            "bottom_px",
            "left_px",
            "right_px",
            "top_percent",
            "bottom_percent",
            "left_percent",
            "right_percent",
        ]:
            values = [m.get(key, 0) for m in all_margins if key in m]
            avg_margins[key] = sum(values) / len(values) if values else 0

        # Collect all bands
        all_header_bands = []
        all_footer_bands = []

        for data in margin_data:
            all_header_bands.extend(data.get("header_bands", []))
            all_footer_bands.extend(data.get("footer_bands", []))

        return {
            "layout_analysis": {
                "header_bands": all_header_bands,
                "footer_bands": all_footer_bands,
                "estimated_margins": avg_margins,
                "analysis_method": "multi_page_comparison",
            }
        }

    def _analyze_single_page(self, image: PILImage) -> Dict:
        """
        Analyze a single page when comparison isn't possible.
        """
        return self._analyze_single_page_size(image.size)

    def _analyze_single_page_size(self, page_size: Tuple[int, int]) -> Dict:
        """
        Provide default margin estimates for single page analysis.
        """
        width, height = page_size

        # Use common academic paper margins as defaults
        default_margins = {
            "top_px": int(height * 0.1),  # 10% top margin
            "bottom_px": int(height * 0.1),  # 10% bottom margin
            "left_px": int(width * 0.1),  # 10% left margin
            "right_px": int(width * 0.1),  # 10% right margin
            "top_percent": 10.0,
            "bottom_percent": 10.0,
            "left_percent": 10.0,
            "right_percent": 10.0,
        }

        return {
            "layout_analysis": {
                "header_bands": [],
                "footer_bands": [],
                "estimated_margins": default_margins,
                "analysis_method": "default_estimates",
            }
        }


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
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.analyzer = PDFAnalyzer()

        if not self.settings.enabled:
            self.logger.info("PDF preprocessing is disabled via configuration")
        elif not OCRMYPDF_AVAILABLE:
            self.logger.warning("OCRmyPDF not available, PDF preprocessing will be skipped")

    def preprocess(self, file_data: bytes, filename: str) -> PDFProcessingResult:
        """
        Preprocess PDF with OCRmyPDF and analyze layout structure.

        Args:
            file_data: PDF file data as bytes
            filename: Original filename for logging purposes

        Returns:
            PDFProcessingResult containing processed data and layout analysis metadata
        """
        # Initialize metadata
        metadata = {
            "preprocessing_enabled": self.settings.enabled,
            "ocrmypdf_available": OCRMYPDF_AVAILABLE,
            "original_filename": filename,
            "processing_timestamp": time.time(),
        }

        # Handle non-PDF files or disabled preprocessing
        if not filename.lower().endswith(".pdf"):
            metadata["skipped_reason"] = "not_pdf"
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        if not self.settings.enabled:
            self.logger.debug(f"PDF preprocessing disabled, skipping: {filename}")
            metadata["skipped_reason"] = "preprocessing_disabled"
            # Still run analysis on original data
            layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
            metadata.update(layout_analysis)
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        if not OCRMYPDF_AVAILABLE:
            self.logger.warning("OCRmyPDF not available, skipping preprocessing")
            metadata["skipped_reason"] = "ocrmypdf_unavailable"
            # Still run analysis on original data
            layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
            metadata.update(layout_analysis)
            return PDFProcessingResult(processed_data=file_data, metadata=metadata)

        try:
            start_time = time.time()
            self.logger.info(f"Starting PDF preprocessing and analysis for: {filename}")

            # Step 1: Analyze original PDF layout
            self.logger.debug("Analyzing PDF layout structure...")
            layout_analysis = self.analyzer.analyze_pdf_layout(file_data, filename)
            metadata.update(layout_analysis)

            # Step 2: OCR preprocessing
            self.logger.debug("Starting OCRmyPDF processing...")
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

                metadata["ocr_method"] = "bytesio"

            except Exception as buffer_error:
                self.logger.debug(f"BytesIO approach failed for {filename}, falling back to temp files: {buffer_error}")
                processed_data = self._preprocess_with_temp_files(file_data, filename)
                metadata["ocr_method"] = "temp_files"
                metadata["ocr_fallback_reason"] = str(buffer_error)

            processing_time = time.time() - start_time
            metadata["processing_time_seconds"] = processing_time
            metadata["processing_successful"] = True

            self.logger.info(f"PDF preprocessing completed for {filename} in {processing_time:.2f} seconds")

            return PDFProcessingResult(processed_data=processed_data, metadata=metadata)

        except Exception as e:
            self.logger.error(f"PDF preprocessing failed for {filename}: {e}")
            metadata["processing_successful"] = False
            metadata["processing_error"] = str(e)
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
    result = pdf_preprocessor.preprocess(file_data, filename)
    return result.processed_data
