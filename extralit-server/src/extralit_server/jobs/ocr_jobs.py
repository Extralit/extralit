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

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional, Union
from uuid import UUID

from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.contexts.ocr.figures import extract_figure_bboxes
from extralit_server.contexts.ocr.tables import extract_table_bboxes
from extralit_server.contexts.ocr.text import extract_text_bboxes
from extralit_server.jobs.queues import DEFAULT_QUEUE, REDIS_CONNECTION

_LOGGER = logging.getLogger(__name__)


@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=1800, retry=Retry(max=2, interval=[30, 60]))
async def async_marker_layout_job(
    pdf_path: Union[str, Path],
    pages: Optional[list[int]] = None,
    extract_text: bool = False,
    document_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """
    Use Marker to extract layout (tables, figures, text blocks) without running OCR.

    This job uses Marker's layout detection capabilities to identify and extract
    bounding boxes for different document elements without performing OCR.

    Args:
        pdf_path: Path to the PDF file to process
        pages: Optional list of page numbers to process (0-indexed). If None, processes all pages
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
    if current_job is None:
        raise Exception("No current job found")

    # Update job metadata
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
                "processing_time": None,  # Could be added if marker provides this
            },
        }

        # Update job metadata with results
        current_job.meta.update(
            {
                "layout_extraction_complete": True,
                "tables_found": len(tables),
                "figures_found": len(figures),
                "text_blocks_found": len(text_blocks),
            }
        )
        current_job.save_meta()

        _LOGGER.info(f"Marker layout extraction completed. Found {len(tables)} tables, {len(figures)} figures")
        return result

    except Exception as e:
        _LOGGER.error(f"Error in marker layout extraction job: {e}")
        current_job.meta["error"] = str(e)
        current_job.save_meta()
        raise


def _call_marker_layout_detection(pdf_path: str, pages: Optional[list[int]] = None) -> dict[str, Any]:
    """
    Call Marker's layout detection API using PdfConverter with JSON output.

    Args:
        pdf_path: Path to the PDF file
        pages: Optional list of page numbers to process (0-indexed)

    Returns:
        Marker's JSON layout detection results with block structure
    """
    try:
        # Import marker components only when function is called (optional dependency)
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        # Create converter with JSON output for layout detection
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
            output_format="json",  # Request JSON output with block structure
            disable_ocr=False,  # Keep OCR enabled for better layout detection
            page_range=pages,  # Limit to specific pages if requested
        )

        # Build document to get structured layout information
        document = converter.build_document(pdf_path)

        # Render to JSON format to get the block structure
        renderer = converter.resolve_dependencies(converter.renderer)
        json_output = renderer(document)

        # Convert to dictionary format expected by our utility functions
        result = {"pages": []}

        for page_output in json_output.children:
            page_data = {
                "page": int(page_output.id.split("/")[-1]),  # Extract page number from ID
                "blocks": [],
            }

            # Extract blocks from the page
            if hasattr(page_output, "children") and page_output.children:
                for block in page_output.children:
                    block_data = {
                        "type": block.block_type.lower(),
                        "bbox": block.bbox,
                        "polygon": block.polygon,
                        "id": block.id,
                        "confidence": 1.0,  # Marker doesn't provide confidence scores
                    }
                    page_data["blocks"].append(block_data)

            result["pages"].append(page_data)

        return result

    except ImportError as e:
        _LOGGER.error(f"Marker dependencies not available: {e}")
        raise ImportError("Marker not installed. Install with: pip install marker-pdf") from e
    except Exception as e:
        _LOGGER.error(f"Error calling Marker API: {e}")
        raise


# Sync wrapper for RQ compatibility
@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=1800, retry=Retry(max=2, interval=[30, 60]))
def marker_layout_job(
    pdf_path: Union[str, Path],
    pages: Optional[list[int]] = None,
    extract_text: bool = False,
    document_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """
    Synchronous wrapper for async_marker_layout_job for RQ compatibility.

    Args:
        pdf_path: Path to the PDF file to process
        pages: Optional list of page numbers to process (0-indexed)
        extract_text: Whether to extract text blocks in addition to tables/figures
        document_id: Optional document ID for job tracking

    Returns:
        Dictionary containing structured layout information
    """
    # Run the async function in the current event loop or create a new one
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If there's already a running loop, we need to run in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, async_marker_layout_job(pdf_path, pages, extract_text, document_id)
                )
                return future.result()
        else:
            return loop.run_until_complete(async_marker_layout_job(pdf_path, pages, extract_text, document_id))
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(async_marker_layout_job(pdf_path, pages, extract_text, document_id))
