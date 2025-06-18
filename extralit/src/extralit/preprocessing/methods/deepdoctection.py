import os
from typing import List

from PIL import Image
from deepdoctection import Page, LayoutType, ImageAnnotationBaseView

from extralit.convert.pdf import extract_image
from extralit.preprocessing.segment import TableSegment, FigureSegment, Segments, Coordinates
from extralit.preprocessing.tables import get_table_header_footer


def get_table_segments(pages: List[Page], output_dir=None, redo=True) -> Segments:
    os.makedirs(output_dir, exist_ok=True)
    segments = Segments()
    for page_num, page in enumerate(pages, start=1):
        if page is None:
            continue
        page_image = Image.fromarray(page.viz(show_layouts=False, show_cells=False, show_token_class=False))

        captured_indices = set()
        for table_num, table in enumerate(page.tables, start=1):
            coordinates = get_coordinates(table, page)
            image_path = extract_image(page_image, coordinates,
                                       title=f"table_{page_num}_{table_num}.png",
                                       output_dir=output_dir, redo=redo)

            table_index = next((i for i, ann in enumerate(page.annotations) \
                                if ann._annotation_id == table.annotation_id), None)

            # Find the table header
            header, footer = get_table_header_footer(
                page.annotations,
                start_index=table_index,
                look_ahead=2,
                get_text_fn=lambda x: x.text,
                header_pattern=r'(?i)(Table)\s?([Il|\d]+\.?)(.*|$)',
                footer_pattern=r'.*',
                header_filter_fn=lambda x: \
                    x._category_name == LayoutType.text and \
                    coordinates.is_vstacked(get_coordinates(x, page), width='smaller') != False,
                footer_filter_fn=lambda x: \
                    x._category_name == LayoutType.text and \
                    coordinates.is_vstacked(get_coordinates(x, page), width='smaller') != False,
                captured_indices=captured_indices
            )
            # print(f'\n> table {table_num}, page {page_num}', '\n\theader:', header, '\n\tfooter:' if footer else '',
            #       footer)

            segment = TableSegment(
                header=(header + footer).strip(),
                page_number=page_num,
                text=table.text,
                html=table.html,
                image=image_path,
                probability=table.score,
                coordinates=coordinates,
                source='deepdoctection',
                original=table,
            )
            segments.items.append(segment)

    return segments


def get_coordinates(layout: ImageAnnotationBaseView, page: Page):
    bbox = layout.bounding_box
    coordinates = Coordinates(
        points=[[bbox.ulx, bbox.uly],
                [bbox.lrx, bbox.uly],
                [bbox.ulx, bbox.lry],
                [bbox.lrx, bbox.lry]],
        layout_width=page.width,
        layout_height=page.height,
    )
    return coordinates


def get_figure_segments(figures: List[Page]) -> Segments:
    segments = Segments()
    for figure in figures:
        segment = FigureSegment(
            header=figure.name,
            page_number=figure.page_idx + 1,
            image=figure.image,
            source='deepdoctection',
            original=figure,
        )
        segments.items.append(segment)

    return segments
