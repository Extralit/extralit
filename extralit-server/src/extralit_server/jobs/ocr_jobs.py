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
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        # Create configuration for JSON output
        config = {
            "output_format": "json",
        }
        if pages is not None:
            config["page_range"] = pages

        config_parser = ConfigParser(config)

        # Create converter with proper configuration
        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
            llm_service=config_parser.get_llm_service(),
        )

        # Convert PDF to JSON format
        rendered = converter(pdf_path)

        # Convert to the format expected by our utility functions
        result = {"pages": []}

        # The rendered object should have a children attribute with pages
        if hasattr(rendered, "children") and rendered.children:
            for page_output in rendered.children:
                # Extract page number from block ID or use index
                page_num = 0
                if hasattr(page_output, "id") and page_output.id:
                    # Try to extract page number from ID like "/page/0/Page/123"
                    id_parts = str(page_output.id).split("/")
                    if len(id_parts) >= 3 and id_parts[1] == "page":
                        try:
                            page_num = int(id_parts[2])
                        except (ValueError, IndexError):
                            pass

                page_data = {
                    "page": page_num,
                    "blocks": [],
                }

                # Extract blocks from the page
                if hasattr(page_output, "children") and page_output.children:
                    for block in page_output.children:
                        if hasattr(block, "block_type") and hasattr(block, "bbox"):
                            block_data = {
                                "type": str(block.block_type).lower(),
                                "bbox": block.bbox if hasattr(block, "bbox") else [],
                                "polygon": block.polygon if hasattr(block, "polygon") else [],
                                "id": str(block.id) if hasattr(block, "id") else "",
                                "confidence": 1.0,  # Marker doesn't provide confidence scores
                            }
                            # Add text content if available
                            if hasattr(block, "html") and block.html:
                                block_data["content"] = block.html
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
    # Since RQ runs jobs synchronously, we can just call the async function directly
    # using asyncio.run() which handles event loop creation properly
    return asyncio.run(async_marker_layout_job(pdf_path, pages, extract_text, document_id))
