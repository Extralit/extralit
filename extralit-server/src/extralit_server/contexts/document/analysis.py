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
PDF text layer detection using OCRmyPDF internal functions.

This module provides functionality to detect whether a PDF already has an OCR text layer
by leveraging OCRmyPDF's internal PdfInfo and PageInfo classes.
"""

import logging
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union
from concurrent.futures import ThreadPoolExecutor

try:
    from ocrmypdf.pdfinfo.info import PageInfo
    from ocrmypdf.exceptions import EncryptedPdfError, InputFileError
    from ocrmypdf._pipeline import get_pdfinfo
    from ocrmypdf._concurrent import Executor
except ImportError as e:
    raise ImportError(
        "OCRmyPDF is required for PDF text layer detection. " "Please install it with: pip install ocrmypdf"
    ) from e

_LOGGER = logging.getLogger(__name__)

DEFAULT_EXECUTOR = ThreadPoolExecutor(max_workers=1)


@dataclass
class PageTextInfo:
    """Information about text content on a specific PDF page."""

    page_number: int
    has_text: bool
    has_images: bool
    has_corrupt_text: bool = False
    width_pixels: Optional[int] = None
    height_pixels: Optional[int] = None
    text_extraction_confidence: Optional[float] = None
    needs_ocr: bool = True


@dataclass
class PDFTextAnalysisResult:
    """Result of PDF text layer analysis."""

    total_pages: int
    has_text_layer: bool
    pages_with_text: int
    pages_with_images: int
    pages_needing_ocr: int
    is_encrypted: bool
    analysis_error: Optional[str] = None
    pages: List[PageTextInfo] = field(default_factory=list)


class PDFTextLayerDetector:
    """
    Detector for PDF text layers using OCRmyPDF internal functions.

    This class uses OCRmyPDF's PdfInfo to analyze PDF pages and determine
    which pages already have text content and which would require OCR processing.
    """

    def __init__(self, executor: Optional["Executor"] = None):
        """
        Initialize the PDF text layer detector.

        Args:
            executor: Optional executor for concurrent processing. Defaults to ThreadPoolExecutor.
        """
        self.executor = executor or DEFAULT_EXECUTOR

    def detect_text_layer(
        self,
        pdf_data: Union[bytes, str, Path],
        filename: str,
        detailed_analysis: bool = True,
        check_pages: Optional[range] = None,
    ) -> PDFTextAnalysisResult:
        """
        Detect if a PDF has an OCR text layer.

        Args:
            pdf_data: PDF data as bytes, file path string, or Path object
            filename: Filename for logging and identification (required)
            detailed_analysis: Whether to perform detailed page-by-page analysis
            check_pages: Optional range of pages to check (None = check all pages)

        Returns:
            PDFTextAnalysisResult containing text layer analysis information
        """
        # Handle different input types
        if isinstance(pdf_data, bytes):
            # Use BytesIO for bytes input - OCRmyPDF can work with file-like objects
            input_file = BytesIO(pdf_data)
        else:
            # Handle string or Path input
            input_path = Path(pdf_data)
            if filename is None:
                filename = input_path.name
            input_file = input_path

        try:
            # Use OCRmyPDF's get_pdfinfo function to analyze the PDF
            pdf_info = get_pdfinfo(
                input_file,
                executor=self.executor,  # type: ignore
                detailed_analysis=detailed_analysis,
                progbar=False,
                check_pages=check_pages,
            )

            # Analyze pages
            pages_info = []
            pages_with_text = 0
            pages_with_images = 0
            pages_needing_ocr = 0

            for page_num, page_info in enumerate(pdf_info.pages):
                if page_info is None:
                    continue

                # Create PageTextInfo from OCRmyPDF's PageInfo
                page_text_info = PageTextInfo(
                    page_number=page_num + 1,  # 1-based page numbering
                    has_text=page_info.has_text,
                    has_images=bool(page_info.images),
                    has_corrupt_text=getattr(page_info, "has_corrupt_text", False),
                    width_pixels=getattr(page_info, "width_pixels", None),
                    height_pixels=getattr(page_info, "height_pixels", None),
                    needs_ocr=self._determine_ocr_requirement(page_info),
                )

                pages_info.append(page_text_info)

                if page_text_info.has_text:
                    pages_with_text += 1
                if page_text_info.has_images:
                    pages_with_images += 1
                if page_text_info.needs_ocr:
                    pages_needing_ocr += 1

            # Determine overall text layer status
            has_text_layer = pages_with_text > 0

            result = PDFTextAnalysisResult(
                total_pages=len(pdf_info.pages),
                has_text_layer=has_text_layer,
                pages_with_text=pages_with_text,
                pages_with_images=pages_with_images,
                pages_needing_ocr=pages_needing_ocr,
                is_encrypted=False,
                pages=pages_info,
            )

            _LOGGER.info(
                f"PDF text analysis for {filename}: "
                f"{pages_with_text}/{len(pdf_info.pages)} pages have text, "
                f"{pages_needing_ocr} pages need OCR"
            )

            return result

        except EncryptedPdfError:
            _LOGGER.warning(f"PDF {filename} is encrypted")
            return PDFTextAnalysisResult(
                total_pages=0,
                has_text_layer=False,
                pages_with_text=0,
                pages_with_images=0,
                pages_needing_ocr=0,
                is_encrypted=True,
                analysis_error="PDF is encrypted",
            )

        except InputFileError as e:
            _LOGGER.error(f"Invalid PDF file {filename}: {e}")
            return PDFTextAnalysisResult(
                total_pages=0,
                has_text_layer=False,
                pages_with_text=0,
                pages_with_images=0,
                pages_needing_ocr=0,
                is_encrypted=False,
                analysis_error=f"Invalid PDF file: {e}",
            )

        except Exception as e:
            _LOGGER.error(f"PDF text analysis failed for {filename}: {e}")
            return PDFTextAnalysisResult(
                total_pages=0,
                has_text_layer=False,
                pages_with_text=0,
                pages_with_images=0,
                pages_needing_ocr=0,
                is_encrypted=False,
                analysis_error=str(e),
            )

    def _determine_ocr_requirement(self, page_info: PageInfo) -> bool:
        """
        Determine if a page requires OCR processing based on OCRmyPDF logic.

        This mirrors the logic from OCRmyPDF's is_ocr_required function but
        simplified for detection purposes.

        Args:
            page_info: PageInfo object from OCRmyPDF

        Returns:
            True if the page needs OCR, False otherwise
        """
        # If page has text, it typically doesn't need OCR (unless forcing)
        if page_info.has_text:
            return False

        # If page has images, it likely needs OCR
        if page_info.images:
            return True

        # If page has no text and no images, it might be vector art
        # For detection purposes, we'll assume it doesn't need OCR
        return False

    def has_text_layer(self, pdf_data: Union[bytes, str, Path], filename: str) -> bool:
        """
        Simple boolean check if PDF has any text layer.

        Args:
            pdf_data: PDF data as bytes, file path string, or Path object
            filename: Filename for logging (required)

        Returns:
            True if PDF has any text content, False otherwise
        """
        result = self.detect_text_layer(pdf_data, filename, detailed_analysis=False)
        return result.has_text_layer and result.analysis_error is None

    def get_pages_needing_ocr(self, pdf_data: Union[bytes, str, Path], filename: str) -> List[int]:
        """
        Get list of page numbers that need OCR processing.

        Args:
            pdf_data: PDF data as bytes, file path string, or Path object
            filename: Filename for logging (required)

        Returns:
            List of 1-based page numbers that need OCR
        """
        result = self.detect_text_layer(pdf_data, filename, detailed_analysis=True)
        if result.analysis_error:
            return []

        return [page.page_number for page in result.pages if page.needs_ocr]
