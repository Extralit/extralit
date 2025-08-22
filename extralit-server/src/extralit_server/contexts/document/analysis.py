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

from io import BytesIO

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTChar, LTTextBox
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage


class PDFOCRLayerDetector:
    def __init__(self):
        self.resource_manager = PDFResourceManager()
        self.laparams = LAParams()
        self.device = PDFPageAggregator(self.resource_manager, laparams=self.laparams)
        self.interpreter = PDFPageInterpreter(self.resource_manager, self.device)

    def has_ocr_text_layer(self, pdf_bytes: bytes, threshold: float = 0.5, verbose=False) -> bool:
        """
        Detect if PDF has OCR text layer by analyzing font resources per page.
        Returns True if more than 50% of pages have font resources (indicating searchable text).

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            bool: True if PDF has OCR text layer, False otherwise
        """
        page_info = self._check_font_resources_per_page(pdf_bytes)

        if not page_info:
            return False

        if verbose:
            print(f"Total pages: {len(page_info)}")
            print(page_info)

        pages_with_fonts = sum(1 for page in page_info if page.get("has_fonts", False))
        page_count = len(page_info)

        # Return True if more than 50% of pages have fonts
        return pages_with_fonts > (page_count * threshold)

    def _check_font_resources_per_page(self, pdf_bytes: bytes) -> list[dict]:
        """
        Check each page for font resources - indicates searchable text
        """
        page_info = []

        pdf_stream = BytesIO(pdf_bytes)
        for page_num, page in enumerate(PDFPage.get_pages(pdf_stream)):
            page_data = {
                "page_number": page_num + 1,
                "has_fonts": False,
                "font_count": 0,
                "has_images": False,
                "resource_types": [],
            }

            if hasattr(page, "resources") and page.resources:
                resources = page.resources

                if "Font" in resources:
                    page_data["has_fonts"] = True
                    font_resource = resources["Font"]
                    try:
                        page_data["font_count"] = len(font_resource)  # type: ignore
                    except (TypeError, AttributeError):
                        page_data["font_count"] = 1

                if "XObject" in resources:
                    page_data["has_images"] = True

                page_data["resource_types"] = list(resources.keys())

            page_info.append(page_data)

        return page_info

    def analyze_character_quality(self, pdf_bytes: bytes) -> dict:
        char_stats = {
            "total_chars": 0,
            "font_variations": set(),
            "suspicious_patterns": 0,
            "ocr_artifacts": 0,
            "avg_char_size": 0,
            "size_variations": [],
        }

        pdf_stream = BytesIO(pdf_bytes)
        for page in PDFPage.get_pages(pdf_stream):
            self.interpreter.process_page(page)
            layout = self.device.get_result()

            for element in layout:
                if isinstance(element, LTTextBox):
                    for line in element:
                        for char in line:
                            if isinstance(char, LTChar):
                                char_stats["total_chars"] += 1

                                if self._is_ocr_artifact(char):
                                    char_stats["ocr_artifacts"] += 1

                                if self._is_suspicious_char(char):
                                    char_stats["suspicious_patterns"] += 1

        char_stats["ocr_quality_score"] = self._calculate_quality_score(char_stats)

        return char_stats

    def _is_ocr_artifact(self, char: LTChar) -> bool:
        if "hidden" in char.fontname.lower() or "ocr" in char.fontname.lower():
            return True

        char_text = char.get_text()
        if len(char_text) == 1:
            # Look for replacement characters or unusual Unicode
            if ord(char_text) > 65535 or char_text in ["�", "□", "▯"]:
                return True

        return False

    def _is_suspicious_char(self, char: LTChar) -> bool:
        char_text = char.get_text()

        # Single character that's not alphanumeric or common punctuation
        if len(char_text) == 1 and not (char_text.isalnum() or char_text in ".,!?;: "):
            return True

        # Very small font size (might indicate hidden text)
        if char.size < 1.0:
            return True

        return False

    def _calculate_quality_score(self, char_stats: dict) -> float:
        if char_stats["total_chars"] == 0:
            return 0.0

        score = 1.0

        # Penalize OCR artifacts
        artifact_ratio = char_stats["ocr_artifacts"] / char_stats["total_chars"]
        score -= artifact_ratio * 0.5

        # Penalize suspicious patterns
        suspicious_ratio = char_stats["suspicious_patterns"] / char_stats["total_chars"]
        score -= suspicious_ratio * 0.3

        return max(0.0, min(1.0, score))


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) != 2:
        print("Usage: python analysis.py <pdf_file_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).is_file():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    ocr_detector = PDFOCRLayerDetector()
    has_ocr = ocr_detector.has_ocr_text_layer(pdf_bytes)
    print(f"PDF has_ocr_text_layer: {has_ocr}")
    ocr_quality = ocr_detector.analyze_character_quality(pdf_bytes)
    print(f"PDF analyze_character_quality: {ocr_quality}")
