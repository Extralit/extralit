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
HTTP client for communicating with extralit-hf-space PyMuPDF extraction service.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple
from io import BytesIO

import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings


_LOGGER = logging.getLogger(__name__)


class HfSpaceSettings(BaseSettings):
    """Settings for extralit-hf-space integration."""
    
    # URL of the extralit-hf-space service
    hf_space_url: str = "http://localhost:7860"
    
    # Timeout for HTTP requests (in seconds)
    request_timeout: float = 300.0  # 5 minutes for large PDFs
    
    # Whether to enable hf-space integration
    enabled: bool = True
    
    class Config:
        env_prefix = "HF_SPACE_"


class PyMuPDFExtractionResult(BaseModel):
    """Result from PyMuPDF extraction service."""
    
    markdown: str
    metadata: Dict[str, Any]
    filename: Optional[str] = None
    processing_time: Optional[float] = None


class HfSpaceClient:
    """HTTP client for extralit-hf-space PyMuPDF extraction service."""
    
    def __init__(self, settings: Optional[HfSpaceSettings] = None):
        self.settings = settings or HfSpaceSettings()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.request_timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def extract_pdf_markdown(
        self,
        pdf_bytes: bytes,
        filename: str,
        analysis_metadata: Optional[Dict[str, Any]] = None
    ) -> PyMuPDFExtractionResult:
        """
        Extract markdown from PDF using the hf-space PyMuPDF service.
        
        Args:
            pdf_bytes: Raw PDF bytes
            filename: Original filename for the PDF
            analysis_metadata: Optional metadata from preprocessing/analysis
            
        Returns:
            PyMuPDFExtractionResult with extracted markdown and metadata
            
        Raises:
            httpx.HTTPError: If HTTP request fails
            ValueError: If extraction fails or returns invalid data
        """
        if not self.settings.enabled:
            raise ValueError("HF Space integration is disabled")
        
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Prepare form data
        files = {
            "pdf": (filename, BytesIO(pdf_bytes), "application/pdf")
        }
        
        data = {}
        if analysis_metadata:
            data["analysis_metadata"] = json.dumps(analysis_metadata)
        
        extract_url = f"{self.settings.hf_space_url.rstrip('/')}/extract"
        
        _LOGGER.info(f"Sending PDF extraction request to {extract_url} for file: {filename}")
        
        try:
            response = await self._client.post(
                extract_url,
                files=files,
                data=data
            )
            response.raise_for_status()
            
            result_data = response.json()
            
            # Validate required fields
            if "markdown" not in result_data:
                raise ValueError("Missing 'markdown' field in response")
            if "metadata" not in result_data:
                raise ValueError("Missing 'metadata' field in response")
            
            return PyMuPDFExtractionResult(**result_data)
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error from hf-space: {e.response.text}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg) from e
            
        except httpx.RequestError as e:
            error_msg = f"Request error to hf-space: {str(e)}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg) from e
    
    async def health_check(self) -> bool:
        """
        Check if the hf-space service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        if not self.settings.enabled:
            return False
            
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            health_url = f"{self.settings.hf_space_url.rstrip('/')}/healthz"
            response = await self._client.get(health_url, timeout=10.0)
            response.raise_for_status()
            
            health_data = response.json()
            return health_data.get("status") == "ok"
            
        except Exception as e:
            _LOGGER.warning(f"HF Space health check failed: {str(e)}")
            return False


# Global settings instance
hf_space_settings = HfSpaceSettings()


async def extract_pdf_with_pymupdf(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[Dict[str, Any]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function to extract PDF markdown using hf-space service.
    
    Args:
        pdf_bytes: Raw PDF bytes
        filename: Original filename
        analysis_metadata: Optional preprocessing metadata
        
    Returns:
        Tuple of (markdown_text, metadata_dict)
        
    Raises:
        ValueError: If extraction fails or service is unavailable
    """
    async with HfSpaceClient(hf_space_settings) as client:
        result = await client.extract_pdf_markdown(pdf_bytes, filename, analysis_metadata)
        return result.markdown, result.metadata
