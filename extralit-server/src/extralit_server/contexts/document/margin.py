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

import logging
import os
from typing import TYPE_CHECKING

import lazy_loader as lazy

os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_INTEL_MFX"] = "0"

try:
    cv2 = lazy.load("cv2")
    np = lazy.load("numpy")
except Exception as e:
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.warning(f"OpenCV not available or failed to load: {e}")

pdf2image = lazy.load("pdf2image")
PIL = lazy.load("PIL")

if TYPE_CHECKING:
    from numpy import ndarray as NDArray
    from PIL.Image import Image

_LOGGER = logging.getLogger(__name__)


def pil_to_cv(image: "Image") -> "NDArray":
    """Convert PIL Image to OpenCV format."""
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)  # type: ignore


def classify_and_draw_layout_regions(
    reference: "Image", mask: "Image", min_area: int = 5000, label: bool = True
) -> tuple["Image", list[dict]]:
    """
    Classify and optionally draw layout regions using contour detection.

    Returns:
        Tuple of (annotated image, list of detected regions)
    """

    mask_np = np.array(mask.convert("L"))  # type: ignore
    h, w = mask_np.shape

    # Clean up the mask using morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # type: ignore
    cleaned = cv2.morphologyEx(mask_np, cv2.MORPH_CLOSE, kernel)  # type: ignore

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # type: ignore

    img = reference.copy() if label else reference
    regions = []

    if label:
        draw = PIL.ImageDraw.Draw(img)  # type: ignore

    for cnt in contours:
        x, y, rw, rh = cv2.boundingRect(cnt)  # type: ignore
        area = rw * rh

        if area < min_area:
            continue

        cx, cy = x + rw // 2, y + rh // 2

        # Classify region based on position
        if cy < h * 0.25:
            region = "header"
        elif cy > h * 0.75:
            region = "footer"
        elif cx < w * 0.15:
            region = "left_margin"
        elif cx > w * 0.85:
            region = "right_margin"
        else:
            region = "body"

        region_data = {
            "type": region,
            "x": x,
            "y": y,
            "width": rw,
            "height": rh,
            "area": area,
            "center_x": cx,
            "center_y": cy,
        }
        regions.append(region_data)

        if label:
            draw.rectangle([x, y, x + rw, y + rh], outline="green", width=2)
            draw.text((x, y - 10), region, fill="green")

    return img, regions


def find_horizontal_bands(mask: "Image", min_height: int = 15, min_ratio: float = 0.95) -> list[tuple[int, int]]:
    """Find horizontal bands of similar content across pages."""
    mask_np: NDArray = np.array(mask.convert("L"))  # type: ignore
    h, w = mask_np.shape

    row_sums: NDArray = np.sum(mask_np == 255, axis=1) / w  # type: ignore
    same_rows: NDArray = row_sums >= min_ratio

    bands = []
    start = None
    for i, val in enumerate(same_rows):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start >= min_height:
                bands.append((start, i))
            start = None
    if start is not None and h - start >= min_height:
        bands.append((start, h))

    return bands


class PDFAnalyzer:
    def analyze_pdf_layout(self, pdf_data: bytes, filename: str) -> dict:
        """
        Analyze PDF layout to extract margin and region information.

        Args:
            pdf_data: PDF file data as bytes
            filename: Filename for logging

        Returns:
            Dictionary containing layout analysis metadata
        """

        try:
            images = pdf2image.convert_from_bytes(pdf_data, dpi=150)  # type: ignore
            if not images:
                return {"error": "No pages found"}

            _LOGGER.info(f"Analyzing layout for {filename} with {len(images)} pages")

            # Analyze layout
            layout_data = self._analyze_page_layout(images)

            return {
                "page_count": len(images),
                "page_dimensions": {"width": images[0].size[0], "height": images[0].size[1]} if images else {},
                **layout_data,
            }

        except Exception as e:
            _LOGGER.error(f"PDF layout analysis failed for {filename}: {e}")
            return {"error": str(e)}

    def _analyze_page_layout(self, images: list["Image"]) -> dict:
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

    def _compare_pages_for_margins(self, reference: "Image", compare: "Image") -> dict | None:
        """
        Compare two pages to identify common regions using advanced CV2 techniques.
        """
        try:
            # Ensure same size
            if reference.size != compare.size:
                _LOGGER.debug("Resizing page to match reference size")
                compare = compare.resize(reference.size)

            # Step 1: Compute difference and invert so white = same
            diff = PIL.ImageChops.difference(reference, compare)  # type: ignore
            sameness_mask = PIL.ImageChops.invert(diff.convert("L"))  # type: ignore

            # Step 2: Threshold the mask (keep high-sameness pixels)
            # Create a lookup table for thresholding
            threshold = 30
            lut = [255 if i > threshold else 0 for i in range(256)]
            sameness_mask.point(lut).convert("1")

            # Step 3: Find horizontal bands (potential headers/footers)
            horizontal_bands = find_horizontal_bands(sameness_mask)

            # Step 4: Use contour-based region classification
            annotated_img, detected_regions = classify_and_draw_layout_regions(
                reference, sameness_mask, min_area=5000, label=False
            )

            # Step 5: Classify and aggregate results
            regions = self._classify_regions_advanced(horizontal_bands, detected_regions, reference.size)

            return regions

        except Exception as e:
            _LOGGER.debug(f"Page comparison failed: {e}")
            return None

    def _classify_regions_advanced(
        self, bands: list[tuple[int, int]], detected_regions: list[dict], page_size: tuple[int, int]
    ) -> dict:
        """
        Advanced region classification combining horizontal bands and contour detection.
        """
        width, height = page_size
        regions = {
            "header_bands": [],
            "footer_bands": [],
            "detected_regions": detected_regions,
            "estimated_margins": {},
        }

        # Process horizontal bands
        for start_y, end_y in bands:
            band_center = (start_y + end_y) / 2
            band_height = end_y - start_y

            # Classify based on position
            if band_center < height * 0.25:  # Top 25%
                regions["header_bands"].append({"start_y": start_y, "end_y": end_y, "height": band_height})
            elif band_center > height * 0.75:  # Bottom 25%
                regions["footer_bands"].append({"start_y": start_y, "end_y": end_y, "height": band_height})

        # Estimate margins using both techniques
        regions["estimated_margins"] = self._estimate_margins_advanced(regions, detected_regions, page_size)

        return regions

    def _estimate_margins_advanced(
        self, regions: dict, detected_regions: list[dict], page_size: tuple[int, int]
    ) -> dict:
        """
        Advanced margin estimation using both band and contour information.
        """
        width, height = page_size
        margins = {
            "top": 0,
            "bottom": 0,
            "left": 50,  # Default estimates
            "right": 50,
        }

        # Calculate top margin from header regions
        header_sources = []
        if regions["header_bands"]:
            header_sources.append(max(band["end_y"] for band in regions["header_bands"]))

        # Add header regions from contour detection
        header_regions = [r for r in detected_regions if r["type"] == "header"]
        if header_regions:
            header_sources.append(max(r["y"] + r["height"] for r in header_regions))

        if header_sources:
            margins["top"] = max(header_sources)

        # Calculate bottom margin from footer regions
        footer_sources = []
        if regions["footer_bands"]:
            footer_sources.append(min(band["start_y"] for band in regions["footer_bands"]))

        # Add footer regions from contour detection
        footer_regions = [r for r in detected_regions if r["type"] == "footer"]
        if footer_regions:
            footer_sources.append(min(r["y"] for r in footer_regions))

        if footer_sources:
            margins["bottom"] = height - min(footer_sources)

        # Calculate left/right margins from contour detection
        left_regions = [r for r in detected_regions if r["type"] == "left_margin"]
        if left_regions:
            margins["left"] = max(r["x"] + r["width"] for r in left_regions)

        right_regions = [r for r in detected_regions if r["type"] == "right_margin"]
        if right_regions:
            margins["right"] = width - min(r["x"] for r in right_regions)

        # Convert to relative percentages for consistency
        return {
            "top_px": margins["top"],
            "bottom_px": margins["bottom"],
            "left_px": margins["left"],
            "right_px": margins["right"],
            "top_percent": (margins["top"] / height) * 100 if height > 0 else 0,
            "bottom_percent": (margins["bottom"] / height) * 100 if height > 0 else 0,
            "left_percent": (margins["left"] / width) * 100 if width > 0 else 0,
            "right_percent": (margins["right"] / width) * 100 if width > 0 else 0,
        }

    def _classify_regions(self, bands: list[tuple[int, int]], page_size: tuple[int, int]) -> dict:
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

    def _estimate_margins_from_bands(self, regions: dict, page_size: tuple[int, int]) -> dict:
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

    def _aggregate_margin_data(self, margin_data: list[dict], page_size: tuple[int, int]) -> dict:
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

        # Collect all bands and regions
        all_header_bands = []
        all_footer_bands = []
        all_detected_regions = []

        for data in margin_data:
            all_header_bands.extend(data.get("header_bands", []))
            all_footer_bands.extend(data.get("footer_bands", []))
            all_detected_regions.extend(data.get("detected_regions", []))

        # Aggregate detected regions by type
        region_stats = {}
        for region in all_detected_regions:
            region_type = region["type"]
            if region_type not in region_stats:
                region_stats[region_type] = []
            region_stats[region_type].append(region)

        return {
            "layout_analysis": {
                "header_bands": all_header_bands,
                "footer_bands": all_footer_bands,
                "detected_regions": all_detected_regions,
                "region_statistics": {
                    region_type: {
                        "count": len(regions),
                        "avg_area": sum(r["area"] for r in regions) / len(regions) if regions else 0,
                        "total_area": sum(r["area"] for r in regions),
                    }
                    for region_type, regions in region_stats.items()
                },
                "estimated_margins": avg_margins,
                "analysis_method": "multi_page_comparison_advanced",
            }
        }

    def _analyze_single_page(self, image: "Image") -> dict:
        """
        Analyze a single page when comparison isn't possible.
        """
        return self._analyze_single_page_size(image.size)

    def _analyze_single_page_size(self, page_size: tuple[int, int]) -> dict:
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
