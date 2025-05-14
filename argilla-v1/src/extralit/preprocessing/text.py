import gc
import logging
from functools import partial
from pathlib import Path
from typing import List
from tqdm.asyncio import tqdm

try:
    import pypdf
    import pypdfium2
    import torch
    from nougat import NougatModel
    from nougat.dataset.rasterize import rasterize_paper
    from nougat.postprocessing import markdown_compatible, close_envs
    from nougat.utils.checkpoint import get_checkpoint
    from nougat.utils.dataset import LazyDataset, ImageDataset
    from nougat.utils.device import default_batch_size, move_to_device
    from torch.utils.data import ConcatDataset
except ImportError as ie:
    raise ImportError("Please run `pip install 'extralit[ocr]'` to install them.") from ie


class NougatOCR:
    def __init__(self, model_tag='0.1.0-base', full_precision=False, markdown=True, skipping=True):
        model_path = get_checkpoint(model_tag=model_tag)
        self.model: NougatModel = NougatModel.from_pretrained(model_path)
        self.markdown = markdown
        self.skipping = skipping

        self.batch_size = default_batch_size()
        self.model = move_to_device(self.model, bf16=not full_precision, cuda=self.batch_size > 0)

        if self.batch_size <= 0:
            self.batch_size = 1

        self.model.eval()

    def batch_predict(self, file_paths: List[Path]) -> List[List[str]]:
        datasets = []

        for pdf in file_paths:
            if not pdf.exists():
                continue

            try:
                dataset = LazyDataset(
                    pdf,
                    partial(self.model.encoder.prepare_input, random_padding=False),
                )
            except pypdf.errors.PdfStreamError:
                logging.info(f"Could not load file {str(pdf)}.")
                continue
            datasets.append(dataset)
        if len(datasets) == 0:
            return

        dataloader = torch.utils.data.DataLoader(
            ConcatDataset(datasets),
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=LazyDataset.ignore_none_collate,
        )

        documents = []
        predictions = []
        file_index = 0
        page_num = 0
        for i, (sample, is_last_page) in enumerate(tqdm(dataloader)):
            model_output = self.model.inference(
                image_tensors=sample, early_stopping=self.skipping
            )
            # check if itnrecal output is faulty
            for j, output in enumerate(model_output["predictions"]):
                if page_num == 0:
                    logging.info(
                        "Processing file %s with %i pages"
                        % (datasets[file_index].name, datasets[file_index].size)
                    )
                page_num += 1
                if output.strip() == "[MISSING_PAGE_POST]":
                    # uncaught repetitions -- most likely empty page
                    predictions.append(f"\n\n[MISSING_PAGE_EMPTY:{page_num}]\n\n")
                elif self.skipping and model_output["repeats"][j] is not None:
                    if model_output["repeats"][j] > 0:
                        # If we end up here, it means the output is most likely not complete and was truncated.
                        logging.warning(f"Skipping page {page_num} due to repetitions.")
                        predictions.append(f"\n\n[MISSING_PAGE_FAIL:{page_num}]\n\n")
                    else:
                        # If we end up here, it means the document page is too different from the training domain.
                        # This can happen e.g. for cover pages.
                        predictions.append(
                            f"\n\n[MISSING_PAGE_EMPTY:{i * self.batchsize + j + 1}]\n\n"
                        )
                else:
                    if self.markdown:
                        output = markdown_compatible(output)
                    predictions.append(output)

                if is_last_page[j]:
                    documents.append(predictions)

                    predictions = []
                    page_num = 0
                    file_index += 1

                    # clear the torch cache and memory
                    self.empty_cache()

        return documents

    def predict(self, file_path: str, verbose=True) -> List[str]:
        with open(file_path, 'rb') as file:
            pdfbin = file.read()
            pdf = pypdfium2.PdfDocument(pdfbin)
            pages = list(range(len(pdf)))

        compute_pages = pages.copy()
        images = rasterize_paper(pdf, pages=compute_pages)

        dataset = ImageDataset(
            images,
            partial(self.model.encoder.prepare_input, random_padding=False),
        )

        dataloader = torch.utils.data.DataLoader(
            dataset,
            batch_size=self.batch_size,
            pin_memory=True,
            shuffle=False,
        )

        # clear the torch cache and memory
        self.empty_cache()

        predictions = [""] * len(pages)
        for idx, sample in tqdm(enumerate(dataloader), total=len(dataloader), disable=not verbose):
            if sample is None:
                continue

            model_output = self.model.inference(image_tensors=sample, early_stopping=self.skipping)

            for page_idx, output in enumerate(model_output["predictions"]):
                if model_output["repeats"][page_idx] is not None:
                    if model_output["repeats"][page_idx] > 0:
                        disclaimer = "\n\n%s\n\n"
                    else:
                        disclaimer = "\n\n%s\n\n"

                    rest = close_envs(model_output["repetitions"][page_idx]).strip()
                    if len(rest) > 0:
                        disclaimer = disclaimer % rest
                    else:
                        disclaimer = ""
                else:
                    disclaimer = ""

                predictions[pages.index(compute_pages[idx * self.batch_size + page_idx])] = \
                    markdown_compatible(output) + disclaimer

            self.empty_cache()
            gc.collect(generation=2)
        return predictions

    def empty_cache(self):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()

    def process_outputs(self, model_output):
        predictions = [""] * len(model_output['predictions'])
        for page_idx, output in enumerate(model_output["predictions"]):
            if model_output["repeats"][page_idx] is not None:
                if model_output["repeats"][page_idx] > 0:
                    disclaimer = "\n\n+++ ==WARNING: Truncated because of repetitions==\n%s\n+++\n\n"
                else:
                    disclaimer = "\n\n+++ ==ERROR: No output for this page==\n%s\n+++\n\n"

                rest = close_envs(model_output["repetitions"][page_idx]).strip()
                if len(rest) > 0:
                    disclaimer = disclaimer % rest
                else:
                    disclaimer = ""
            else:
                disclaimer = ""

            predictions[page_idx] = markdown_compatible(output) + disclaimer
        return predictions
