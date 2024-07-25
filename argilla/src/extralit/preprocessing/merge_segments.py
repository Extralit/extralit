import copy
import difflib
import os
from collections import Counter
from typing import List, Optional, Tuple, Union, Dict, Any

import argilla as rg
import pandas as pd
from argilla.client.feedback.utils import image_to_html
from pydantic.v1 import BaseModel, Field, validator
from rapidfuzz import fuzz
from unstructured.documents.elements import Element, Header, FigureCaption, Image, \
    Footer, Table as UnstructuredTable

from extralit.convert.text import find_longest_superstrings
from extralit.preprocessing.segment import TextSegment, TableSegment, CHUNK_DELIM, FigureSegment, Segments
from extralit.preprocessing.tables import SAMPLE_HTML_TABLE


class Alignments(BaseModel):
    items: List['SegmentsAlignment'] = Field(default_factory=list, description="List of SegmentsAlignment objects")

    def to_records(self, dataset: rg.FeedbackDataset, fill_missing_tables=False, **kwargs) -> List[rg.FeedbackRecord]:
        records = [item.to_record(dataset=dataset, **kwargs) for item in self.items]
        records = [record for record in records if record is not None]

        if fill_missing_tables:
            self.insert_missing_tables(records, **kwargs)

        return records

    def insert_missing_tables(self, records: List[rg.FeedbackRecord], **kwargs):
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

            suggestions = copy.deepcopy(kwargs.get('suggestions', []))
            suggestions.extend([
                {"question_name": "header-correction", "value": f"Table {number}"},
                {"question_name": "text-correction", "value": SAMPLE_HTML_TABLE},
            ])
            missing_record = rg.FeedbackRecord(fields=fields, suggestions=suggestions, metadata=metadata)
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
            dataset: rg.FeedbackDataset,
            fields: Optional[Dict[str, str]] = None,
            suggestions: Optional[List[Dict[str, str]]] = None,
            metadata: Optional[Dict[str, str]] = None,
            **kwargs) -> Optional[rg.FeedbackRecord]:

        fields: Dict[str, str] = {
            **(fields or {})
        }
        if isinstance(self.header, str):
            fields["header"] = self.header.strip()
        else:
            fields["header"] = ''

        if self.summary:
            fields['header'] += f'{CHUNK_DELIM}{self.summary}'

        suggestions = copy.deepcopy(suggestions) or []

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
                fields["image"] = image_to_html(self.image)

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

        if dataset.field_by_name('metadata') and not fields.get('metadata'):
            fields['metadata'] = pd.DataFrame.from_dict(metadata, orient='index').T.to_markdown(index=False)

        record = rg.FeedbackRecord(fields=fields, metadata=metadata, **kwargs)

        return record


Alignments.update_forward_refs()
SegmentsAlignment.update_forward_refs()


def merge_extractions(**extraction_sources: Dict[str, Segments]) -> Alignments:
    extraction_sources = {source: segments for source, segments in extraction_sources.items() \
                          if segments is not None and len(segments)}
    pointers = {source: 0 for source in extraction_sources}
    merged_data = []

    while any(pointer < len(extraction_list) for pointer, extraction_list in
              zip(pointers.values(), extraction_sources.values())):
        current_items = []
        for source, segments in extraction_sources.items():
            index = pointers[source]
            if index < len(segments):
                current_item = segments[index]
                current_items.append((source, current_item))

        # groups_ordering = group_segments([segment for (source, segment) in current_items], threshold=30)
        # current_items = [(source, segment, number) for (source, segment), number in \
        #                  zip(current_items, groups_ordering)]

        # Sort by page number, then by table number, handling None values
        valid_items: List[Tuple[str, Union[TableSegment, FigureSegment]]] = sorted(
            current_items, key=lambda x: (x[1].page_number, x[1].number or float('inf')))
        if not valid_items: break

        current_page_number = valid_items[0][1].page_number
        filtered_items: List[Tuple[str, TextSegment]] = [(source, segment) for source, segment, *number in valid_items \
                                                         if segment.page_number == current_page_number]

        # Combine headers for unique values
        unique_headers = set(segment.header.strip() for (source, segment) in filtered_items if segment.header)
        combined_header = CHUNK_DELIM.join(find_longest_superstrings(unique_headers, similarity_threshold=90))
        summary = next((segment.summary for source, segment in filtered_items \
                        if getattr(segment, 'summary', None)), None)
        number = next((segment.number for source, segment in filtered_items \
                       if getattr(segment, 'number', None)), None)
        image = next((segment.image for source, segment in filtered_items \
                      if getattr(segment, 'image', None)), None)
        probabilities = [segment.probability for source, segment in filtered_items \
                         if getattr(segment, 'probability', None)]

        # Create SegmentsAlignment object
        segment_alignment = SegmentsAlignment(
            header=combined_header.strip(),
            summary=summary,
            page_number=current_page_number,
            number=number,
            extractions={source: segment for source, segment in filtered_items},
            image=image,
            type=filtered_items[0][1].type,
            probability=max(probabilities, default=None),
        )
        merged_data.append(segment_alignment)

        # Increment pointers for all sources that had the current header
        for source, _ in filtered_items:
            pointers[source] += 1

    return Alignments(items=merged_data)


def group_segments_by_similarity(segments: List[TextSegment], threshold=80.0) -> List[int]:
    if len(segments) == 1:
        return [0]

    groups = []
    for seg in segments:
        for group in groups:
            if max(fuzz.ratio(seg.text_cleaned(), group_item.text_cleaned()) for group_item in group) >= threshold:
                group.append(seg)
                break
        else:
            groups.append([seg])

    groups.sort(key=len, reverse=True)

    ordered_groups = []
    for seg in segments:
        for i, group in enumerate(groups):
            if seg in group:
                ordered_groups.append(i)
                break

    return ordered_groups


def find_matching_text_elem(text: str, elements: List[Element], page_number: int, start_index: Optional[int] = None,
                            thresh=0.5) -> List[int]:
    matches = []

    for i in range(start_index or 0, len(elements)):
        elem = elements[i]
        if isinstance(elem, (FigureCaption, Header, Footer, UnstructuredTable, Image)):
            continue

        if page_number <= elem.metadata.page_number <= page_number + 1:
            ratio = difflib.SequenceMatcher(None, text, elem.text).ratio()
            if ratio > thresh:
                matches.append(i)

    return matches

# @DeprecationWarning
# def merge_text_segments(doc: Document, elements: List[Element], thresh=0.5) -> List[SegmentsAlignment]:
#     def llmsherpa_section_to_segment(section: Section) -> TextSegment:
#         assert not isinstance(section, Table), f"section must be a Section, got {type(section)}"
#
#         if section.children:
#             text = CHUNK_DELIM.join(get_paragraphs(section))
#         else:
#             text = None
#
#         header = section.title
#
#         return TextSegment(
#             header=header,
#             page_number=section.page_idx + 1,
#             text=text,
#             html=section.to_html(),
#             source='llmsherpa',
#             original=section,
#         )
#
#     merged = []
#
#     element_index = 0
#     for section in doc.sections():
#         section_page = section.page_idx + 1
#         section_title = section.title
#         if not section.children:
#             continue
#
#         matched_elements: List[Element] = []
#         for child in section.children:
#             if isinstance(child, llmsherpa.readers.layout_reader.Paragraph):
#                 child_text = child.to_text(include_children=True, recurse=True).replace('\n', ' ')
#
#                 matched_elem_idx = find_matching_text_elem(child_text, elements, page_number=section_page,
#                                                            start_index=element_index, thresh=thresh) or [element_index]
#                 matched_elements.extend([elements[i] for i in matched_elem_idx if i < len(elements)])
#
#             else:
#                 continue
#
#             element_index = max(matched_elem_idx) + 1
#
#         # If texts are similar enough, create a record
#         if matched_elements:
#             record = SegmentsAlignment(
#                 header=section_title,
#                 llmsherpa=[llmsherpa_section_to_segment(section)],
#                 unstructured=[TextSegment.from_unstructured(elem, header=section_title) for elem in matched_elements])
#             merged.append(record)
#
#     return merged
