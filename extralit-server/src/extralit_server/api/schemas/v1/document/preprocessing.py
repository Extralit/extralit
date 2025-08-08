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

from typing import Dict, List, Optional
from pydantic import BaseModel


class PDFMetadata(BaseModel):
    """
    Metadata for PDF processing results.
    """

    filename: str
    processing_time: float
    page_count: Optional[int] = None
    language_detected: Optional[List[str]] = None
    processing_settings: Optional[Dict] = None
    analysis_results: Optional[Dict] = None
