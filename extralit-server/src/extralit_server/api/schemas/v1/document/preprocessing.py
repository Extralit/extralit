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

import unicodedata
from typing import Any

from pydantic import BaseModel


def sanitize_dict_for_s3(data: Any) -> Any:
    """
    Recursively sanitize dictionary values to ensure they're compatible with S3 storage.
    S3 metadata only supports US-ASCII characters.

    Args:
        data: Data to sanitize (dict, list, string, or other types)

    Returns:
        Sanitized data with ASCII-safe string values
    """
    if isinstance(data, str):
        # Normalize Unicode and convert to ASCII, replacing non-ASCII with closest equivalents
        normalized = unicodedata.normalize("NFKD", data)
        return normalized.encode("ascii", "ignore").decode("ascii")
    elif isinstance(data, dict):
        # Recursively sanitize nested dictionaries
        return {key: sanitize_dict_for_s3(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Sanitize list items
        return [sanitize_dict_for_s3(item) for item in data]
    else:
        # Keep non-string values as-is
        return data


class PDFMetadata(BaseModel):
    """
    Metadata for PDF processing results.
    """

    filename: str
    processing_time: float
    page_count: int | None = None
    language_detected: list[str] | None = None
    processing_settings: dict | None = None
    analysis_results: dict | None = None

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """
        Override model_dump to sanitize output for S3 compatibility.
        Ensures all string values are ASCII-safe.
        """
        raw_dict = super().model_dump(**kwargs)
        return sanitize_dict_for_s3(raw_dict)
