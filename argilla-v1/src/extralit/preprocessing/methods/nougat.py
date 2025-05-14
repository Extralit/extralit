import logging
import re
from typing import List

import pypandoc
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo
from pydantic import BaseModel

from extralit.convert.html_table import remove_html_styles
from extralit.convert.text import remove_longest_repeated_subsequence
from extralit.convert.text import remove_markdown_from_string
from extralit.preprocessing.segment import TableSegment, TextSegment, Segments


class NougatOutput(BaseModel):
    reference: str
    pages: List[str]


def get_text_segments(pages: List[str], title="Title") -> Segments:
    segments = Segments()
    current_segment = None
    stored_header = ""
    parents_stack = []

    for page_number, page in enumerate(pages, start=1):
        page = remove_longest_repeated_subsequence(page, min_substring_len=1, min_repeats=10)
        page = re.sub(r'\n*\\begin{table}.*?\\end{table}\n.*?(\n|$)', '', page, flags=re.DOTALL)
        page = re.sub(r'\n*\\begin{tabular}.*?\\end{tabular}\n.*?(\n|$)', '', page, flags=re.DOTALL)
        if not current_segment and page_number == 1:
            current_segment = TextSegment(header=title, level=1, page_number=page_number, text='')

        for line in page.split('\n'):
            header_match = re.match(r'(#+)\s*(.*)', line)
            if header_match:
                if current_segment and (current_segment.text or current_segment.relationships):
                    segments.items.append(current_segment)
                level = len(header_match.group(1))
                while parents_stack and parents_stack[-1].level >= level:
                    parents_stack.pop()
                parent = parents_stack[-1] if parents_stack else None
                current_segment = TextSegment(header=f"{stored_header}{header_match.group(2)}",
                                              level=level,
                                              page_number=page_number,
                                              text='')

                if parent:
                    current_segment.relationships[NodeRelationship.PARENT] = \
                        RelatedNodeInfo(node_id=parent.id, )

                    parent.relationships.setdefault(NodeRelationship.CHILD, []).append(
                        RelatedNodeInfo(node_id=current_segment.id, )
                    )
                stored_header = ""
                parents_stack.append(current_segment)

            elif current_segment:
                current_segment.text += line + '\n'

    segments.make_headers_unique()
    return segments


def correct_column_definition(latex_table: str) -> str:
    # Split the table into rows
    rows = re.split(r'\\', latex_table)

    # Find the row with the maximum number of columns
    max_columns = max(row.count('&') for row in rows if r'\begin' not in row and r'\end' not in row)

    # Generate the corrected column definition
    corrected_definition = ' '.join(['c' for _ in range(max_columns + 1)])

    # Replace the original column definition in the \begin{tabular} line
    corrected_table = re.sub(r'\\begin{tabular}{.*?}', r'\\begin{tabular}{' + corrected_definition + '}', latex_table)

    return corrected_table


def get_table_segments(pages: List[str]) -> Segments:
    segments = Segments()

    for page_number, page_text in enumerate(pages, start=1):
        # Regular expression pattern for LaTeX tables
        pattern = r'(\\begin{table}.*?\\end{tabular}(.*?)\\end{table})\n(.*?)(\n|$)'
        matches = re.findall(pattern, page_text, re.DOTALL)
        if not matches:
            pattern = r'(\\begin{tabular}.*?\\end{tabular}(.*?))\n(.*?)(\n|$)'
            matches = re.findall(pattern, page_text, re.DOTALL)

        for match in matches:
            table_content, footer, caption, *_ = match
            table_html, table_markdown = '', ''

            try:
                table_html = pypandoc.convert_text(table_content, 'html', format='latex')
            except Exception as e:
                try:
                    table_content = correct_column_definition(table_content)
                    table_html = pypandoc.convert_text(table_content, 'html', format='latex')
                except Exception as e:
                    logging.warning(f"Could not convert table to HTML: {e.__str__()}")
            finally:
                if table_html:
                    table_html = remove_html_styles(table_html)
                    table_html = remove_markdown_from_string(table_html)
                else:
                    continue

            if not table_html.startswith(r'<table>'):
                continue
            else:
                table_html = table_html.replace('—', '-').replace('·', '.')

            caption = caption.strip() + (('\n' + footer.strip()) if footer else '')

            # Create a Segment object
            segment = TableSegment(
                header=caption,
                text=table_markdown,
                html=table_html,
                page_number=page_number,
                original=table_content,
                source='nougat',
            )
            segments.items.append(segment)

    return segments
