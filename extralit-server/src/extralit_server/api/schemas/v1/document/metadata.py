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

from typing import Any, Optional

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
    thumbnail_generated: Optional[bool] = Field(
        None, description="Whether a thumbnail was generated during layout analysis"
    )


class PreprocessingMetadata(BaseModel):
    """Preprocessing job results stored in documents.metadata_."""

    processing_time: float = Field(..., description="Processing time in seconds")
    ocr_applied: bool = Field(..., description="Whether OCR was applied during preprocessing")
    processed_s3_url: Optional[str] = Field(None, description="S3 URL of processed PDF")


class ChunkMetadata(BaseModel):
    """A single text chunk produced by the chunker."""

    text: str = Field(..., description="Chunk text content")
    start_index: int = Field(..., description="Character start offset in source text")
    end_index: int = Field(..., description="Character end offset in source text")
    token_count: int = Field(..., description="Number of tokens in the chunk")


class TextExtractionMetadata(BaseModel):
    """Text extraction job results."""

    markdown: str = Field(None, description="Extracted text")
    extraction_method: str = Field(..., description="Method used for extraction")
    chunks: Optional[list[ChunkMetadata]] = Field(None, description="Text chunks for embedding / retrieval")


class DocumentProcessingMetadata(BaseModel):
    """Complete document processing metadata stored in documents.metadata_."""

    workflow_id: Optional[str] = Field(None, description="Workflow ID for tracking")
    analysis_metadata: Optional[AnalysisMetadata] = Field(None, description="Analysis results")
    preprocessing_metadata: Optional[PreprocessingMetadata] = Field(None, description="Preprocessing results")
    text_extraction_metadata: Optional[TextExtractionMetadata] = Field(None, description="Text extraction results")
    workflow_status: str = Field(default="running", description="Overall workflow status")

    def update_analysis_results(self, analysis_result: dict) -> None:
        """Update analysis metadata from job result."""
        layout_data = analysis_result.get("layout_analysis", {})

        # Extract margin analysis from layout_analysis if it exists
        margin_analysis = {}
        if "layout_analysis" in layout_data:
            # The margin data is in layout_data["layout_analysis"]["estimated_margins"]
            nested_layout = layout_data["layout_analysis"]
            margin_analysis = nested_layout.get("estimated_margins", {})
        elif "estimated_margins" in layout_data:
            margin_analysis = layout_data["estimated_margins"]

        self.analysis_metadata = AnalysisMetadata(
            thumbnail_generated=analysis_result.get("thumbnail_generated"),
            has_ocr_text_layer=analysis_result.get("has_ocr_text_layer"),
            needs_ocr=analysis_result.get("needs_ocr"),
            ocr_quality=OCRQualityMetadata(**analysis_result.get("analysis_metadata", {})),
            layout_analysis=LayoutAnalysisMetadata(
                page_count=layout_data.get("page_count"),
                margin_analysis=margin_analysis,
                **{
                    k: v
                    for k, v in layout_data.items()
                    if k not in ["layout_analysis", "estimated_margins", "page_count"]
                },
            ),
        )

    def update_preprocessing_results(self, preprocess_result: dict) -> None:
        """Update preprocessing metadata from job result."""
        self.preprocessing_metadata = PreprocessingMetadata(
            processing_time=preprocess_result["processing_time"],
            ocr_applied=preprocess_result.get("ocr_applied", False),
            processed_s3_url=preprocess_result.get("processed_s3_url"),
        )

    def update_text_extraction_results(
        self, text: str, chunks: list[dict], extraction_method: str = "external_ocr"
    ) -> None:
        """Update text extraction metadata including chunks."""
        self.text_extraction_metadata = TextExtractionMetadata(
            markdown=text,
            extraction_method=extraction_method,
            chunks=[ChunkMetadata(**c) for c in chunks],
        )

    def is_workflow_complete(self) -> bool:
        """Check if all workflow steps are complete."""
        return all(
            [
                self.analysis_metadata is not None,
                self.preprocessing_metadata is not None,
                self.text_extraction_metadata is not None,
            ]
        )
