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
PDF extraction job orchestration for document processing pipeline.
"""

import logging
from typing import Any, Optional

from extralit_server.contexts.ocr.text import extract_pdf_text_async

_LOGGER = logging.getLogger(__name__)


async def extract_pdf_text_sync(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[dict[str, Any]] = None,
    extraction_config: Optional[dict[str, Any]] = None,
    use_rq: bool = True,
) -> tuple[str, dict[str, Any]]:
    """Synchronous wrapper for PDF text extraction."""
    try:
        _LOGGER.info(f"Extracting text from PDF: {filename}")

        markdown_text, metadata = await extract_pdf_text_async(
            pdf_bytes=pdf_bytes,
            filename=filename,
            analysis_metadata=analysis_metadata,
            extraction_config=extraction_config,
            use_rq=use_rq,
        )

        _LOGGER.info(f"Text extraction completed for {filename} ({len(markdown_text)} characters)")
        return markdown_text, metadata

    except Exception as e:
        _LOGGER.error(f"Text extraction failed for {filename}: {e}")
        raise


def should_extract_text(filename: str, file_metadata: dict[str, Any]) -> bool:
    """Determine if text extraction should be performed for a file."""
    if not filename.lower().endswith(".pdf"):
        return False

    if file_metadata.get("text_extracted", False):
        return False

    file_size = file_metadata.get("file_size_bytes", 0)
    max_size = 100 * 1024 * 1024  # 100MB default limit
    if file_size > max_size:
        _LOGGER.warning(f"Skipping text extraction for {filename}: file too large ({file_size} bytes)")
        return False

    return True


def create_extraction_config(
    analysis_metadata: Optional[dict[str, Any]] = None, custom_config: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Create extraction configuration based on analysis metadata."""
    config = {}

    if analysis_metadata:
        if "margins" in analysis_metadata:
            margins = analysis_metadata["margins"]
            if isinstance(margins, dict) and all(k in margins for k in ["left", "top", "right", "bottom"]):
                config["margins"] = (margins["left"], margins["top"], margins["right"], margins["bottom"])

        if analysis_metadata.get("has_headers"):
            config["header_detection_max_levels"] = 6
        else:
            config["header_detection_max_levels"] = 3

    if custom_config:
        config.update(custom_config)

    return config
