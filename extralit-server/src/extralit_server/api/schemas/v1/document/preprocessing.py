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
    rotation_ran: bool = False
    error: str | None = None
    page_count: int | None = None
    processing_settings: dict | None = None

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """
        Override model_dump to sanitize output for S3 compatibility.
        Ensures all string values are ASCII-safe.
        """
        raw_dict = super().model_dump(**kwargs)
        return sanitize_dict_for_s3(raw_dict)
