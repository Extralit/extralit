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

import os
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()  # loads variables from a .env file in the project root

DEFAULT_TIMEOUT = int(os.getenv("MARKER_MODAL_TIMEOUT_SECS", "600"))


def get_modal_base_url() -> str:
    base_url = os.getenv("MARKER_MODAL_BASE_URL", "").rstrip("/")
    if not base_url:
        raise RuntimeError("MARKER_MODAL_BASE_URL is not set. Set it to your Modal endpoint URL.")
    return base_url


def convert_document_via_modal(
    pdf_path: Path,
    output_format: str = "json",
    page_range: Optional[str] = None,
    force_ocr: bool = False,
    paginate_output: bool = False,
    use_llm: bool = False,
    timeout: Optional[int] = None,
    extra_headers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """
    Calls the Modal-hosted Marker /convert endpoint and returns the JSON response.
    """
    base_url = get_modal_base_url()
    url = f"{base_url}/convert"

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    files = {"file": (pdf_path.name, open(pdf_path, "rb"), "application/pdf")}
    data = {
        "output_format": output_format,  # "json" is best for layout parsing
        "page_range": page_range,
        "force_ocr": str(bool(force_ocr)).lower(),
        "paginate_output": str(bool(paginate_output)).lower(),
        "use_llm": str(bool(use_llm)).lower(),
    }
    data = {k: v for k, v in data.items() if v not in (None, "", "none", "null")}

    headers = extra_headers or {}
    t = timeout if timeout is not None else DEFAULT_TIMEOUT
    resp = requests.post(url, files=files, data=data, headers=headers, timeout=t)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Modal Marker conversion failed: {e}; body={resp.text[:1000]}") from e
    return resp.json()
