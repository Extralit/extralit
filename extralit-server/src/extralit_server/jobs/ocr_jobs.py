# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OCR-related job functions for document processing."""

import logging
from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING, Any, Optional, Union
from uuid import UUID

from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.contexts.ocr.figures import extract_figure_bboxes
from extralit_server.contexts.ocr.tables import extract_table_bboxes
from extralit_server.contexts.ocr.text import extract_text_bboxes
from extralit_server.jobs.queues import DEFAULT_QUEUE, REDIS_CONNECTION

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from marker.renderers.json import JSONOutput
    from marker.renderers.markdown import MarkdownOutput

try:
    from marker.config.parser import ConfigParser
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
except ImportError as e:
    _LOGGER.error(f"Marker dependencies not available: {e}")
    raise ImportError("Marker not installed. Install with: pip install marker-pdf") from e


@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=1800, retry=Retry(max=2, interval=[30, 60]))
async def async_marker_layout_job(
    pdf_path: Union[str, Path],
    pages: Optional[str] = None,
    extract_text: bool = False,
    document_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """
    Use Marker to extract layout (tables, figures, text blocks) without running OCR.

    This job uses Marker's layout detection capabilities to identify and extract
    bounding boxes for different document elements without performing OCR.

    Args:
        pdf_path: Path to the PDF file to process
        pages: Optional comma-separated page numbers to process (0-indexed). If None, processes all pages
        extract_text: Whether to extract text blocks in addition to tables/figures
        document_id: Optional document ID for job tracking

    Returns:
        Dictionary containing structured layout information:
        - tables: List of table bounding boxes
        - figures: List of figure bounding boxes
        - text_blocks: List of text block bounding boxes (if extract_text=True)
        - metadata: Job execution metadata
    """
    current_job = get_current_job()
    if current_job is not None:
        current_job.meta.update(
            {
                "pdf_path": str(pdf_path),
                "document_id": str(document_id) if document_id else None,
                "pages": pages,
                "extract_text": extract_text,
                "workflow_step": "marker_layout_extraction",
            }
        )
        current_job.save_meta()

    try:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        _LOGGER.info(f"Starting Marker layout extraction for: {pdf_path}")

        # Call Marker's layout detection
        # Use the real PdfConverter API for layout detection
        try:
            # Process the PDF and get layout information
            layout_result = _call_marker_layout_detection(str(pdf_path), pages)
        except Exception as e:
            _LOGGER.error(f"Failed to call Marker API: {e}")
            raise

        # Extract bounding boxes using our utility functions
        tables = extract_table_bboxes(layout_result)
        figures = extract_figure_bboxes(layout_result)
        text_blocks = extract_text_bboxes(layout_result) if extract_text else []

        result = {
            "tables": tables,
            "figures": figures,
            "text_blocks": text_blocks,
            "metadata": {
                "source": "marker",
                "pdf_path": str(pdf_path),
                "pages_processed": pages or "all",
                "total_elements": len(tables) + len(figures) + len(text_blocks),
                "extract_text": extract_text,
                "processing_time": None,
            },
        }

        # Update job metadata with results
        # current_job.meta.update(
        #     {
        #         "layout_extraction_complete": True,
        #         "tables_found": len(tables),
        #         "figures_found": len(figures),
        #         "text_blocks_found": len(text_blocks),
        #     }
        # )
        # current_job.save_meta()

        _LOGGER.info(f"Marker layout extraction completed. Found {len(tables)} tables, {len(figures)} figures")
        return result

    except Exception as e:
        _LOGGER.error(f"Error in marker layout extraction job: {e}", exc_info=True)
        # current_job.meta["error"] = str(e)
        # current_job.save_meta()
        raise


def _call_marker_layout_detection(pdf_path: str, pages: Optional[str] = None) -> dict[str, Any]:
    """
    Call Marker's layout detection API using the standard PdfConverter.

    Args:
        pdf_path: Path to the PDF file
        pages: Optional list of page numbers to process (0-indexed)

    Returns:
        Marker's layout detection results with block structure
    """
    # Basic input validation
    if not pdf_path:
        raise ValueError("PDF path cannot be empty")

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

    if pdf_file.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF: {pdf_path}")

    try:
        # Create optimized configuration for layout detection
        config_dict = {
            "output_format": "json",
            "parallel_factor": 1,
        }

        if pages is not None:
            config_dict["page_range"] = pages

        config = ConfigParser(config_dict)
        model_dict = create_model_dict()

        converter = PdfConverter(
            config=config.generate_config_dict(),
            artifact_dict=model_dict,
        )

        # Convert PDF - this will return a Document object with detected layout
        result: "MarkdownOutput | JSONOutput" = converter(pdf_path)  # noqa: UP037
        print(type(result))
        pprint(result.model_dump())

        # Extract layout information from the result
        # The result should have metadata and blocks that we can process
        layout_data = {"pages": []}

        if hasattr(result, "pages") and result.pages:
            for page_idx, page in enumerate(result.pages):
                page_data = {"page": page_idx, "blocks": []}

                # Extract blocks from the page
                if hasattr(page, "blocks") and page.blocks:
                    for block in page.blocks:
                        if hasattr(block, "block_type") and hasattr(block, "bbox"):
                            block_data = {
                                "type": str(block.block_type).lower(),
                                "bbox": list(block.bbox) if block.bbox else [],
                                "id": str(getattr(block, "id", "")),
                                "score": getattr(block, "confidence", 1.0),
                            }

                            # Add content based on block type
                            if hasattr(block, "content"):
                                block_data["content"] = str(block.content)
                            elif hasattr(block, "text"):
                                block_data["content"] = str(block.text)

                            page_data["blocks"].append(block_data)

                layout_data["pages"].append(page_data)

        return layout_data

    except Exception as e:
        _LOGGER.error(f"Error calling Marker API: {e}")
        raise


if __name__ == "__main__":
    import argparse
    import asyncio
    import json
    from uuid import UUID

    parser = argparse.ArgumentParser(description="Test async_marker_layout_job from CLI.")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process.")
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Comma-separated list of page numbers to process (0-indexed). If omitted, all pages are processed.",
    )
    parser.add_argument(
        "--extract-text", action="store_true", help="Extract text blocks in addition to tables/figures."
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path
    pages = args.pages
    extract_text = args.extract_text

    async def _main():
        # Call the underlying logic directly, not as an RQ job
        result = await async_marker_layout_job(
            pdf_path=pdf_path,
            pages=pages,
            extract_text=extract_text,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(_main())
