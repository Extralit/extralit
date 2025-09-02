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

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from extralit_server.contexts.document.thumbnail import generate_thumbnail, generate_thumbnail_from_image
from extralit_server.contexts.files import get_thumbnail_s3_object_path


class TestThumbnailPaths:
    """Test thumbnail S3 path generation."""

    def test_get_thumbnail_s3_object_path_with_uuid(self):
        """Test thumbnail path generation with UUID."""
        doc_id = uuid4()
        path = get_thumbnail_s3_object_path(doc_id)
        assert path == f"thumbnails/{doc_id}"

    def test_get_thumbnail_s3_object_path_with_string(self):
        """Test thumbnail path generation with string."""
        doc_id = "test-document-id"
        path = get_thumbnail_s3_object_path(doc_id)
        assert path == "thumbnails/test-document-id"

    def test_get_thumbnail_s3_object_path_with_none_raises_exception(self):
        """Test that None ID raises exception."""
        with pytest.raises(Exception, match="id cannot be None"):
            get_thumbnail_s3_object_path(None)

    def test_get_thumbnail_s3_object_path_with_empty_string_raises_exception(self):
        """Test that empty string raises exception."""
        with pytest.raises(Exception, match="id cannot be None"):
            get_thumbnail_s3_object_path("")


class TestThumbnailGeneration:
    """Test thumbnail generation functionality."""

    @patch('extralit_server.contexts.document.thumbnail.pdf2image')
    def test_generate_thumbnail_success(self, mock_pdf2image):
        """Test successful thumbnail generation."""
        # Mock the pdf2image conversion
        mock_image = MagicMock()
        mock_image.size = (800, 1000)  # Original size
        mock_thumbnail = MagicMock()
        mock_image.resize.return_value = mock_thumbnail
        mock_thumbnail.save = MagicMock()
        
        mock_pdf2image.convert_from_bytes.return_value = [mock_image]
        mock_pdf2image.PIL.Image.LANCZOS = "LANCZOS"  # Mock the constant
        
        # Mock the save operation to return PNG bytes
        with patch('io.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = b'fake_png_data'
            mock_bytesio.return_value = mock_buffer
            
            result = generate_thumbnail(b'fake_pdf_data')
            
            # Verify the result
            assert result == b'fake_png_data'
            
            # Verify calls
            mock_pdf2image.convert_from_bytes.assert_called_once_with(
                b'fake_pdf_data', dpi=72, first_page=1, last_page=1
            )
            mock_image.resize.assert_called_once_with((200, 250), resample="LANCZOS")
            mock_thumbnail.save.assert_called_once()

    @patch('extralit_server.contexts.document.thumbnail.pdf2image')
    def test_generate_thumbnail_no_pages_raises_exception(self, mock_pdf2image):
        """Test that no pages raises exception."""
        mock_pdf2image.convert_from_bytes.return_value = []
        
        with pytest.raises(Exception, match="Thumbnail generation failed"):
            generate_thumbnail(b'fake_pdf_data')

    @patch('extralit_server.contexts.document.thumbnail.pdf2image')
    def test_generate_thumbnail_pdf2image_error_raises_exception(self, mock_pdf2image):
        """Test that pdf2image errors are handled."""
        mock_pdf2image.convert_from_bytes.side_effect = Exception("PDF conversion failed")
        
        with pytest.raises(Exception, match="Thumbnail generation failed"):
            generate_thumbnail(b'fake_pdf_data')


class TestThumbnailFromImage:
    """Test thumbnail generation from PIL Images."""

    @patch('extralit_server.contexts.document.thumbnail.pdf2image')
    def test_generate_thumbnail_from_image_success(self, mock_pdf2image):
        """Test successful thumbnail generation from PIL Image."""
        # Mock PIL Image
        mock_image = MagicMock()
        mock_image.size = (800, 1000)  # Original size
        mock_thumbnail = MagicMock()
        mock_image.resize.return_value = mock_thumbnail
        mock_thumbnail.save = MagicMock()
        
        mock_pdf2image.PIL.Image.LANCZOS = "LANCZOS"  # Mock the constant
        
        # Mock the save operation to return PNG bytes
        with patch('io.BytesIO') as mock_bytesio:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = b'fake_png_data'
            mock_bytesio.return_value = mock_buffer
            
            result = generate_thumbnail_from_image(mock_image)
            
            # Verify the result
            assert result == b'fake_png_data'
            
            # Verify calls
            mock_image.resize.assert_called_once_with((200, 250), resample="LANCZOS")
            mock_thumbnail.save.assert_called_once()

    @patch('extralit_server.contexts.document.thumbnail.pdf2image')
    def test_generate_thumbnail_from_image_resize_error_raises_exception(self, mock_pdf2image):
        """Test that image resize errors are handled."""
        mock_image = MagicMock()
        mock_image.size = (800, 1000)
        mock_image.resize.side_effect = Exception("Image resize failed")
        
        with pytest.raises(Exception, match="Thumbnail generation failed"):
            generate_thumbnail_from_image(mock_image)