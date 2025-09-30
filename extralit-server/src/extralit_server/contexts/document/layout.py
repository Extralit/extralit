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

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class PDFOCRSettings(BaseSettings):
    """
    PDF OCR settings that can be configured via environment variables.

    All settings have the OCR_ prefix.
    """

    class Config:
        env_prefix = "OCR_"

    run_mode: Literal["marker", "local"] = "local"

    modal_base_url: str | None = Field(default=None, description="Base URL for Modal-hosted Marker service")

    modal_timeout_secs: int = Field(
        default=600, description="Timeout in seconds for requests to Modal-hosted Marker service"
    )


settings = PDFOCRSettings()
