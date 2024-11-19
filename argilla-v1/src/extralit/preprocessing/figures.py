import base64
import io
import logging
from typing import Optional

from PIL import Image
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from extralit.extraction.staging import heal_json


class FigureExtractionResponse(BaseModel):
    """ Figure digitization and summary of scientific chart or figure. """
    summary: str = Field(
        None, description="Summary of the figure, detailing the variables visualized and the observations compared.")
    html: str = Field(
        None,
        description="HTML table of data extracted from the chart with the same structure as the original figure, "
                    "with exact data values omitted. If the provided image is a map or a picture, this field will be empty.")

    def __init__(self, **data):
        super().__init__(**data)
        if 'html' in data:
            self.html = clean_html_table(data['html'])

    @classmethod
    def parse_raw(cls, b, **kwargs):
        healed_json_string = heal_json(b)
        try:
            output = super().parse_raw(healed_json_string, **kwargs)
        except Exception as e:
            logging.error(f'Error parsing {cls.__name__}: {e}\n'
                          f'Given: "{healed_json_string}"')
            return cls(items=[])

        return output


def encode_image(image_path: str, max_size=(1000, 1000), resize_only=True) -> Optional[str]:
    # Open an image file
    with Image.open(image_path) as img:
        original_size = img.size
        img.thumbnail(max_size)
        new_size = img.size

        if resize_only:
            if original_size != new_size:
                img.save(image_path)
        else:
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='PNG')

            return base64.b64encode(byte_arr).decode("utf-8")


def clean_html_table(html_string: str) -> Optional[str]:
    if not html_string:
        return None

    try:
        # Parse the HTML
        soup = BeautifulSoup(html_string, 'html.parser')

        # Find the first table in the HTML
        table = soup.find('table')

        # If a table was found
        if table is not None:
            caption = table.find('caption')
            if caption is not None:
                caption.decompose()

        # If a table was found, return its HTML as a string
        if table is not None:
            return str(table)
        else:
            return None
    except:
        return None
