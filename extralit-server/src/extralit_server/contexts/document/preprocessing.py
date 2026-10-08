"""Rotation-only ocrmypdf pass.

No OCR is produced here: `tesseract_timeout=0` kills the tesseract spawn, and `skip_text` leaves
text pages untouched. OSD (page orientation) is the one thing tesseract is still asked for, which
is why its budget is bounded. Margins and the thumbnail belong to the analysis job.
"""

import logging
import os
import tempfile
import time
from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

import lazy_loader as lazy
from pydantic import Field
from pydantic_settings import BaseSettings

from extralit_server.api.schemas.v1.document.preprocessing import PDFMetadata

ocrmypdf = lazy.load("ocrmypdf")

_LOGGER = logging.getLogger(__name__)


@dataclass
class PDFProcessingResponse:
    """
    Result of PDF preprocessing containing both processed data and analysis metadata.
    """

    processed_data: bytes
    metadata: PDFMetadata


class PDFPreprocessingSettings(BaseSettings):
    """
    PDF preprocessing settings, configurable via `PREPROCESSING_`-prefixed environment variables.
    """

    class Config:
        env_prefix = "PREPROCESSING_"

    enabled: bool = Field(default=True, description="Run ocrmypdf at all. False leaves the PDF byte-identical.")

    rotate_pages: bool = Field(default=True, description="Auto-rotate pages whose text is not upright")

    rotate_pages_threshold: float = Field(
        default=2.0, description="Confidence tesseract's OSD must reach before a page is rotated"
    )

    tesseract_non_ocr_timeout: float = Field(
        default=30.0,
        description="Per-page budget for OSD, the only tesseract call made here (ocrmypdf's own default is 180s)",
    )

    progress_bar: bool = Field(default=False, description="Show progress bar during processing")

    jobs: int = Field(
        default=1,
        description="Worker processes for ocrmypdf. 1 in containers with limited CPU, to avoid oversubscription.",
    )

    def get_ocrmypdf_args(self) -> dict:
        """Arguments for `ocrmypdf.ocr`, with everything OCR-shaped nailed shut.

        `clean` (unpaper) and `optimize` only pay off alongside OCR output, and rasterizing
        alternatives (`force_ocr`, `redo_ocr`) would destroy the text layer this pipeline relies on.
        """
        return {
            "rotate_pages": self.rotate_pages,
            "rotate_pages_threshold": self.rotate_pages_threshold,
            "skip_text": True,
            "tesseract_timeout": 0,
            "tesseract_non_ocr_timeout": self.tesseract_non_ocr_timeout,
            "clean": False,
            "optimize": 0,
            "progress_bar": self.progress_bar,
            "jobs": self.jobs,
        }


settings = PDFPreprocessingSettings()


class PDFPreprocessor:
    """Runs ocrmypdf over a PDF for page rotation only."""

    def __init__(self, settings: PDFPreprocessingSettings = settings):
        self.settings = settings

    def preprocess(self, file_data: bytes, filename: str) -> PDFProcessingResponse:
        """Rotate pages, best effort.

        Returns the original bytes with `rotation_ran=False` and the reason in `error` when
        ocrmypdf fails — a failed rotation must not cost the caller its document.
        """
        if not filename.lower().endswith(".pdf") or not self.settings.enabled:
            return PDFProcessingResponse(
                processed_data=file_data,
                metadata=PDFMetadata(filename=filename, processing_time=0.0),
            )

        start_time = time.time()
        processed_data, rotation_ran, error = file_data, False, None

        try:
            try:
                input_buffer = BytesIO(file_data)
                output_buffer = BytesIO()
                ocrmypdf.ocr(input_buffer, output_buffer, **self.settings.get_ocrmypdf_args())  # type: ignore
                processed_data = output_buffer.getvalue()
                output_buffer.close()
                input_buffer.close()
            except TypeError as buffer_error:
                # Some ocrmypdf paths insist on real files; a genuine failure re-raises below.
                _LOGGER.debug(f"BytesIO approach failed for {filename}, falling back to temp files: {buffer_error}")
                processed_data = self._preprocess_with_temp_files(file_data, filename)
            rotation_ran = True
        except Exception as e:
            _LOGGER.warning(f"Rotation failed for {filename}, keeping the original: {e}")
            processed_data, error = file_data, str(e)

        metadata = PDFMetadata(
            filename=filename,
            processing_time=time.time() - start_time,
            rotation_ran=rotation_ran,
            error=error,
        )
        return PDFProcessingResponse(processed_data=processed_data, metadata=metadata)

    def _preprocess_with_temp_files(self, file_data: bytes, filename: str) -> bytes:
        """
        Fallback implementation using unique temporary files to avoid concurrency issues.
        """
        input_temp_file = None
        output_temp_file = None

        try:
            unique_id = str(uuid4())
            temp_dir = tempfile.gettempdir()

            input_temp_file = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix=f"ocr_input_{unique_id}_", dir=temp_dir, delete=False
            )
            input_temp_file.write(file_data)
            input_temp_file.flush()
            input_temp_file.close()

            output_temp_file = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix=f"ocr_output_{unique_id}_", dir=temp_dir, delete=False
            )
            output_temp_file.close()

            ocrmypdf.ocr(input_temp_file.name, output_temp_file.name, **self.settings.get_ocrmypdf_args())  # type: ignore

            with open(output_temp_file.name, "rb") as f:
                processed_data = f.read()

            return processed_data

        finally:
            for temp_file in [input_temp_file, output_temp_file]:
                if temp_file is not None:
                    try:
                        if hasattr(temp_file, "name"):
                            os.unlink(temp_file.name)
                    except OSError as e:
                        _LOGGER.warning(f"Failed to clean up temp file: {e}")


preprocessor = PDFPreprocessor()
