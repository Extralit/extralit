import re
from os.path import join
from typing import List

import spacy
from pdf2image import convert_from_path
from unstructured.documents.elements import Element, FigureCaption, Table, Image, Text

from extralit.convert.pdf import extract_image
from extralit.preprocessing.segment import TableSegment, FigureSegment, TextSegment, Segments, Coordinates
from extralit.preprocessing.tables import table_extraction_qc, get_table_header_footer


def get_table_segments(
    elements: List[Element], max_caption_look_head=5, output_dir=None, redo=False
) -> Segments:
    try:
        pdf_path = join(elements[0].metadata.file_directory, elements[0].metadata.filename)
        page_image = convert_from_path(pdf_path, dpi=450)
    except Exception as e:
        print(e)
        page_image = None

    tables = Segments()
    captions_taken = set()
    for i, elem in enumerate(elements):
        if not isinstance(elem, Table):
            continue

        page_number = elem.metadata.page_number
        coordinates = Coordinates(**elem.metadata.coordinates.to_dict())

        # Find the closest FigureCaption element nearest either behind or ahead of the index `i`
        header, footer = get_table_header_footer(
            elements,
            start_index=i,
            look_ahead=max_caption_look_head,
            get_text_fn=lambda x: x.text,
            header_pattern=r'(?i)(Table)\s?([Il|\d]+\.?)(.*|$)',
            footer_pattern=r'.*',
            header_filter_fn=lambda x:
            isinstance(x, (Text, FigureCaption)) and \
            page_number == x.metadata.page_number and \
            coordinates.is_vstacked(Coordinates(**x.metadata.coordinates.to_dict()), width='smaller') != False,
            footer_filter_fn=lambda x:
            isinstance(x, (Text, FigureCaption)) and \
            page_number == x.metadata.page_number and \
            coordinates.is_vstacked(Coordinates(**x.metadata.coordinates.to_dict()), width='smaller') != False,
            captured_indices=captions_taken)

        image_path = None
        if page_image and output_dir and page_number < len(page_image):
            image_path = extract_image(page_image[page_number - 1], coordinates=coordinates,
                                       title=f"table_{i}",
                                       output_dir=output_dir, redo=redo)

        segment = TableSegment(
            header=header.strip() if header else None,
            page_number=page_number,
            coordinates=coordinates,
            image=image_path,
            probability=getattr(elem.metadata, 'detection_class_prob', None),
            text=elem.text,
            html=elem.metadata.text_as_html.replace('—', '-').replace('·', '.'),
            source='unstructured',
            original=elem,
        )

        if table_extraction_qc(segment):
            tables.items.append(segment)

    return tables


def get_figure_segments(
    elements: List[Element], skip_empty_header=True, max_caption_look_head=5
) -> Segments:
    figures = Segments()
    captions_taken = set()
    for i, elem in enumerate(elements):
        if not isinstance(elem, Image):
            continue

        # Find the closest FigureCaption element nearest either behind or ahead of the index `i`
        title_el = None
        for j in range(1, max_caption_look_head):
            if i - j > 0 and isinstance(elements[i - j], FigureCaption) and i - j not in captions_taken:
                title_el = elements[i - j].text
                captions_taken.add(i - j)
                break
            elif i + j < len(elements) and isinstance(elements[i + j], FigureCaption) and i + j not in captions_taken:
                title_el = elements[i + j].text
                captions_taken.add(i + j)
                break

        if skip_empty_header and (not title_el or 'fig' not in title_el.lower()):
            continue

        segment = FigureSegment(
            header=title_el,
            page_number=elem.metadata.page_number,
            coordinates=elem.metadata.coordinates.to_dict(),
            image=getattr(elem.metadata, 'image_path', None),
            probability=getattr(elem.metadata, 'detection_class_prob', None),
            text=elem.text,
            html=elem.metadata.text_as_html,
            source='unstructured',
            original=elem,
        )
        figures.items.append(segment)

    return figures


def get_text_segments(elements: List[Element]) -> Segments:
    segments = Segments()
    parent_map = {}
    watermark_pattern = r'(?:\b[\w/]\s)+'
    nlp = spacy.load("en_core_web_sm")

    for elem in elements:
        if len(elem.text) < 5 or isinstance(elem, (Table, FigureCaption, Image)):
            continue
        elif re.match(watermark_pattern, elem.text):
            continue
        elif "reference" not in elem.text.lower() and not any(nlp(elem.text).ents):
            continue

        segment = TextSegment(
            level=getattr(elem.metadata, 'level', None),
            text=elem.text,
            page_number=elem.metadata.page_number,
            coordinates=elem.metadata.coordinates.to_dict(),
            probability=getattr(elem.metadata, 'detection_class_prob', None),
            source='unstructured',
            original=elem,
        )
        segments.items.append(segment)

    #     parent_id = getattr(elem.metadata, 'parent_id', None)
    #     if parent_id:
    #         if parent_id not in parent_map:
    #             parent_map[parent_id] = []
    #         parent_map[parent_id].append(segment)
    #
    # for segment in segments:
    #     parent_id = getattr(segment.original.metadata, 'parent_id', None)
    #     if parent_id and parent_id in parent_map:
    #         segment.children = parent_map[parent_id]
    #
    # segments = [segment for segment in segments if segment.children]

    return segments
