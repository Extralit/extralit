import json
import logging
import os.path
import uuid
from typing import Optional, Any, List, Union, Dict

from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.program import MultiModalLLMCompletionProgram
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.schema import NodeRelationship, RelatedNodeType
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from pydantic.v1 import BaseModel, Field, validator

from extralit.convert.html_table import html_table_to_json, html_to_df, llmsherpa_html_to_df
from extralit.extraction import prompts
from extralit.preprocessing.figures import encode_image, FigureExtractionResponse
from extralit.preprocessing.tables import extract_table_number

CHUNK_DELIM = '\n\n---\n'


class Segments(BaseModel):
    items: List[Union['TextSegment', 'TableSegment', 'FigureSegment']] = Field(
        default_factory=list, description="List of segments")

    def get(self, id: str, header: str = None, default=None):
        for item in self.items:
            if item.id == id or (header and item.header == header):
                return item

        return default

    def make_headers_unique(self) -> None:
        header_dict = {}

        for segment in self.items:
            if segment.header in header_dict:
                parent = segment.relationships.get(NodeRelationship.PARENT)
                if parent:
                    parent_segment = self.get(parent.node_id)
                    if parent_segment:
                        segment.header = f"{parent_segment.header}: {segment.header}"
                        print(segment.id, segment.header)
            else:
                header_dict[segment.header] = segment

    def __repr_str__(self, join_str: str) -> str:
        return '\n  ' + f'{join_str}\n  '.join(f'{type(item).__name__}({item})' for item in self.items)

    @validator('items', pre=True, each_item=True)
    def parse_segments(cls, v):
        if not isinstance(v, dict):
            v = v.dict()

        segment_type = v.get('type', '').lower()
        if segment_type in {'figure', 'image'}:
            return FigureSegment(**v)
        elif segment_type == 'table' or 'html' in v:
            return TableSegment(**v)
        else:
            return TextSegment(**v)

    @classmethod
    def from_pdffigures2(cls, json_file: str) -> 'Segments':
        with open(json_file, 'r') as f:
            data = json.load(f)

        items = []
        for item in data:
            mapped_item = {
                'header': item['caption'],
                'type': item['figType'].lower(),
                'text': ' '.join(item['imageText']),
                'image': item['renderURL'],
                'page_number': item['page'] + 1,
                'coordinates': {
                    'points': [[item['regionBoundary']['x1'], item['regionBoundary']['y1']],
                               [item['regionBoundary']['x2'], item['regionBoundary']['y1']],
                               [item['regionBoundary']['x1'], item['regionBoundary']['y2']],
                               [item['regionBoundary']['x2'], item['regionBoundary']['y2']]],
                    'layout_width': item['regionBoundary']['x2'] - item['regionBoundary']['x1'],
                    'layout_height': item['regionBoundary']['y2'] - item['regionBoundary']['y1'],
                    'system': 'points'
                },
                'source': 'pdffigures2',
            }
            items.append(cls.parse_segments(mapped_item))

        items = sorted(
            items, key=lambda x: (x.page_number, x.number or float('inf')))

        return cls(items=items)

    @property
    def duration(self):
        return sum([item.duration or 0 for item in self.items if item.duration and item.duration < 1000])

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)


class Coordinates(BaseModel):
    points: List[List[float]] = Field(...,
                                      description="List of 4 points, e.g. [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]")
    layout_width: Optional[int] = Field(None, description="Width of the layout")
    layout_height: Optional[int] = Field(None, description="Height of the layout")
    system: Optional[str] = Field(description="System of coordinates")

    def __repr_str__(self, join_str: str) -> str:
        return ''

    def is_vstacked(self, other: 'Coordinates', width: Optional[str] = 'same', tol=0.05) -> Optional[bool]:
        if not self.points or not other.points:
            return None

        if self.layout_width and self.layout_width == other.layout_width:
            tolerance = self.layout_width * tol  # 1% of the layout width
        else:
            tolerance = 10  # pixels

        # Get the x-coordinates of the current bounding box
        x1_self = self.points[0][0]
        x2_self = self.points[1][0]

        # Get the x-coordinates of the other bounding box
        x1_other = other.points[0][0]
        x2_other = other.points[1][0]

        # Check if the x-coordinates of the two bounding boxes are approximately equal
        if width == 'smaller':
            return abs(x1_self - x1_other) <= tolerance and (x2_self + tolerance) > x2_other
        elif width == 'larger':
            return abs(x1_self - x1_other) <= tolerance and (x2_self + tolerance) <= x2_other
        elif width == 'same':
            return abs(x1_self - x1_other) <= tolerance and abs(x2_self - x2_other) <= tolerance
        else:
            return abs(x1_self - x1_other) <= tolerance


class TextSegment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier of the segment",
                    repr=False)

    header: Optional[str] = Field(None, description="Header of the element", example="Abstract")
    text: str = Field(..., description="Content as plain text", repr=False)
    summary: Optional[str] = Field(None, description="Summary of the content")
    page_number: Optional[int] = Field(None, description="Page number of the segment")
    coordinates: Optional['Coordinates'] = Field(None, description="Coordinates of the element in the document",
                                                 repr=False)
    level: Optional[int] = Field(None, description="Level of the header")
    relationships: Dict[NodeRelationship, RelatedNodeType] = Field(
        default_factory=dict,
        description="A mapping of relationships to other segments.",
    )
    source: Optional[str] = Field(None, description="Source of the element", example="llmsherpa", repr=False)
    type: Optional[str] = Field('text', description="Type of the element", example="text", repr=False)
    original: Optional[Any] = Field(None, exclude=True,
                                    description="Original object from which the segment was extracted", repr=False)
    duration: Optional[float] = Field(None, description="Duration spent in manual extraction", repr=False)

    def text_cleaned(self):
        return self.text.replace(' | ', ' ').replace("---", "").strip()

    def __repr_str__(self, join_str: str) -> str:
        return join_str.join(repr(v) if a is None else (
            f'{a}="{v[:100]}...{v[-100:]}"'.replace('\n', '') if isinstance(v, str) and len(v) > 200 else f'{a}={v!r}') \
                             for a, v in self.__repr_args__() \
                             if v and a not in {'INCLUDE_METADATA_KEYS'})


class TableSegment(TextSegment):
    footer: Optional[str] = Field(None, description="Footer of the table or figure, to explain variable acronyms.")
    html: Optional[str] = Field(None, description="Content as HTML structured", repr=False)
    image: Optional[str] = Field(None, description="URL/filepath of the element's image", repr=False)
    probability: Optional[float] = Field(None, description="Probability or confidence of the segment's extraction")
    type: Optional[str] = Field('table', description="Type of the element", repr=False)

    @property
    def number(self) -> Optional[int]:
        return extract_table_number(self.header)

    def __repr_args__(self):
        args = super().__repr_args__()
        args.append(('number', self.number))
        return args

    def to_df(self, **kwargs):
        if self.source == 'llmsherpa':
            df = llmsherpa_html_to_df(self.html)
        else:
            df = html_to_df(self.html, **kwargs)

        return df

    def to_csv(self):
        df = self.to_df()
        csv = df.to_csv(index=bool(df.index.name) or len(df.index.names) > 1)
        return csv

    def to_json(self) -> str:
        json = None
        try:
            if self.source == 'llmsherpa':
                df = llmsherpa_html_to_df(self.html)
                json = df.to_json(orient='table',
                                  index=bool(df.index.name) or len(df.index.names) > 1)

            else:
                json = html_table_to_json(self.html)
        except Exception as e:
            logging.warning(f'{e}, {self.type}, {self.html}')

        return json


class FigureSegment(TableSegment):
    type: Optional[str] = Field('figure', description="Type of the element", repr=False)

    @property
    def number(self) -> Optional[int]:
        return extract_table_number(self.header, pattern=r"(?i)(fig\.?|figure)[.:\s]*([Il|\d]+)", group=2)

    def extract_html_table(self) -> Optional[FigureExtractionResponse]:
        if not os.path.exists(self.image): return None

        try:
            encode_image(self.image, resize_only=True)
        except Exception as e:
            logging.warning(f'Failed to encode image: {e}')
            return None

        openai_mm_llm = OpenAIMultiModal(
            model="gpt-4o",
            temperature=0.0,
            max_new_tokens=2048,
            image_detail="low",
            max_retries=1,
        )

        llm_program = MultiModalLLMCompletionProgram.from_defaults(
            image_documents=SimpleDirectoryReader(input_files=[self.image]).load_data(),
            output_parser=PydanticOutputParser(FigureExtractionResponse),
            prompt=prompts.FIGURE_TABLE_EXT_PROMPT_TMPL,
            multi_modal_llm=openai_mm_llm,
        )

        try:
            logging.info(f'Extracting figure table: {self.header}')
            response: FigureExtractionResponse = llm_program(header_str=self.header)
            self.html = response.html
            if response.summary:
                self.summary = response.summary
        except Exception as e:
            logging.warning(f'{e}')
            return None

        return response


TextSegment.update_forward_refs()
Segments.update_forward_refs()
Coordinates.update_forward_refs()
