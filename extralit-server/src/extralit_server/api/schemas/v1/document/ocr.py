"""
OCR and text extraction related Pydantic schemas.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from .preprocessing import PDFMetadata


class ExtractionRequest(BaseModel):
    """
    Request schema for PDF extraction endpoint.
    
    This schema represents the metadata and configuration for PDF extraction.
    The actual PDF file is sent as a multipart upload.
    """
    
    file_url: Optional[str] = Field(
        None, 
        description="Optional URL to the PDF file if hosted externally"
    )
    analysis_metadata: Optional[PDFMetadata] = Field(
        None,
        description="Analysis and preprocessing metadata from extralit-server"
    )
    extraction_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom extraction configuration parameters"
    )


class ExtractionResponse(BaseModel):
    """
    Response schema for PDF extraction endpoint.
    """
    
    markdown: str = Field(..., description="Extracted markdown content")
    metadata: PDFMetadata = Field(..., description="Extraction and processing metadata")
    filename: Optional[str] = Field(None, description="Original filename of the PDF")
    processing_time: Optional[float] = Field(None, description="Time taken for extraction in seconds")


class PyMuPDFExtractionResult(BaseModel):
    """
    Result from PyMuPDF extraction service.
    """
    
    markdown: str
    metadata: Dict[str, Any]
    filename: Optional[str] = None
    processing_time: Optional[float] = None


class ErrorResponse(BaseModel):
    """
    Error response schema.
    """
    
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code for programmatic handling")


__all__ = [
    "ExtractionRequest",
    "ExtractionResponse", 
    "PyMuPDFExtractionResult",
    "ErrorResponse",
]
