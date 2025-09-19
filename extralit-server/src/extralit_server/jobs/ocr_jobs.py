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

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"File is not a PDF: {pdf_path}")

        try:
            # Step 1: Create configuration
            config_dict, model_dict = create_marker_config(pages)

            # Step 2: Run Marker
            result = run_marker(str(pdf_path), config_dict, model_dict)
            print("result", type(result))

            # Step 3: Parse output
            layout_result = parse_marker_output(result)

        except Exception as e:
            _LOGGER.error(f"Error calling Marker API: {e}", exc_info=True)
            raise e

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


def create_marker_config(pages: Optional[str] = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Create optimized Marker configuration for layout detection only (no OCR).

    Args:
        pages: Optional comma-separated page numbers to process

    Returns:
        Tuple of (config_dict, model_dict) for Marker
    """
    # Configure for JSON output and layout detection only
    config_dict = {
        "output_format": "json",  # This forces JSONOutput
        "parallel_factor": 1,
        "extract_images": False,  # Skip image extraction for speed
    }

    if pages is not None:
        config_dict["page_range"] = pages

    # Create model dict - keep all models to avoid dependency resolution issues
    # Models will be loaded but won't be used for actual OCR due to configuration
    model_dict = create_model_dict()

    return config_dict, model_dict


def run_marker(pdf_path: str, config_dict: dict[str, Any], model_dict: dict[str, Any]) -> "JSONOutput":
    """
    Run Marker layout detection on a PDF.

    Args:
        pdf_path: Path to the PDF file
        config_dict: Marker configuration dictionary
        model_dict: Marker model dictionary

    Returns:
        JSONOutput object containing layout detection results
    """
    # Use ConfigParser to properly set up the renderer
    config_parser = ConfigParser(config_dict)
    final_config = config_parser.generate_config_dict()

    converter = PdfConverter(
        config=final_config,
        artifact_dict=model_dict,
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),  # This will return JSONRenderer for "json" format
    )

    # This should return JSONOutput because of our config
    result = converter(pdf_path)

    # Verify we got JSONOutput as expected
    if not hasattr(result, "model_dump"):
        raise ValueError(f"Expected a Pydantic model with model_dump (like JSONOutput), but got {type(result)}")

    return result


def parse_marker_output(result: "JSONOutput") -> dict[str, Any]:
    """
    Parse Marker JSONOutput into our application's expected layout format.

    Args:
        result: JSONOutput object from Marker

    Returns:
        A dictionary with a structured list of pages and their blocks.
    """
    layout_data = {"pages": []}

    # JSONOutput has a children attribute that contains the pages
    if hasattr(result, "children") and result.children:
        for page_idx, page in enumerate(result.children):
            page_data = {"page": page_idx, "blocks": []}

            # Each page can have children (blocks)
            if hasattr(page, "children") and page.children:
                for block in page.children:
                    block_data = {
                        "type": block.block_type if hasattr(block, "block_type") else "unknown",
                        "bbox": block.bbox if hasattr(block, "bbox") else [],
                        "content": (block.html if hasattr(block, "html") else "").strip(),
                        "id": block.id if hasattr(block, "id") else "",
                        "score": 1.0,  # Marker doesn't provide confidence scores
                    }
                    page_data["blocks"].append(block_data)

            layout_data["pages"].append(page_data)

    return layout_data


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

    pdf_path: str = args.pdf_path
    pages: str = args.pages
    extract_text: bool = args.extract_text

    async def _main():
        # Call the underlying logic directly, not as an RQ job
        result = await async_marker_layout_job(
            pdf_path=pdf_path,
            pages=pages,
            extract_text=extract_text,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(_main())
