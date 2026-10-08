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


class TriageMetadata(BaseModel):
    """Structural classification of the PDF, from pdf-inspector's page objects.

    `pages_needing_ocr` fires on any image-bearing page under ~1400 characters, so figure-heavy
    papers are false positives. Good enough to gate rotation and to surface the OCR gap; nothing
    is skipped on the strength of it.
    """

    pdf_type: str = Field(..., description="text_based, image_based, mixed or unknown")
    confidence: float = Field(default=0.0, description="Classifier confidence, 0.0-1.0")
    page_count: int = Field(default=0, description="Number of pages")
    pages_needing_ocr: list[int] = Field(default_factory=list, description="1-indexed pages with no usable text")
    ocr_reasons_by_page: dict[str, list[str]] = Field(
        default_factory=dict, description="Why each of those pages was flagged, keyed by page number"
    )
    pages_with_tables: list[int] = Field(default_factory=list, description="1-indexed pages carrying tables")
    pages_with_columns: list[int] = Field(default_factory=list, description="1-indexed multi-column pages")
    has_encoding_issues: bool = Field(default=False, description="Whether text decodes to mojibake")


class AnalysisMetadata(BaseModel):
    """Analysis job results stored in documents.metadata_."""

    triage: Optional[TriageMetadata] = Field(None, description="Structural classification of the PDF")
    has_ocr_text_layer: Optional[bool] = Field(None, description="Deprecated, no longer written")
    needs_ocr: Optional[bool] = Field(None, description="Deprecated, no longer written")
    ocr_quality: Optional[OCRQualityMetadata] = Field(None, description="Deprecated, no longer written")
    layout_analysis: LayoutAnalysisMetadata = Field(..., description="Layout analysis results")
    thumbnail_generated: Optional[bool] = Field(
        None, description="Whether a thumbnail was generated during layout analysis"
    )


class PreprocessingMetadata(BaseModel):
    """Preprocessing job results stored in documents.metadata_."""

    processing_time: float = Field(..., description="Processing time in seconds")
    ocr_applied: bool = Field(..., description="Whether OCR was applied during preprocessing")
    processed_s3_url: Optional[str] = Field(None, description="S3 URL of processed PDF")
    rotation_ran: Optional[bool] = Field(None, description="Whether page rotation completed")
    error: Optional[str] = Field(None, description="Why preprocessing fell back to the original PDF")


class TextExtractionMetadata(BaseModel):
    """Text extraction job results."""

    markdown: str = Field(None, description="Extracted text")
    extraction_method: str = Field(..., description="Method used for extraction")


class LayoutMetadata(BaseModel):
    """Layout extraction job results.

    Only pointers and counts — the layout itself lives in object storage, because
    `documents.metadata_` is returned in full by every `GET /documents` listing.
    """

    layout_url: str = Field(..., description="S3 object path of the canonical DoclingDocument JSON")
    items_uri: Optional[str] = Field(None, description="Lance dataset holding this workspace's layout items")
    pages_uri: Optional[str] = Field(None, description="Lance dataset holding this workspace's page geometry")
    items_version: Optional[int] = Field(None, description="Items dataset version after this document was written")
    pages_version: Optional[int] = Field(None, description="Pages dataset version after this document was written")
    parser: str = Field(..., description="Name of the layout parser that produced the document")
    docling_version: str = Field(..., description="docling-core schema version the JSON was written with")
    num_items: int = Field(default=0, description="Number of layout items extracted")
    num_pages: int = Field(default=0, description="Number of pages with registered geometry")
    pages_needing_ocr: list[int] = Field(
        default_factory=list, description="1-indexed pages with no reliable text layer"
    )


class DocumentProcessingMetadata(BaseModel):
    """Complete document processing metadata stored in documents.metadata_."""

    workflow_id: Optional[str] = Field(None, description="Workflow ID for tracking")
    analysis_metadata: Optional[AnalysisMetadata] = Field(None, description="Analysis results")
    preprocessing_metadata: Optional[PreprocessingMetadata] = Field(None, description="Preprocessing results")
    text_extraction_metadata: Optional[TextExtractionMetadata] = Field(None, description="Text extraction results")
    layout_metadata: Optional[LayoutMetadata] = Field(None, description="Layout extraction results")
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

        triage = analysis_result.get("triage")
        self.analysis_metadata = AnalysisMetadata(
            thumbnail_generated=analysis_result.get("thumbnail_generated"),
            triage=TriageMetadata(**triage) if isinstance(triage, dict) else triage,
            layout_analysis=LayoutAnalysisMetadata(
                page_count=analysis_result.get("page_count") or layout_data.get("page_count"),
                has_tables=bool(triage.get("pages_with_tables")) if isinstance(triage, dict) else False,
                margin_analysis=margin_analysis,
                **{
                    k: v
                    for k, v in layout_data.items()
                    if k not in ["layout_analysis", "estimated_margins", "page_count", "pages_sampled", "has_tables"]
                },
            ),
        )

    def update_preprocessing_results(self, preprocess_result: dict) -> None:
        """Update preprocessing metadata from job result."""
        self.preprocessing_metadata = PreprocessingMetadata(
            processing_time=preprocess_result["processing_time"],
            ocr_applied=preprocess_result.get("ocr_applied", False),
            processed_s3_url=preprocess_result.get("processed_s3_url"),
            rotation_ran=preprocess_result.get("rotation_ran"),
            error=preprocess_result.get("error"),
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
