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

"""Text block detection and bounding box utilities for OCR processing."""

from typing import Any


def extract_text_bboxes(marker_layout: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract text block bounding boxes from Marker layout detection results.

    Args:
        marker_layout: Dictionary containing Marker's layout detection results

    Returns:
        List of dictionaries containing text bounding box information:
        - page: Page number (0-indexed)
        - bbox: Bounding box coordinates [x0, y0, x1, y1]
        - score: Confidence score (if available)
        - type: Element type ('text')
        - content: Text content (if available)
    """
    text_blocks = []

    # Handle different possible Marker output formats
    pages_data = marker_layout.get("pages", [])
    if not pages_data and "blocks" in marker_layout:
        # Single page format
        pages_data = [marker_layout]

    for page_idx, page_data in enumerate(pages_data):
        page_number = page_data.get("page", page_idx)
        blocks = page_data.get("blocks", [])

        for block in blocks:
            block_type = block.get("type") or block.get("block_type")
            if block_type and block_type.lower() in [
                "text",
                "paragraph",
                "heading",
                "title",
                "sectionheader",
                "textinlinemath",
                "listitem",
                "line",
                "span",
            ]:
                bbox = block.get("bbox") or block.get("coordinates")
                if bbox and len(bbox) == 4:
                    text_blocks.append(
                        {
                            "page": page_number,
                            "bbox": bbox,
                            "score": block.get("score") or block.get("confidence"),
                            "type": "text",
                            "subtype": block_type,
                            "content": block.get("text") or block.get("content", ""),
                            "metadata": {
                                "source": "marker",
                                "block_id": block.get("id"),
                                "polygon": block.get("polygon"),
                            },
                        }
                    )

    return text_blocks


def normalize_text_bbox(bbox: list[float], page_width: float, page_height: float) -> list[float]:
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
