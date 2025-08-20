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
PDF text extraction using PyMuPDF service with RQ integration.

This module provides PDF text extraction functionality with both RQ-based
asynchronous processing and HTTP fallback for reliability. It follows the
senior developer approach of simple, reusable functions with comprehensive
error handling and fallback mechanisms.
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

_LOGGER = logging.getLogger(__name__)


async def extract_pdf_text_async(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[dict[str, Any]] = None,
    extraction_config: Optional[dict[str, Any]] = None,
    use_rq: bool = True,
) -> tuple[str, dict[str, Any]]:
    """
    Extract hierarchical markdown text from PDF using PyMuPDF service.

    This function provides the main interface for PDF text extraction with
    automatic fallback between RQ and HTTP methods based on availability.

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Original filename of the PDF
        analysis_metadata: Optional metadata from document preprocessing
        extraction_config: Optional extraction configuration overrides
        use_rq: Whether to prefer RQ-based processing (default: True)

    Returns:
        Tuple of (markdown_text, metadata_dict)

    Raises:
        Exception: If both RQ and HTTP methods fail
    """
    if not pdf_bytes:
        raise ValueError("Empty PDF content provided")

    if not filename:
        filename = "document.pdf"

    # Determine processing method
    should_use_rq = use_rq and PYMUPDF_RQ_ENABLED and is_redis_available()

    if should_use_rq:
        try:
            _LOGGER.info(f"Using RQ-based extraction for {filename}")
            return await _extract_via_rq(pdf_bytes, filename, analysis_metadata, extraction_config)
        except Exception as e:
            _LOGGER.warning(f"RQ extraction failed for {filename}: {e}")
            if PYMUPDF_RQ_FALLBACK_HTTP:
                _LOGGER.info(f"Falling back to HTTP extraction for {filename}")
                return await _extract_via_http(pdf_bytes, filename, analysis_metadata, extraction_config)
            else:
                raise
    else:
        _LOGGER.info(f"Using HTTP extraction for {filename}")
        return await _extract_via_http(pdf_bytes, filename, analysis_metadata, extraction_config)


async def _extract_via_rq(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[dict[str, Any]] = None,
    extraction_config: Optional[dict[str, Any]] = None,
    max_wait_time: int = 600,
) -> tuple[str, dict[str, Any]]:
    """
    Extract PDF text using RQ background job processing.

    This function enqueues a job and waits for completion with polling.
    It's designed to be simple and reliable with proper timeout handling.

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Original filename of the PDF
        analysis_metadata: Optional metadata from document preprocessing
        extraction_config: Optional extraction configuration overrides
        max_wait_time: Maximum time to wait for job completion in seconds

    Returns:
        Tuple of (markdown_text, metadata_dict)

    Raises:
        Exception: If job fails or times out
    """
    # Enqueue the job
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
                    _LOGGER.info(f"RQ extraction completed for {filename} in {elapsed_time}s")
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
    _LOGGER.error(f"RQ extraction timed out for {filename} after {max_wait_time}s")
    cancel_job(job_id)
    raise Exception(f"PDF extraction timed out after {max_wait_time} seconds")


async def _extract_via_http(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[dict[str, Any]] = None,
    extraction_config: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any]]:
    """
    Extract PDF text using direct HTTP call to PyMuPDF service.

    This function provides the HTTP fallback when RQ is unavailable.
    It's designed to be simple and reliable with proper error handling.

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Original filename of the PDF
        analysis_metadata: Optional metadata from document preprocessing
        extraction_config: Optional extraction configuration overrides

    Returns:
        Tuple of (markdown_text, metadata_dict)

    Raises:
        Exception: If HTTP request fails
    """
    try:
        async with httpx.AsyncClient(timeout=PYMUPDF_REQUEST_TIMEOUT) as client:
            # Prepare form data
            files = {"pdf": (filename, pdf_bytes, "application/pdf")}
            data = {}

            if analysis_metadata:
                import json

                data["analysis_metadata"] = json.dumps(analysis_metadata)

            if extraction_config:
                import json

                data["extraction_config"] = json.dumps(extraction_config)

            # Make request to extraction endpoint
            response = await client.post(f"{PYMUPDF_SERVICE_URL}/extract", files=files, data=data)
            response.raise_for_status()

            result = response.json()

            # Extract markdown and metadata from response
            markdown = result.get("markdown", "")
            metadata = result.get("metadata", {})

            _LOGGER.info(f"HTTP extraction completed for {filename}")
            return markdown, metadata

    except httpx.TimeoutException:
        _LOGGER.error(f"HTTP extraction timed out for {filename}")
        raise Exception(f"PDF extraction request timed out after {PYMUPDF_REQUEST_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        _LOGGER.error(f"HTTP extraction failed for {filename}: {e.response.status_code} {e.response.text}")
        raise Exception(f"PDF extraction service error: {e.response.status_code}")
    except Exception as e:
        _LOGGER.error(f"HTTP extraction failed for {filename}: {e}")
        raise Exception(f"PDF extraction failed: {e}")


# Convenience function for backward compatibility
async def extract_pdf_text(
    pdf_bytes: bytes, filename: str, analysis_metadata: Optional[dict[str, Any]] = None
) -> tuple[str, dict[str, Any]]:
    """
    Simple wrapper for extract_pdf_text_async with default settings.

    This function provides backward compatibility and a simpler interface
    for basic PDF text extraction needs.

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Original filename of the PDF
        analysis_metadata: Optional metadata from document preprocessing

    Returns:
        Tuple of (markdown_text, metadata_dict)
    """
    return await extract_pdf_text_async(
        pdf_bytes=pdf_bytes, filename=filename, analysis_metadata=analysis_metadata, use_rq=True
    )
