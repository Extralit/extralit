from typing import List

import spacy
from llmsherpa.readers.layout_reader import Section, Document, Paragraph, Table

from extralit.convert.html_table import fix_llmsherpa_html_table
from extralit.preprocessing.segment import TableSegment, TextSegment, Segments
from extralit.preprocessing.tables import table_extraction_qc, get_table_header_footer


def get_table_segments(document: Document, caption_pattern=r'(?i)(Table)\s?(\d+\.?)(.*|$)') -> Segments:
    tables = Segments()
    captions_taken = set()
    for table in document.tables():
        if not isinstance(table, Table):
            continue

        sections: List[Section] = table.parent.children

        header, footer = get_table_header_footer(
            elements=sections,
            start_index=sections.index(table),
            look_ahead=5,
            get_text_fn=lambda x: x.to_text(),
            current_pattern=r'(?i)(Table)\s?(\d+\.?)(.*?)(?=\|)',
            header_pattern=r'(?i)(Table)\s?([Il|\d]+\.?)(.*|$)',
            footer_pattern=r'(?i)(Table)\s?([Il|\d]+\.?)(.*|$)',
            header_filter_fn=lambda x: \
                isinstance(x, Paragraph) and \
                table.page_idx == x.page_idx,
            footer_filter_fn=lambda x: \
                isinstance(x, Paragraph) and \
                table.page_idx == x.page_idx,
            captured_indices=captions_taken
        )
        # print(f'\n> page {table.page_idx}', '\n\theader:', header, '\n\tfooter:' if footer else '', footer)

        html = table.to_html().strip()
        if not html:
            continue

        segment = TableSegment(
            header=(header + footer).strip(),
            page_number=table.page_idx + 1,
            text=table.to_text(),
            html=fix_llmsherpa_html_table(html),
            source='llmsherpa',
            original=table,
        )
        if not table_extraction_qc(segment):
            continue
        tables.items.append(segment)

    return tables


def get_paragraphs(section: Section) -> List[str]:
    text_chunks = []
    for child in section.children:
        if not isinstance(child, Paragraph):
            continue

        text = child.to_text(include_children=True, recurse=True).replace('\n', ' ')
        text_chunks.append(text)

    return text_chunks


def get_text_segments(document: Document) -> Segments:
    segments = Segments()
    nlp = spacy.load("en_core_web_sm")
    for section in document.sections():
        if not isinstance(section, Section) or isinstance(section, Table):
            continue

        if section.children:
            text = ''.join(get_paragraphs(section))
        else:
            continue

        if not any(nlp(text).ents):
            continue

        segment = TextSegment(
            header=section.title,
            page_number=section.page_idx + 1,
            text=text,
            html=section.to_html().replace('—', '-').replace('·', '.'),
            source='llmsherpa',
            original=section,
        )

        segments.items.append(segment)

    return segments
