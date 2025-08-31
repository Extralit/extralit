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

import pytest
from uuid import uuid4

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