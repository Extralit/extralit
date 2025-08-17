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

import asyncio
import logging
from typing import Any, Optional

from extralit_server.contexts.ocr.rq_client import (
    cancel_job,
    enqueue_pdf_extraction,
    get_job_status,
    is_redis_available,
)

_LOGGER = logging.getLogger(__name__)


async def extract_pdf_text_sync(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[dict[str, Any]] = None,
    extraction_config: Optional[dict[str, Any]] = None,
    use_rq: bool = True,
    max_wait_time: int = 600,
) -> tuple[str, dict[str, Any]]:
    """
    Extract PDF text using direct RQ communication with extralit-hf-space worker.

    This function implements the correct flow:
    extralit-server → RQ (pdf_queue) → extralit-hf-space worker → extract_pdf_markdown_job
    """
    try:
        _LOGGER.info(f"Extracting text from PDF: {filename} using direct RQ")

        if not use_rq or not is_redis_available():
            raise Exception("RQ is not available and HTTP fallback is disabled for direct RQ flow")

        # Enqueue job directly to pdf_queue
        job_id = enqueue_pdf_extraction(
            pdf_bytes=pdf_bytes,
            filename=filename,
            analysis_metadata=analysis_metadata,
            extraction_config=extraction_config,
            job_timeout=max_wait_time,
        )

        # Poll for completion
        poll_interval = 2  # Start with 2 second intervals
        max_poll_interval = 10  # Cap at 10 seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            try:
                status_info = get_job_status(job_id)
                status = status_info.get("status")

                if status == "finished":
                    result = status_info.get("result", {})
                    if result.get("ok", False):
                        markdown = result.get("markdown", "")
                        metadata = result.get("metadata", {})
                        _LOGGER.info(f"Direct RQ extraction completed for {filename} in {elapsed_time}s")
                        return markdown, metadata
                    else:
                        error = result.get("error", "Unknown error")
                        raise Exception(f"Extraction job failed: {error}")

                elif status == "failed":
                    error = status_info.get("error", "Job failed without details")
                    raise Exception(f"Extraction job failed: {error}")

                elif status in ["queued", "started"]:
                    # Job is still processing, continue polling
                    # Gradually increase poll interval to reduce load
                    poll_interval = min(poll_interval * 1.2, max_poll_interval)
                    continue

                else:
                    _LOGGER.warning(f"Unknown job status for {job_id}: {status}")
                    continue

            except Exception as e:
                _LOGGER.error(f"Error checking job status for {job_id}: {e}")
                # Try to cancel the job before giving up
                cancel_job(job_id)
                raise

        # Timeout reached
        _LOGGER.error(f"Direct RQ extraction timed out for {filename} after {max_wait_time}s")
        cancel_job(job_id)
        raise Exception(f"PDF extraction timed out after {max_wait_time} seconds")

    except Exception as e:
        _LOGGER.error(f"Direct RQ text extraction failed for {filename}: {e}")
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
