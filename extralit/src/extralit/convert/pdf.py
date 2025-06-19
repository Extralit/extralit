import os
from pathlib import Path
from typing import Optional

from PIL import Image

from extralit.preprocessing.segment import Coordinates


def extract_image(
    pdf_page: Image, coordinates: Coordinates, title: str, output_dir: Path, pad=20, redo=False
) -> Optional[str]:
    if not coordinates or not coordinates.points:
        return None

    # Create output directory if it doesn't exist
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Define output path
    if not title.endswith('.png'):
        title += '.png'
    image_path = os.path.join(output_dir, title)
    if os.path.exists(image_path) and not redo:
        return image_path

    # Get page dimensions
    page_width, page_height = pdf_page.size

    # Normalize coordinates
    if coordinates.layout_width:
        x_coords = [coordinates.points[i][0] * page_width / coordinates.layout_width for i in range(4)]
    else:
        x_coords = [coordinates.points[i][0] for i in range(4)]

    if coordinates.layout_height:
        y_coords = [coordinates.points[i][1] * page_height / coordinates.layout_height for i in range(4)]
    else:
        y_coords = [coordinates.points[i][1] for i in range(4)]

    x1, x2 = min(x_coords), max(x_coords)
    y1, y2 = min(y_coords), max(y_coords)

    # Add padding to the coordinates
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(page_width, x2 + pad)
    y2 = min(page_height, y2 + pad)

    padded_coords = (x1, y1, x2, y2)

    # Crop the image
    cropped_image = pdf_page.crop(padded_coords)

    # Save the image if it doesn't exist
    cropped_image.save(image_path)

    return image_path
