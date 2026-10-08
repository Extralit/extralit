import io
import logging
from typing import TYPE_CHECKING

import lazy_loader as lazy

pdf2image = lazy.load("pdf2image")
PIL = lazy.load("PIL")

if TYPE_CHECKING:
    from PIL.Image import Image

_LOGGER = logging.getLogger(__name__)


def generate_thumbnail_from_image(image: "Image", max_width: int = 200, max_height: int = 300) -> bytes:
    """
    Generate a thumbnail image from a PIL Image.

    Args:
        image: PIL Image object (typically from pdf2image conversion)
        max_width: Maximum width of the thumbnail in pixels
        max_height: Maximum height of the thumbnail in pixels

    Returns:
        Thumbnail image data as bytes (PNG format)

    Raises:
        Exception: If thumbnail generation fails
    """
    try:
        # Calculate thumbnail size maintaining aspect ratio
        original_width, original_height = image.size

        # Calculate scaling factor to fit within max dimensions
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        scale_factor = min(width_ratio, height_ratio)

        # Calculate new dimensions
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)

        # Create thumbnail
        thumbnail = image.resize((new_width, new_height), resample=PIL.Image.Resampling.LANCZOS)  # type: ignore

        # Convert to bytes in PNG format
        thumbnail_buffer = io.BytesIO()
        thumbnail.save(thumbnail_buffer, format="PNG", optimize=True)
        thumbnail_buffer.seek(0)

        _LOGGER.info(f"Generated thumbnail: {new_width}x{new_height} from {original_width}x{original_height}")

        return thumbnail_buffer.getvalue()

    except Exception as e:
        _LOGGER.error(f"Failed to generate thumbnail: {e}")
        raise Exception(f"Thumbnail generation failed: {e}")
