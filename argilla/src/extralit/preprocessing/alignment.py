import copy
import difflib
import os
from collections import Counter
from typing import List, Optional, Tuple, Union, Dict, Any

import argilla as rg
import pandas as pd
from pydantic.v1 import BaseModel, Field, validator
from rapidfuzz import fuzz
from unstructured.documents.elements import Element, Header, FigureCaption, Image, \
    Footer, Table as UnstructuredTable

from extralit.convert.text import find_longest_superstrings
from extralit.preprocessing.segment import TextSegment, TableSegment, CHUNK_DELIM, FigureSegment, Segments
from extralit.preprocessing.tables import SAMPLE_HTML_TABLE


class Alignments(BaseModel):
    items: List['SegmentsAlignment'] = Field(default_factory=list, description="List of SegmentsAlignment objects")

    def to_records(self, dataset: rg.Dataset, fill_missing_tables=False, **kwargs) -> List[rg.Record]:
        records = [item.to_record(dataset=dataset, **kwargs) for item in self.items]
        records = [record for record in records if record is not None]

        if fill_missing_tables:
            self.insert_missing_tables(records, **kwargs)

        return records

    def insert_missing_tables(self, records: List[rg.Record], **kwargs):
        captured_numbers = [item.number for item in self.items if item.number]
        numbers_count = Counter(captured_numbers)
        max_number = max([item.number for item in self.items if item.number], default=0)

        for number in range(1, max_number + 1):
            if number in captured_numbers: continue
            # Check that the previous number is not duplicated
            if number > 1 and numbers_count.get(number - 1, 1e6) > 1: continue

            metadata = copy.deepcopy(kwargs.get('metadata', {}))
            metadata['number'] = f"Table {number}"
            fields = {
                'header': f'This table #{number} was not detected',
                'metadata': pd.DataFrame.from_dict(metadata, orient='index').T.to_markdown(index=False),
            }

            suggestions = []
            suggestion_data = copy.deepcopy(kwargs.get('suggestions', []))
            for sug in suggestion_data:
                suggestions.append(
                    rg.Suggestion(
                        question_name=sug["question_name"],
                        value=sug["value"]
                    )
                )
            suggestions.extend([
                rg.Suggestion("header-correction", f"Table {number}"),
                rg.Suggestion("text-correction", SAMPLE_HTML_TABLE),
            ])

            missing_record = rg.Record(
                fields=fields,
                suggestions=suggestions,
                metadata=metadata
            )
            records.insert(number - 1, missing_record)

    def __repr_str__(self, join_str: str) -> str:
        return f"\n  " + f"{join_str}\n  ".join(f'{type(item).__name__}({item})' for item in self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)


class SegmentsAlignment(BaseModel):
    header: str = Field(..., description="Header of the element", example="Abstract")
    type: str = Field(..., description="Type of the element", example="text")
    page_number: int = Field(..., example=1)
    summary: Optional[str] = Field(..., description="Summary of the content", example="Summary")
    number: Optional[int] = Field(None, description="Number of the table/figure", example=1)
    extractions: Dict[str, Any] = Field(default_factory=dict, description="Extractions from different sources")
    image: Optional[str] = Field(None)
    probability: Optional[float] = Field(None, description="Probability of the detection algorithm")

    @validator('extractions', each_item=True, pre=True)
    def check_segment_types(cls, segment: Union[FigureSegment, TableSegment]):
        return segment

    def __getitem__(self, key):
        return self.extractions[key]

    def __repr_str__(self, join_str: str) -> str:
        extractions_str = f"{join_str}\n\t" + f"{join_str}\n\t".join(
            f'"{k}"={type(v).__name__}({v})' for k, v in self.extractions.items())
        return f'page_number={self.page_number}, number={self.number}, extractions={{ {extractions_str} }}'

    def to_record(
            self,
            dataset: rg.Dataset,
            fields: Optional[Dict[str, str]] = None,
            suggestions: Optional[List[Dict[str, str]]] = None,
            metadata: Optional[Dict[str, str]] = None,
            **kwargs) -> Optional[rg.Record]:

        fields: Dict[str, str] = {
            **(fields or {})
        }
        if isinstance(self.header, str):
            fields["header"] = self.header.strip()
        else:
            fields["header"] = ''

        if self.summary:
            fields['header'] += f'{CHUNK_DELIM}{self.summary}'

        record_suggestions = []
        if suggestions:
            for sug in suggestions:
                record_suggestions.append(
                    rg.Suggestion(
                        question_name=sug["question_name"],
                        value=sug["value"]
                    )
                )

        if self.type.lower() == 'text':
            pass

        elif self.type.lower() in ['table', 'figure']:
            for source, segment in self.extractions.items():
                if segment.summary:
                    fields['header'] += f'{CHUNK_DELIM}{segment.summary}'

                if segment.html:
                    if source == 'nougat':
                        fields["text-1"] = segment.html
                    elif source == 'unstructured':
                        fields["text-2"] = segment.html
                    elif source == 'llmsherpa':
                        fields["text-3"] = segment.html
                    elif source == 'deepdoctection':
                        fields["text-4"] = segment.html
                    elif source == 'pdffigures2':
                        fields["text-5"] = segment.html

            if isinstance(self.image, str) and os.path.exists(self.image):
                fields["image"] = self.image  # v2 handles image paths directly

        else:
            print('Skipped', self.type, metadata, self.extractions.keys())

        # Metadata
        metadata = copy.deepcopy(metadata) or {}
        metadata['type'] = f'{self.type}'
        if self.number:
            metadata['number'] = f'{self.type} {self.number}'
        if self.probability:
            metadata['probability'] = self.probability
        if self.page_number:
            metadata['page_number'] = str(self.page_number)

        if 'metadata' in dataset.fields and not fields.get('metadata'):
            fields['metadata'] = pd.DataFrame.from_dict(metadata, orient='index').T.to_markdown(index=False)

        record = rg.Record(
            fields=fields,
            metadata=metadata,
            suggestions=record_suggestions,
            **kwargs
        )

        return record


Alignments.update_forward_refs()
SegmentsAlignment.update_forward_refs()

# Rest of the file remains unchanged
