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

"""Document processing metadata schemas for workflow tracking."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OCRQualityMetadata(BaseModel):
    """OCR quality analysis metadata."""

    total_chars: int = Field(..., description="Total characters analyzed")
    ocr_artifacts: int = Field(..., description="Number of OCR artifacts detected")
    suspicious_patterns: int = Field(..., description="Number of suspicious patterns found")
    ocr_quality_score: float = Field(..., description="Overall OCR quality score (0.0-1.0)")


class LayoutAnalysisMetadata(BaseModel):
    """PDF layout analysis metadata."""

    page_count: int = Field(None, description="Number of pages in PDF")
    has_tables: bool = Field(default=False, description="Whether tables were detected")
    has_figures: bool = Field(default=False, description="Whether figures were detected")
    text_regions: int = Field(default=0, description="Number of text regions detected")
    margin_analysis: dict[str, Any] = Field(default_factory=dict, description="Margin analysis results")


class AnalysisMetadata(BaseModel):
    """Analysis job results stored in documents.metadata_."""

    has_ocr_text_layer: Optional[bool] = Field(None, description="Whether PDF has OCR text layer")
    needs_ocr: Optional[bool] = Field(None, description="Whether additional OCR processing is needed")
    ocr_quality: OCRQualityMetadata = Field(..., description="OCR quality analysis")
    layout_analysis: LayoutAnalysisMetadata = Field(..., description="Layout analysis results")
    analysis_completed_at: datetime = Field(..., description="When analysis was completed")


class PreprocessingMetadata(BaseModel):
    """Preprocessing job results stored in documents.metadata_."""

    processing_time: float = Field(..., description="Processing time in seconds")
    ocr_applied: bool = Field(..., description="Whether OCR was applied during preprocessing")
    processed_s3_url: Optional[str] = Field(None, description="S3 URL of processed PDF")
    preprocessing_completed_at: datetime = Field(..., description="When preprocessing was completed")


class TextExtractionMetadata(BaseModel):
    """Text extraction job results."""

    extracted_text_length: int = Field(..., description="Length of extracted text")
    extraction_method: str = Field(..., description="Method used for extraction")
    text_extraction_completed_at: datetime = Field(..., description="When text extraction was completed")


class TableExtractionMetadata(BaseModel):
    """Table extraction job results."""

    tables_found: int = Field(..., description="Number of tables extracted")
    extraction_method: str = Field(..., description="Method used for table extraction")
    table_extraction_completed_at: datetime = Field(..., description="When table extraction was completed")


class EmbeddingMetadata(BaseModel):
    """Embedding job results."""

    embedding_model: str = Field(..., description="Model used for embeddings")
    embedding_dimensions: int = Field(..., description="Dimensionality of embeddings")
    embedding_completed_at: datetime = Field(..., description="When embedding was completed")


class DocumentProcessingMetadata(BaseModel):
    """Complete document processing metadata stored in documents.metadata_."""

    workflow_id: Optional[str] = Field(None, description="Workflow ID for tracking")
    analysis_metadata: Optional[AnalysisMetadata] = Field(None, description="Analysis results")
    preprocessing_metadata: Optional[PreprocessingMetadata] = Field(None, description="Preprocessing results")
    text_extraction_metadata: Optional[TextExtractionMetadata] = Field(None, description="Text extraction results")
    table_extraction_metadata: Optional[TableExtractionMetadata] = Field(None, description="Table extraction results")
    embedding_metadata: Optional[EmbeddingMetadata] = Field(None, description="Embedding results")
    workflow_started_at: Optional[datetime] = Field(None, description="When workflow was started")
    workflow_completed_at: Optional[datetime] = Field(None, description="When workflow was completed")
    workflow_status: str = Field(default="running", description="Overall workflow status")

    def update_analysis_results(self, analysis_result: dict) -> None:
        """Update analysis metadata from job result."""
        self.analysis_metadata = AnalysisMetadata(
            has_ocr_text_layer=analysis_result.get("has_ocr_text_layer"),
            needs_ocr=analysis_result.get("needs_ocr"),
            ocr_quality=OCRQualityMetadata(**analysis_result.get("analysis_metadata", {})),
            layout_analysis=LayoutAnalysisMetadata(**analysis_result.get("layout_analysis", {})),
            analysis_completed_at=datetime.now(timezone.utc),
        )

    def update_preprocessing_results(self, preprocess_result: dict) -> None:
        """Update preprocessing metadata from job result."""
        self.preprocessing_metadata = PreprocessingMetadata(
            processing_time=preprocess_result["processing_time"],
            ocr_applied=preprocess_result.get("ocr_applied", False),
            processed_s3_url=preprocess_result.get("processed_s3_url"),
            preprocessing_completed_at=datetime.now(timezone.utc),
        )

    def is_workflow_complete(self) -> bool:
        """Check if all workflow steps are complete."""
        return all(
            [
                self.analysis_metadata is not None,
                self.preprocessing_metadata is not None,
                self.text_extraction_metadata is not None,
                self.table_extraction_metadata is not None,
                self.embedding_metadata is not None,
            ]
        )


# Job Input/Output Schemas for PDF Workflow


class AnalysisAndPreprocessJobInput(BaseModel):
    """Input schema for combined analysis and preprocessing job."""

    document_id: UUID = Field(..., description="Document ID to process")
    s3_url: str = Field(..., description="S3 URL of the PDF file")
    reference: str = Field(..., description="Document reference for tracking")
    workspace_id: UUID = Field(..., description="Workspace ID")


class AnalysisAndPreprocessJobOutput(BaseModel):
    """Output schema for combined analysis and preprocessing job."""

    document_id: UUID = Field(..., description="Document ID that was processed")
    analysis_result: dict[str, Any] = Field(..., description="Analysis results including OCR quality and layout")
    preprocessing_result: dict[str, Any] = Field(..., description="Preprocessing results including processing time")
    needs_ocr: bool = Field(..., description="Whether additional OCR processing is needed")
    processed_s3_url: str = Field(..., description="S3 URL of the processed PDF")
    processing_time: float = Field(..., description="Total processing time in seconds")
