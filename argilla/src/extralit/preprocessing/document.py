import glob
import os
from os.path import join
from typing import Tuple, Optional

import dill
import pandas as pd

from extralit.preprocessing.segment import Segments
from extralit.storage.files import FileHandler, StorageType

__all__ = [
    'load_segments',
    'create_or_load_unstructured_segments',
    'create_or_load_llmsherpa_segments',
    'create_or_load_nougat_segments',
    'create_or_load_pdffigures2_segments',
    'create_or_load_deepdoctection_segments',
]

def load_segments(file_handler: FileHandler, path: str) -> Tuple[Segments, Segments, Segments]:
    texts = Segments()
    tables = Segments()
    figures = Segments()

    if file_handler.exists(join(path, 'texts.json')):
        texts = Segments.parse_raw(file_handler.read_text(join(path, 'texts.json')))
    if file_handler.exists(join(path, 'tables.json')):
        tables = Segments.parse_raw(file_handler.read_text(join(path, 'tables.json')))
    if file_handler.exists(join(path, 'figures.json')):
        figures = Segments.parse_raw(file_handler.read_text(join(path, 'figures.json')))

    return texts, tables, figures


def create_or_load_unstructured_segments(
    paper: pd.Series, file_handler: FileHandler,
    load_only=True, redo=False, save=True,
) -> Tuple[Optional[Segments], Optional[Segments], Optional[Segments]]:
    from extralit.preprocessing.methods import unstructured
    from unstructured.partition.pdf import partition_pdf
    from unstructured.staging.base import elements_to_json, elements_from_json

    cache_path: str = join('unstructured', paper.name)
    model_output_path = join(cache_path, 'elements.json')
    figures_path = join(cache_path, 'figures')

    if file_handler.exists(cache_path) and load_only:
        return load_segments(file_handler, cache_path)

    if not file_handler.exists(model_output_path) or redo:
        print(f"Unstructured {paper.name}: {cache_path}", flush=True)
        os.makedirs(figures_path, exist_ok=True)
        elements = partition_pdf(
            filename=paper.file_path,
            strategy='hi_res',
            infer_table_structure=True,
            chunking_strategy={
                'multipage_sections': True,
                'include_metadata': True,
                'combine_text_under_n_chars': 500,
            },
            extract_images_in_pdf=True,
            image_output_dir_path=figures_path,
            extract_image_block_output_dir=figures_path,
            pdf_image_dpi=600,
        )
        if save:
            elements_to_json(elements, filename=model_output_path)
    else:
        elements = elements_from_json(model_output_path)

    texts = unstructured.get_text_segments(elements)
    tables = unstructured.get_table_segments(elements, output_dir=figures_path)
    figures = unstructured.get_figure_segments(elements)

    if save:
        file_handler.write_text(join(cache_path, 'texts.json'), texts.json())
        file_handler.write_text(join(cache_path, 'tables.json'), tables.json())
        file_handler.write_text(join(cache_path, 'figures.json'), figures.json())

    return texts, tables, figures


def create_or_load_llmsherpa_segments(
    paper: pd.Series, file_handler: FileHandler,
    load_only=True, redo=False, save=True,
) -> Tuple[Optional[Segments], Optional[Segments], Optional[Segments]]:
    from extralit.preprocessing.methods import llmsherpa
    from llmsherpa.readers import LayoutPDFReader

    cache_path: str = join('llmsherpa', paper.name)
    model_output_path = join(cache_path, 'document.pkl')

    if file_handler.exists(cache_path) and load_only:
        return load_segments(file_handler, cache_path)

    if not file_handler.exists(model_output_path) or redo:
        print(f"Llmsherpa {paper.name}: {cache_path}", flush=True)
        os.makedirs(cache_path, exist_ok=True)
        pdf_reader = LayoutPDFReader(
            "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all")
        try:
            document = pdf_reader.read_pdf(paper.file_path)
        except Exception as e:
            print(e)
            return None, None, None
        if save:
            with open(model_output_path, 'wb') as file:
                dill.dump(document, file)
    else:
        with open(model_output_path, 'rb') as file:
            document = dill.load(file)

    texts = llmsherpa.get_text_segments(document)
    tables = llmsherpa.get_table_segments(document)

    if save:
        file_handler.write_text(join(cache_path, 'texts.json'), texts.json())
        file_handler.write_text(join(cache_path, 'tables.json'), tables.json())

    return texts, tables, None


def create_or_load_nougat_segments(
    paper: pd.Series, file_handler: FileHandler,
    nougat_model=None,
    load_only=True, redo=False, save=True,
) -> Tuple[Optional[Segments], Optional[Segments], Optional[Segments]]:
    from extralit.preprocessing.methods import nougat

    cache_path: str = join('nougat', paper.name)
    model_output_path = join(cache_path, 'predictions.json')

    if file_handler.exists(cache_path) and load_only:
        return load_segments(file_handler, cache_path)

    if not file_handler.exists(model_output_path) or redo:
        from extralit.preprocessing.text import NougatOCR
        if not isinstance(nougat_model, NougatOCR):
            raise ValueError("NougatOCR model is required for Nougat preprocessing.")

        predictions = nougat_model.predict(paper.file_path)
        output = nougat.NougatOutput(reference=paper.name, pages=predictions)
        if save:
            file_handler.write_text(model_output_path, output.json())
    else:
        output = nougat.NougatOutput.parse_file(model_output_path)

    texts = nougat.get_text_segments(output.pages)
    tables = nougat.get_table_segments(output.pages)

    if save:
        file_handler.write_text(join(cache_path, 'texts.json'), texts.json())
        file_handler.write_text(join(cache_path, 'tables.json'), tables.json())

    return texts, tables, None


def create_or_load_pdffigures2_segments(
    paper: pd.Series, file_handler: FileHandler, 
    jar_path='~/bin/pdffigures2.jar', load_only=True, redo=False, save=True,
) -> Tuple[Optional[Segments], Optional[Segments], Optional[Segments]]:
    if not os.path.exists(jar_path):
        raise FileNotFoundError(f"pdffigures2 jar not found: {jar_path}")
    
    cache_path: str = join('pdffigure2', paper.name)
    _, file_name_ext = os.path.split(paper.file_path)
    file_name, _ = os.path.splitext(file_name_ext)
    model_output_path = join(cache_path, f'{file_name}.json')

    if file_handler.exists(join(cache_path, 'figures.json')) and load_only:
        return load_segments(file_handler, cache_path)

    if not file_handler.exists(model_output_path) or redo:
        print(f"pdffigures2 {paper.name}: {cache_path}", flush=True)
        os.makedirs(cache_path, exist_ok=True)
        command = 'java -jar {jar_path} {file_path} -m {output_dir} -d {output_dir} --figure-format png'
        os.system(command.format(
            jar_path=jar_path,
            file_path=paper.file_path,
            output_dir=cache_path.rstrip('/') + '/'))

    try:
        segments = Segments.from_pdffigures2(model_output_path)
    except Exception as e:
        print(e)
        return None, None, None

    tables = Segments()
    figures = Segments()
    for segment in segments.items:
        if segment.type == 'table':
            tables.items.append(segment)
        elif segment.type == 'figure':
            figures.items.append(segment)

    if save:
        file_handler.write_text(join(cache_path, 'tables.json'), tables.json())
        file_handler.write_text(join(cache_path, 'figures.json'), figures.json())

    return None, tables, figures


def create_or_load_deepdoctection_segments(
    paper: pd.Series, file_handler: FileHandler,
    load_only=True, redo=False, save=True,
) -> Tuple[Optional[Segments], Optional[Segments], Optional[Segments]]:
    from extralit.preprocessing.methods import deepdoctection
    import deepdoctection as dd

    cache_path: str = join('deepdoctection', paper.name)
    model_output_path = join(cache_path, 'page_1.json')

    if file_handler.exists(cache_path) and load_only:
        return load_segments(file_handler, cache_path)

    if not file_handler.exists(model_output_path) or redo:
        print(f"Deepdoctection {paper.name}: {cache_path}", flush=True)
        os.makedirs(cache_path, exist_ok=True)

        os.environ["USE_DD_PILLOW"] = "True"
        os.environ["USE_DD_OPENCV"] = "False"

        analyzer = dd.get_dd_analyzer(config_overwrite=[
            "PT.LAYOUT.WEIGHTS=microsoft/table-transformer-detection/pytorch_model.bin",
            "PT.ITEM.WEIGHTS=microsoft/table-transformer-structure-recognition-v1.1-all/pytorch_model.bin",
            "PT.ITEM.FILTER=['table']",
            "USE_PDF_MINER=True",
            "USE_OCR=True",
        ])

        try:
            df = analyzer.analyze(path=paper.file_path)
            df.reset_state()
        except Exception as e:
            print(e)
            return None, None, None

        doc = iter(df)
        pages = []
        for page_num in range(1, len(df) + 1):
            try:
                page: dd.Page = next(doc)
                pages.append(page)
                page.save(image_to_json=True, path=join(cache_path, f'page_{page_num}.json')) if save else None
            except StopIteration:
                break
    else:
        pages = []
        for path in sorted(glob.glob(join(cache_path, 'page_*.json'))):
            pages.append(dd.Page.from_file(path))

    tables = deepdoctection.get_table_segments(pages, output_dir=join(cache_path, 'tables'), redo=redo)
    # figures = deepdoctection.get_figure_segments(pages)

    if save:
        file_handler.write_text(join(cache_path, 'tables.json'), tables.json())
        # file_handler.write_text(join(cache_path, 'figures.json'), figures.json())

    return None, tables, None


