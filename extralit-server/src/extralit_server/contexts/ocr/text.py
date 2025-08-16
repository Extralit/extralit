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
PyMuPDF text extraction client for communicating with extralit-hf-space service.

This module provides text extraction capabilities using PyMuPDF through a
microservice architecture, enabling hierarchical markdown extraction from PDFs.
"""

import json
import logging
from io import BytesIO
from typing import Any, Optional

import httpx
from pydantic_settings import BaseSettings

# Import centralized schemas - single source of truth
from extralit_server.api.schemas.v1.document.ocr import ExtractionResponse
from extralit_server.api.schemas.v1.document.preprocessing import PDFMetadata

_LOGGER = logging.getLogger(__name__)


class PyMuPDFServiceSettings(BaseSettings):
    """Configuration settings for PyMuPDF extraction service."""

    # URL of the extralit-hf-space service
    service_url: str = "http://localhost:7860"

    # Timeout for HTTP requests (in seconds)
    request_timeout: float = 300.0  # 5 minutes for large PDFs

    # Whether to enable PyMuPDF extraction integration
    enabled: bool = True

    class Config:
        env_prefix = "PYMUPDF_"


class PyMuPDFExtractionClient:
    """HTTP client for PyMuPDF text extraction service."""

    def __init__(self, settings: Optional[PyMuPDFServiceSettings] = None):
        self.settings = settings or PyMuPDFServiceSettings()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.request_timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def extract_markdown(
        self, pdf_bytes: bytes, filename: str, analysis_metadata: Optional[dict[str, Any]] = None
    ) -> ExtractionResponse:
        """
        Extract structured markdown from PDF using PyMuPDF service.

        Args:
            pdf_bytes: Raw PDF bytes
            filename: Original filename for the PDF
            analysis_metadata: Optional metadata from preprocessing/analysis

        Returns:
            ExtractionResponse with extracted markdown and metadata

        Raises:
            httpx.HTTPError: If HTTP request fails
            ValueError: If extraction fails or returns invalid data
        """
        if not self.settings.enabled:
            raise ValueError("PyMuPDF extraction service is disabled")

        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Prepare form data
        files = {"pdf": (filename, BytesIO(pdf_bytes), "application/pdf")}

        data = {}
        if analysis_metadata:
            if hasattr(analysis_metadata, "model_dump"):
                # If it's a Pydantic model, serialize it
                data["analysis_metadata"] = json.dumps(analysis_metadata.model_dump())
            else:
                # If it's already a dict, serialize it directly
                data["analysis_metadata"] = json.dumps(analysis_metadata)

        extract_url = f"{self.settings.service_url.rstrip('/')}/extract"

        _LOGGER.info(f"Extracting text from {filename} using PyMuPDF service at {extract_url}")

        try:
            response = await self._client.post(extract_url, files=files, data=data)
            response.raise_for_status()

            result_data = response.json()

            # Validate required fields
            if "markdown" not in result_data:
                raise ValueError("Missing 'markdown' field in response")
            if "metadata" not in result_data:
                raise ValueError("Missing 'metadata' field in response")

            # Convert metadata dict to PDFMetadata object
            metadata_dict = result_data["metadata"]
            pdf_metadata = PDFMetadata(**metadata_dict)

            return ExtractionResponse(
                markdown=result_data["markdown"],
                metadata=pdf_metadata,
                filename=result_data.get("filename"),
                processing_time=result_data.get("processing_time"),
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error from PyMuPDF service: {e.response.text}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg) from e

        except httpx.RequestError as e:
            error_msg = f"Request error to PyMuPDF service: {e!s}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg) from e

    async def health_check(self) -> bool:
        """
        Check if the PyMuPDF extraction service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        if not self.settings.enabled:
            return False

        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            health_url = f"{self.settings.service_url.rstrip('/')}/healthz"
            response = await self._client.get(health_url, timeout=10.0)
            response.raise_for_status()

            health_data = response.json()
            return health_data.get("status") == "ok"

        except Exception as e:
            _LOGGER.warning(f"PyMuPDF service health check failed: {e!s}")
            return False


# Global settings and client management for connection reuse
_service_settings = PyMuPDFServiceSettings()
_global_client: Optional[PyMuPDFExtractionClient] = None


async def get_extraction_client() -> PyMuPDFExtractionClient:
    """
    Get or create a global PyMuPDF extraction client for connection reuse.
    This improves performance by avoiding client initialization overhead.
    """
    global _global_client
    if _global_client is None:
        _global_client = PyMuPDFExtractionClient(_service_settings)
        await _global_client.__aenter__()
    elif _global_client._client is None:
        await _global_client.__aenter__()
    return _global_client


async def extract_pdf_text(
    pdf_bytes: bytes, filename: str, analysis_metadata: Optional[dict[str, Any]] = None
) -> tuple[str, dict[str, Any]]:
    """
    Extract structured text from PDF using PyMuPDF with connection reuse.

    Args:
        pdf_bytes: Raw PDF bytes
        filename: Original filename
        analysis_metadata: Optional preprocessing metadata

    Returns:
        Tuple of (markdown_text, metadata_dict)

    Raises:
        ValueError: If extraction fails or service is unavailable
    """
    try:
        client = await get_extraction_client()
        result = await client.extract_markdown(pdf_bytes, filename, analysis_metadata)
        return result.markdown, result.metadata
    except Exception as e:
        _LOGGER.error(f"PyMuPDF text extraction failed for {filename}: {e!s}")
        raise ValueError(f"PDF text extraction failed: {e!s}") from e


async def cleanup_extraction_client():
    """Clean up global extraction client resources. Call this on application shutdown."""
    global _global_client
    if _global_client is not None:
        await _global_client.__aexit__(None, None, None)
        _global_client = None


async def check_service_health() -> bool:
    """
    Check if the PyMuPDF extraction service is healthy.

    Returns:
        True if service is healthy, False otherwise
    """
    try:
        client = await get_extraction_client()
        return await client.health_check()
    except Exception as e:
        _LOGGER.warning(f"Service health check failed: {e!s}")
        return False


# Public API exports
__all__ = [
    "PyMuPDFExtractionClient",
    "PyMuPDFServiceSettings",
    "check_service_health",
    "cleanup_extraction_client",
    "extract_pdf_text",
]
