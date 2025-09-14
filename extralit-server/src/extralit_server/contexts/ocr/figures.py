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

"""Figure detection and bounding box utilities for OCR processing."""

from typing import Any


def extract_figure_bboxes(marker_layout: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract figure bounding boxes from Marker layout detection results.

    Args:
        marker_layout: Dictionary containing Marker's layout detection results

    Returns:
        List of dictionaries containing figure bounding box information:
        - page: Page number (0-indexed)
        - bbox: Bounding box coordinates [x0, y0, x1, y1]
        - score: Confidence score (if available)
        - type: Element type ('figure')
    """
    figures = []

    # Input validation
    if not marker_layout or not isinstance(marker_layout, dict):
        return figures

    # Handle different possible Marker output formats
    pages_data = marker_layout.get("pages", [])
    if not pages_data and "blocks" in marker_layout:
        # Single page format
        pages_data = [marker_layout]

    # Validate pages data
    if not isinstance(pages_data, list):
        return figures

    for page_idx, page_data in enumerate(pages_data):
        # Validate page data structure
        if not isinstance(page_data, dict):
            continue

        page_number = page_data.get("page", page_idx)
        blocks = page_data.get("blocks", [])

        # Validate blocks structure
        if not isinstance(blocks, list):
            continue

        for block in blocks:
            # Validate block structure
            if not isinstance(block, dict):
                continue

            # Try different naming conventions for block type
            block_type = (
                block.get("type") or block.get("block_type") or block.get("category") or block.get("label") or ""
            ).lower()

            # Multiple patterns for figure detection (including Marker-specific types)
            if any(
                keyword in block_type
                for keyword in [
                    "figure",
                    "image",
                    "graphic",
                    "chart",
                    "diagram",
                    "plot",
                    "picture",
                    "picturegroup",
                    "figuregroup",
                    "figureblock",
                    "figure_block",
                    "imageblock",
                    "image_block",  #
                ]
            ):
                # Try different naming conventions for bounding box
                bbox = (
                    block.get("bbox")
                    or block.get("coordinates")
                    or block.get("bounding_box")
                    or block.get("rect")
                    or block.get("box")
                )

                # Additional fallback: try nested structure
                if not bbox and "geometry" in block:
                    bbox = block["geometry"].get("bbox") or block["geometry"].get("coordinates")

                # Validate bbox format with multiple possible formats
                valid_bbox = None
                if bbox:
                    if isinstance(bbox, list) and len(bbox) == 4:
                        # Standard [x1, y1, x2, y2] format
                        try:
                            valid_bbox = [float(x) for x in bbox]
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(bbox, dict):
                        # Object format like {x1, y1, x2, y2} or {left, top, right, bottom}
                        try:
                            if all(k in bbox for k in ["x1", "y1", "x2", "y2"]):
                                valid_bbox = [
                                    float(bbox["x1"]),
                                    float(bbox["y1"]),
                                    float(bbox["x2"]),
                                    float(bbox["y2"]),
                                ]
                            elif all(k in bbox for k in ["left", "top", "right", "bottom"]):
                                valid_bbox = [
                                    float(bbox["left"]),
                                    float(bbox["top"]),
                                    float(bbox["right"]),
                                    float(bbox["bottom"]),
                                ]
                        except (ValueError, TypeError, KeyError):
                            pass

                if valid_bbox:
                    # Try different naming conventions for caption/description
                    caption = (
                        block.get("caption")
                        or block.get("text")
                        or block.get("content")
                        or block.get("description")
                        or block.get("alt_text")
                        or ""
                    )

                    # Try different naming conventions for confidence score
                    score = (
                        block.get("score")
                        or block.get("confidence")
                        or block.get("probability")
                        or block.get("certainty")
                    )
                    figures.append(
                        {
                            "page": page_number,
                            "bbox": valid_bbox,
                            "score": score,
                            "type": "figure",
                            "caption": caption,
                            "metadata": {
                                "source": "marker",
                                "block_id": block.get("id") or block.get("block_id"),
                                "polygon": block.get("polygon") or block.get("shape"),
                                "original_type": block.get("type") or block.get("block_type"),
                            },
                        }
                    )

    return figures


def normalize_figure_bbox(bbox: list[float], page_width: float, page_height: float) -> list[float]:
    """
    Normalize bounding box coordinates to relative values (0-1 range).

    Args:
        bbox: Bounding box coordinates [x0, y0, x1, y1]
        page_width: Page width in points
        page_height: Page height in points

    Returns:
        Normalized bounding box coordinates [x0, y0, x1, y1]
    """
    if not bbox or len(bbox) != 4:
        return [0.0, 0.0, 0.0, 0.0]

    x0, y0, x1, y1 = bbox
    return [
        max(0.0, min(1.0, x0 / page_width)),
        max(0.0, min(1.0, y0 / page_height)),
        max(0.0, min(1.0, x1 / page_width)),
        max(0.0, min(1.0, y1 / page_height)),
    ]


def filter_figures_by_size(figures: list[dict[str, Any]], min_area: float = 0.001) -> list[dict[str, Any]]:
    """
    Filter figures by minimum area to remove noise/small artifacts.

    Args:
        figures: List of figure dictionaries with bbox information
        min_area: Minimum relative area threshold (0-1 range)

    Returns:
        Filtered list of figures
    """
    filtered = []
    for figure in figures:
        bbox = figure.get("bbox", [])
        if len(bbox) == 4:
            x0, y0, x1, y1 = bbox
            area = abs((x1 - x0) * (y1 - y0))
            if area >= min_area:
                filtered.append(figure)
    return filtered
