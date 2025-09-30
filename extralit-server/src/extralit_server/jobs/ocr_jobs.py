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
import os
from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING, Any, Optional, Union
from uuid import UUID

from dotenv import load_dotenv
from rq import Retry, get_current_job
from rq.decorators import job

from extralit_server.contexts.ocr.figures import extract_figure_bboxes
from extralit_server.contexts.ocr.tables import extract_table_bboxes
from extralit_server.contexts.ocr.text import extract_text_bboxes
from extralit_server.jobs.queues import DEFAULT_QUEUE, REDIS_CONNECTION

load_dotenv()

# Switch between local Marker and Modal-remote Marker
MARKER_RUN_MODE = os.getenv("MARKER_RUN_MODE", "local").lower()

_LOGGER = logging.getLogger(__name__)

if MARKER_RUN_MODE == "local":
    try:
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
    except ImportError as e:
        _LOGGER.error(f"Marker dependencies not available: {e}")
        raise ImportError("Marker not installed. Install with: pip install marker-pdf") from e
else:
    # Modal mode: use HTTP client, no local Marker deps needed
    from extralit_server.integrations.modal.marker_client import convert_document_via_modal

if TYPE_CHECKING:
    from marker.renderers.json import JSONOutput


@job(queue=DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=1800, retry=Retry(max=2, interval=[30, 60]))
async def async_marker_layout_job(
    pdf_path: Union[str, Path],
    pages: Optional[str] = None,
    extract_text: bool = False,
    document_id: Optional[UUID] = None,
) -> dict[str, Any]:
    """
    Use Marker to extract layout (tables, figures, text blocks).
    If MARKER_RUN_MODE=modal, calls Modal endpoint; if =local, runs Marker in-process.
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
                "run_mode": MARKER_RUN_MODE,
            }
        )
        current_job.save_meta()

    try:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"File is not a PDF: {pdf_path}")

        _LOGGER.info(f"Starting Marker layout extraction for: {pdf_path} (mode={MARKER_RUN_MODE})")

        if MARKER_RUN_MODE == "modal":
            _LOGGER.info(f"Using Modal endpoint: {os.getenv('MARKER_MODAL_BASE_URL')}")
            # Call Modal-hosted Marker with JSON output for layout parsing
            modal_resp = convert_document_via_modal(
                pdf_path=pdf_path,
                output_format="json",
                page_range=pages,
                force_ocr=False,
                paginate_output=False,
                use_llm=False,
            )
            if not modal_resp.get("success"):
                raise RuntimeError(f"Modal conversion failed: {modal_resp}")
            json_payload = modal_resp.get("json") or {}
            layout_result = parse_marker_json_output(json_payload)
        else:
            # Local execution
            config_dict, model_dict = create_marker_config(pages)
            result = run_marker(str(pdf_path), config_dict, model_dict)
            layout_result = parse_marker_output(result)

        # Extract bounding boxes using our utility functions
        tables = extract_table_bboxes(layout_result)
        figures = extract_figure_bboxes(layout_result)
        text_blocks = extract_text_bboxes(layout_result) if extract_text else []

        output = {
            "tables": tables,
            "figures": figures,
            "text_blocks": text_blocks,
            "metadata": {
                "source": "marker",
                "run_mode": MARKER_RUN_MODE,
                "pdf_path": str(pdf_path),
                "pages_processed": pages or "all",
                "total_elements": len(tables) + len(figures) + len(text_blocks),
                "processing_time": None,
            },
        }

        pprint(output)
        _LOGGER.info(f"Marker layout extraction completed. Found {len(tables)} tables, {len(figures)} figures")
        return output

    except Exception as e:
        _LOGGER.error(f"Error in marker layout extraction job: {e}", exc_info=True)
        raise


def create_marker_config(pages: Optional[str] = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Create optimized Marker configuration for layout detection only (no OCR).
    """
    config_dict = {
        "output_format": "json",
        "force_ocr": False,
        "paginate_output": False,
        "extract_images": False,
    }
    if pages is not None:
        config_dict["page_range"] = pages
    model_dict = create_model_dict()
    return config_dict, model_dict


def run_marker(pdf_path: str, config_dict: dict[str, Any], model_dict: dict[str, Any]) -> "JSONOutput":
    """
    Run Marker layout detection locally.
    """
    config_parser = ConfigParser(config_dict)
    final_config = config_parser.generate_config_dict()

    converter = PdfConverter(
        config=final_config,
        artifact_dict=model_dict,
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
    )

    result = converter(pdf_path)
    if not hasattr(result, "model_dump"):
        raise ValueError(f"Expected a Pydantic model with model_dump (like JSONOutput), but got {type(result)}")
    return result


def parse_marker_output(result: "JSONOutput") -> dict[str, Any]:
    """
    Parse Marker JSONOutput into our application's expected layout format.
    """
    layout_data = {"pages": []}
    if result.children:
        for page_idx, page in enumerate(result.children):
            page_data = {"page": page_idx, "blocks": []}
            if page.children:
                for block in page.children:
                    block_data = {
                        "type": getattr(block, "block_type", None) or "unknown",
                        "bbox": getattr(block, "bbox", None) or [],
                        "content": (getattr(block, "html", None) or "").strip(),
                        "id": getattr(block, "id", None) or "",
                        "score": None,
                    }
                    page_data["blocks"].append(block_data)
            layout_data["pages"].append(page_data)
    return layout_data


def parse_marker_json_output(result_json: dict[str, Any]) -> dict[str, Any]:
    """
    Parse the JSON renderer payload returned by Modal (modal_resp['json']).
    Mirrors Marker JSONOutput.model_dump().
    """
    layout_data = {"pages": []}
    children = result_json.get("children") or []
    for page_idx, page in enumerate(children):
        page_data = {"page": page_idx, "blocks": []}
        for block in page.get("children") or []:
            block_data = {
                "type": block.get("block_type") or "unknown",
                "bbox": block.get("bbox") or [],
                "content": (block.get("html") or "").strip(),
                "id": block.get("id") or "",
                "score": None,
            }
            page_data["blocks"].append(block_data)
        layout_data["pages"].append(page_data)
    return layout_data


if __name__ == "__main__":
    import argparse
    import asyncio
    import json

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

    async def _main():
        result = await async_marker_layout_job(
            pdf_path=args.pdf_path,
            pages=args.pages,
            extract_text=args.extract_text,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(_main())
