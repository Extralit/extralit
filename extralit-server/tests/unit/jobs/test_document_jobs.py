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

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.jobs.document_jobs import analysis_and_preprocess_job
from extralit_server.models.database import Document


class TestDocumentJobs:
    """Test suite for document job functions."""

    @patch("extralit_server.jobs.document_jobs.files")
    @patch("extralit_server.jobs.document_jobs.PDFPreprocessor")
    @patch("extralit_server.jobs.document_jobs.PDFAnalyzer")
    @patch("extralit_server.jobs.document_jobs.PDFOCRLayerDetector")
    @patch("extralit_server.jobs.document_jobs.AsyncSessionLocal")
    @patch("extralit_server.jobs.document_jobs.get_current_job")
    async def test_analysis_and_preprocess_job_success(
        self,
        mock_get_current_job,
        mock_session,
        mock_ocr_detector_class,
        mock_analyzer_class,
        mock_preprocessor_class,
        mock_files,
    ):
        """Test successful analysis and preprocess job."""
        # Setup test data
        document_id = uuid4()
        s3_url = f"/api/v1/file/test-workspace/documents/{document_id}/test.pdf"
        reference = "test_ref"
        workspace_name = "test-workspace"

        # Mock current job
        mock_job = MagicMock()
        mock_job.meta = {}
        mock_get_current_job.return_value = mock_job

        # Mock file operations
        mock_client = MagicMock()
        mock_files.get_s3_client = AsyncMock(return_value=mock_client)
        mock_files.download_file_content = AsyncMock(return_value=b"%PDF-1.5 test pdf content")
        mock_files.get_thumbnail_s3_object_path.return_value = f"thumbnails/{document_id}"
        mock_files.put_object = AsyncMock()

        # Mock OCR detector
        mock_ocr_detector = MagicMock()
        mock_ocr_detector.has_ocr_text_layer.return_value = True
        mock_ocr_detector.analyze_character_quality.return_value = {
            "ocr_quality_score": 0.8,
            "total_chars": 1000,
            "ocr_artifacts": 5,
            "suspicious_patterns": 2,
        }
        mock_ocr_detector_class.return_value = mock_ocr_detector

        # Mock PDF analyzer - now returns tuple (layout_analysis, thumbnail_data)
        mock_analyzer = MagicMock()
        layout_analysis = {
            "page_count": 1,
            "page_dimensions": {"width": 612, "height": 792},
            "layout_analysis": {"analysis_method": "single_page_default"},
        }
        thumbnail_data = b"mock_thumbnail_data"
        mock_analyzer.analyze_pdf_layout.return_value = (layout_analysis, thumbnail_data)
        mock_analyzer_class.return_value = mock_analyzer

        # Mock preprocessor
        mock_preprocessor = MagicMock()
        mock_processing_response = MagicMock()
        mock_processing_response.processed_data = b"%PDF-1.5 processed content"
        mock_processing_response.metadata.processing_time = 5.0
        mock_processing_response.metadata.model_dump.return_value = {"processing_time": 5.0}
        mock_preprocessor.preprocess.return_value = mock_processing_response
        mock_preprocessor_class.return_value = mock_preprocessor

        # Mock database session
        mock_db = MagicMock()
        mock_document = MagicMock()
        mock_document.metadata_ = None
        mock_db.get.return_value = mock_document
        mock_session.return_value.__enter__.return_value = mock_db

        # Execute job
        result = await analysis_and_preprocess_job(document_id, s3_url, reference, workspace_name)

        # Verify result structure
        assert "document_id" in result
        assert "analysis_result" in result
        assert "preprocessing_result" in result
        assert result["document_id"] == str(document_id)

        # Verify analysis result
        analysis_result = result["analysis_result"]
        assert analysis_result["has_ocr_text_layer"] is True
        assert analysis_result["ocr_quality_score"] == 0.8
        assert analysis_result["layout_analysis"] == layout_analysis
        assert analysis_result["thumbnail_generated"] is True

        # Verify preprocessing result
        preprocessing_result = result["preprocessing_result"]
        assert preprocessing_result["processing_time"] == 5.0

        # Verify file operations were called
        mock_files.download_file_content.assert_called_once()
        mock_files.put_object.assert_called()  # Called for both processed PDF and thumbnail

        # Verify analyzers were called correctly
        mock_ocr_detector.has_ocr_text_layer.assert_called_once()
        mock_ocr_detector.analyze_character_quality.assert_called_once()
        mock_analyzer.analyze_pdf_layout.assert_called_once()
        mock_preprocessor.preprocess.assert_called_once()

        # Verify database operations
        mock_db.get.assert_called_once_with(Document, document_id)
        mock_db.commit.assert_called_once()

    @patch("extralit_server.jobs.document_jobs.files")
    @patch("extralit_server.jobs.document_jobs.get_current_job")
    async def test_analysis_and_preprocess_job_no_client(self, mock_get_current_job, mock_files):
        """Test analysis and preprocess job when storage client is not available."""
        # Setup test data
        document_id = uuid4()
        s3_url = f"/api/v1/file/test-workspace/documents/{document_id}/test.pdf"
        reference = "test_ref"
        workspace_name = "test-workspace"

        # Mock current job
        mock_job = MagicMock()
        mock_job.meta = {}
        mock_get_current_job.return_value = mock_job

        # Mock file operations - no client available
        mock_files.get_s3_client = AsyncMock(return_value=None)

        # Execute job and expect exception
        with pytest.raises(TypeError, match="object NoneType can't be used in 'await' expression"):
            await analysis_and_preprocess_job(document_id, s3_url, reference, workspace_name)

        # Verify job meta was updated with error
        assert "error" in mock_job.meta

    @patch("extralit_server.jobs.document_jobs.files")
    @patch("extralit_server.jobs.document_jobs.PDFAnalyzer")
    @patch("extralit_server.jobs.document_jobs.PDFOCRLayerDetector")
    @patch("extralit_server.jobs.document_jobs.get_current_job")
    async def test_analysis_and_preprocess_job_no_thumbnail(
        self, mock_get_current_job, mock_ocr_detector_class, mock_analyzer_class, mock_files
    ):
        """Test analysis and preprocess job when thumbnail generation fails."""
        # Setup test data
        document_id = uuid4()
        s3_url = f"/api/v1/file/test-workspace/documents/{document_id}/test.pdf"
        reference = "test_ref"
        workspace_name = "test-workspace"

        # Mock current job
        mock_job = MagicMock()
        mock_job.meta = {}
        mock_get_current_job.return_value = mock_job

        # Mock file operations
        mock_client = MagicMock()
        mock_files.get_s3_client = AsyncMock(return_value=mock_client)
        mock_files.download_file_content = AsyncMock(return_value=b"%PDF-1.5 test pdf content")
        mock_files.put_object = AsyncMock()

        # Mock OCR detector
        mock_ocr_detector = MagicMock()
        mock_ocr_detector.has_ocr_text_layer.return_value = False
        mock_ocr_detector.analyze_character_quality.return_value = {
            "ocr_quality_score": 0.3,
            "total_chars": 500,
            "ocr_artifacts": 50,
            "suspicious_patterns": 20,
        }
        mock_ocr_detector_class.return_value = mock_ocr_detector

        # Mock PDF analyzer - returns no thumbnail data
        mock_analyzer = MagicMock()
        layout_analysis = {
            "page_count": 1,
            "page_dimensions": {"width": 612, "height": 792},
            "layout_analysis": {"analysis_method": "single_page_default"},
        }
        mock_analyzer.analyze_pdf_layout.return_value = (layout_analysis, None)  # No thumbnail
        mock_analyzer_class.return_value = mock_analyzer

        # Mock preprocessor to skip it for this test by raising exception early
        with patch("extralit_server.jobs.document_jobs.PDFPreprocessor") as mock_preprocessor_class:
            mock_preprocessor = MagicMock()
            mock_processing_response = MagicMock()
            mock_processing_response.processed_data = b"%PDF-1.5 processed content"
            mock_processing_response.metadata.processing_time = 3.0
            mock_processing_response.metadata.model_dump.return_value = {"processing_time": 3.0}
            mock_preprocessor.preprocess.return_value = mock_processing_response
            mock_preprocessor_class.return_value = mock_preprocessor

            # Mock database
            with patch("extralit_server.jobs.document_jobs.AsyncSessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_document = MagicMock()
                mock_document.metadata_ = None
                mock_db.get.return_value = mock_document
                mock_session.return_value.__enter__.return_value = mock_db

                # Execute job
                result = await analysis_and_preprocess_job(document_id, s3_url, reference, workspace_name)

                # Verify that thumbnail was not generated
                analysis_result = result["analysis_result"]
                assert analysis_result["thumbnail_generated"] is False
                assert analysis_result["needs_ocr"] is True  # Low quality score and no OCR layer
